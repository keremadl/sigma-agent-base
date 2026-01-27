from typing import AsyncGenerator, List, Dict, Any
import os
import logging

import litellm


logger = logging.getLogger(__name__)

# Configure LiteLLM
litellm.drop_params = True  # Ignore provider-specific params
litellm.set_verbose = False  # Reduce logging noise


async def generate_stream(
    messages: List[Dict[str, Any]],
    model: str,
    api_key: str,
    temperature: float = 0.7,
    max_tokens: int = 4000,
) -> AsyncGenerator[Dict[str, Any], None]:
    """
    Generate streaming response from LLM

    Yields dicts with type ("thinking" or "content") and content.
    For Gemini 3 Pro, uses native thinking mode via thinkingConfig.

    Args:
        messages: List of message dicts with role and content
        model: Model name (e.g., "gpt-4o-mini", "gemini-3-pro-preview")
        api_key: API key for the model provider
        temperature: Randomness (0-1)
        max_tokens: Maximum response length

    Yields:
        Dict with "type" ("thinking" or "content") and "content" (text chunk)
    """
    try:
        # Set appropriate API key
        if "gpt" in model.lower() or "o1" in model.lower():
            os.environ["OPENAI_API_KEY"] = api_key
            custom_provider = None
        elif "claude" in model.lower():
            os.environ["ANTHROPIC_API_KEY"] = api_key
            custom_provider = None
        elif "gemini" in model.lower():
            os.environ["GOOGLE_API_KEY"] = api_key
            custom_provider = "gemini"  # Explicit provider - forces Gemini API
        else:
            custom_provider = None

        logger.info(f"Starting stream with model: {model}")

        # Build completion kwargs
        completion_kwargs = {
            "model": model,
            "messages": messages,
            "stream": True,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        
        # Add explicit provider for Gemini models
        if custom_provider:
            completion_kwargs["custom_llm_provider"] = custom_provider

        # CRITICAL FIX: Set temperature = 1.0 for Gemini 3 Pro to avoid infinite loops
        # Add thinkingConfig for Gemini 3 Pro native thinking mode
        if model == "gemini-3-pro-preview":
            completion_kwargs["temperature"] = 1.0  # Required! Prevents infinite loops
            completion_kwargs["extra_body"] = {
                "thinkingConfig": {
                    "thinkingLevel": "high"
                }
            }
            logger.info("Enabled native thinking mode for Gemini 3 Pro")
            logger.info(f"thinkingConfig: {completion_kwargs.get('extra_body')}")
            logger.info(f"Temperature set to: {completion_kwargs.get('temperature')}")

        response = await litellm.acompletion(**completion_kwargs)

        chunk_count = 0
        async for chunk in response:
            chunk_count += 1
            delta = chunk.choices[0].delta
            
            # DEBUG: Log delta structure for Gemini 3 Pro
            if model == "gemini-3-pro-preview" and chunk_count <= 5:
                logger.info(f"=== Chunk #{chunk_count} Debug ===")
                logger.info(f"Delta type: {type(delta)}")
                logger.info(f"Delta attributes: {dir(delta)}")
                logger.info(f"Delta dict keys (if dict): {delta.keys() if isinstance(delta, dict) else 'N/A'}")
                
                # Check all possible thinking attribute names
                thinking_attrs = []
                if hasattr(delta, "thinking"):
                    thinking_attrs.append("thinking")
                if hasattr(delta, "thought"):
                    thinking_attrs.append("thought")
                if isinstance(delta, dict):
                    if "thinking" in delta:
                        thinking_attrs.append("dict.thinking")
                    if "thought" in delta:
                        thinking_attrs.append("dict.thought")
                
                logger.info(f"Found thinking attributes: {thinking_attrs}")
                
                # Try to get thinking content
                thinking_content = None
                if hasattr(delta, "thinking") and delta.thinking:
                    thinking_content = delta.thinking
                    logger.info(f"Found thinking via delta.thinking: {thinking_content[:100] if thinking_content else 'None'}")
                elif isinstance(delta, dict) and "thinking" in delta and delta["thinking"]:
                    thinking_content = delta["thinking"]
                    logger.info(f"Found thinking via dict['thinking']: {thinking_content[:100] if thinking_content else 'None'}")
                elif hasattr(delta, "thought") and delta.thought:
                    thinking_content = delta.thought
                    logger.info(f"Found thinking via delta.thought: {thinking_content[:100] if thinking_content else 'None'}")
                elif isinstance(delta, dict) and "thought" in delta and delta["thought"]:
                    thinking_content = delta["thought"]
                    logger.info(f"Found thinking via dict['thought']: {thinking_content[:100] if thinking_content else 'None'}")
                else:
                    logger.info("No thinking content found in this chunk")
            
            # Check for native thinking chunks (Gemini 3 Pro)
            has_thinking = False
            thinking_content = None
            
            # Check multiple possible attribute names
            if hasattr(delta, "thinking") and delta.thinking:
                has_thinking = True
                thinking_content = delta.thinking
            elif isinstance(delta, dict) and "thinking" in delta and delta["thinking"]:
                has_thinking = True
                thinking_content = delta["thinking"]
            elif hasattr(delta, "thought") and delta.thought:
                has_thinking = True
                thinking_content = delta.thought
            elif isinstance(delta, dict) and "thought" in delta and delta["thought"]:
                has_thinking = True
                thinking_content = delta["thought"]
            
            # Yield thinking chunk if present
            if has_thinking and thinking_content:
                logger.info(f"Yielding thinking chunk ({len(thinking_content)} chars)")
                yield {
                    "type": "thinking",
                    "content": thinking_content
                }
            
            # Yield content chunk if present
            if hasattr(delta, "content") and delta.content:
                logger.info(f"Yielding content chunk ({len(delta.content)} chars)")
                yield {
                    "type": "content",
                    "content": delta.content
                }
            elif isinstance(delta, dict) and "content" in delta and delta["content"]:
                logger.info(f"Yielding content chunk ({len(delta['content'])} chars)")
                yield {
                    "type": "content",
                    "content": delta["content"]
                }

        logger.info(f"Streaming complete. Total chunks processed: {chunk_count}")

    except Exception as e:
        logger.error(f"LLM streaming error: {e}", exc_info=True)
        yield {
            "type": "content",
            "content": f"\n\n[Error: {str(e)}]"
        }


async def generate_with_thinking(
    messages: List[Dict[str, Any]],
    model: str,
    api_key: str,
    include_thinking: bool = True,
    temperature: float = 0.7,
) -> AsyncGenerator[Dict[str, Any], None]:
    """
    Generate streaming response with thinking/answer section parsing

    For Gemini 3 Pro: Uses native thinking chunks from LiteLLM
    For other models: Parses <thinking> tags from content

    Yields dicts with:
    - section: "thinking" | "answer" | "raw"
    - content: chunk text
    - full: accumulated full text

    Args:
        messages: Message list
        model: Model name
        api_key: API key
        include_thinking: If False, thinking section is captured but not yielded
        temperature: Randomness

    Yields:
        Dict with section info and content
    """
    full_response = ""
    thinking_buffer = ""
    answer_buffer = ""

    # Check if using Gemini 3 Pro native thinking mode
    use_native_thinking = model == "gemini-3-pro-preview"

    try:
        if use_native_thinking:
            # Native thinking mode for Gemini 3 Pro
            logger.info("Using native thinking mode for Gemini 3 Pro")
            thinking_chunks_count = 0
            content_chunks_count = 0
            
            async for chunk_dict in generate_stream(messages, model, api_key, temperature):
                chunk_type = chunk_dict.get("type")
                chunk_content = chunk_dict.get("content", "")
                
                if chunk_type == "thinking":
                    # Accumulate thinking content
                    thinking_chunks_count += 1
                    thinking_buffer += chunk_content
                    logger.info(f"Processing thinking chunk #{thinking_chunks_count}")
                    if include_thinking:
                        # Yield thinking chunks as they arrive
                        yield {
                            "section": "thinking",
                            "content": chunk_content,
                            "full": full_response,  # Full response doesn't include thinking yet
                        }
                elif chunk_type == "content":
                    # Accumulate answer content
                    content_chunks_count += 1
                    answer_buffer += chunk_content
                    full_response += chunk_content
                    logger.info(f"Processing content chunk #{content_chunks_count}")
                    # Yield answer chunks as they arrive
                    yield {
                        "section": "answer",
                        "content": chunk_content,
                        "full": full_response,
                    }
            
            logger.info(f"Native thinking complete. Thinking chunks: {thinking_chunks_count}, Content chunks: {content_chunks_count}")
            
            # Yield any remaining buffers
            if thinking_buffer and include_thinking:
                # Already yielded incrementally, but ensure final state is correct
                pass
            if answer_buffer:
                # Already yielded incrementally
                pass
        else:
            # Tag-based parsing for other models (backward compatibility)
            current_section = None
            buffer = ""

            async for chunk_dict in generate_stream(messages, model, api_key, temperature):
                # For non-Gemini-3-Pro models, generate_stream yields content chunks
                chunk_content = chunk_dict.get("content", "")
                full_response += chunk_content
                buffer += chunk_content

                # Check for section markers
                if "<thinking>" in buffer:
                    current_section = "thinking"
                    # Remove the tag from output
                    buffer = buffer.replace("<thinking>", "")
                    if not include_thinking:
                        buffer = ""
                        continue

                if "</thinking>" in buffer:
                    current_section = None
                    buffer = buffer.replace("</thinking>", "")
                    if not include_thinking:
                        buffer = ""
                        continue

                if "<answer>" in buffer:
                    current_section = "answer"
                    buffer = buffer.replace("<answer>", "")

                if "</answer>" in buffer:
                    buffer = buffer.replace("</answer>", "")

                # Yield chunk if buffer has content
                if buffer:
                    yield {
                        "section": current_section or "answer",
                        "content": buffer,
                        "full": full_response,
                    }
                    buffer = ""

            # Yield any remaining buffer
            if buffer:
                yield {
                    "section": current_section or "answer",
                    "content": buffer,
                    "full": full_response,
                }

    except Exception as e:
        logger.error(f"Thinking stream error: {e}", exc_info=True)
        yield {
            "section": "error",
            "content": f"\n\n[Error: {str(e)}]",
            "full": full_response,
        }
