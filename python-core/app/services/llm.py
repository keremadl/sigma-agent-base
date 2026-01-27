from typing import AsyncGenerator, List, Dict, Any
import os
import logging

import litellm


logger = logging.getLogger(__name__)

# Configure LiteLLM
litellm.drop_params = True  # Ignore provider-specific params
litellm.set_verbose = False  # Reduce logging noise


class TagParser:
    """
    State machine parser for XML tags in streaming responses.
    Handles partial tags across chunk boundaries and strips tags completely.
    """
    
    def __init__(self):
        self.state = "outside"  # outside, in_thinking, in_answer
        self.buffer = ""  # Main buffer for accumulating content
        self.current_content = ""  # Content being accumulated for current section
        # Tag definitions
        self.THINKING_OPEN = "<thinking>"
        self.THINKING_CLOSE = "</thinking>"
        self.ANSWER_OPEN = "<answer>"
        self.ANSWER_CLOSE = "</answer>"
        self.MAX_TAG_LEN = max(len(self.THINKING_OPEN), len(self.THINKING_CLOSE), 
                               len(self.ANSWER_OPEN), len(self.ANSWER_CLOSE))
    
    def process_chunk(self, chunk: str) -> List[Dict[str, str]]:
        """
        Process chunk and return list of parsed sections.
        Streams content incrementally as it's parsed.
        
        Args:
            chunk: New chunk of text to process
            
        Returns:
            List of dicts with "section" and "content" keys
        """
        if not chunk:
            return []
        
        results = []
        self.buffer += chunk
        
        # Process buffer until no more complete tags are found
        while True:
            made_progress = False
            
            if self.state == "outside":
                # Look for opening tags
                thinking_start = self.buffer.find(self.THINKING_OPEN)
                answer_start = self.buffer.find(self.ANSWER_OPEN)
                
                # Determine which tag comes first
                if thinking_start != -1 and (answer_start == -1 or thinking_start < answer_start):
                    # Found <thinking> first
                    if thinking_start > 0:
                        # Content before tag - treat as answer (fallback)
                        pre_content = self.buffer[:thinking_start].strip()
                        if pre_content:
                            results.append({"section": "answer", "content": pre_content})
                            logger.info(f"TagParser: Found content before <thinking> tag, yielding as answer ({len(pre_content)} chars)")
                    
                    # Strip the tag and switch to thinking mode
                    self.buffer = self.buffer[thinking_start + len(self.THINKING_OPEN):]
                    self.state = "in_thinking"
                    self.current_content = ""
                    logger.info("TagParser: Switching to THINKING mode")
                    made_progress = True
                    
                elif answer_start != -1:
                    # Found <answer> first
                    if answer_start > 0:
                        # Content before tag - treat as answer (fallback)
                        pre_content = self.buffer[:answer_start].strip()
                        if pre_content:
                            results.append({"section": "answer", "content": pre_content})
                            logger.info(f"TagParser: Found content before <answer> tag, yielding as answer ({len(pre_content)} chars)")
                    
                    # Strip the tag and switch to answer mode
                    self.buffer = self.buffer[answer_start + len(self.ANSWER_OPEN):]
                    self.state = "in_answer"
                    self.current_content = ""
                    logger.info("TagParser: Switching to ANSWER mode")
                    made_progress = True
                else:
                    # No complete tags found - check if buffer ends with partial tag
                    # Keep enough chars in buffer to detect split tags
                    safe_to_yield_len = len(self.buffer) - self.MAX_TAG_LEN
                    if safe_to_yield_len > 0:
                        # Check if the end of buffer could be start of a tag
                        buffer_end = self.buffer[-self.MAX_TAG_LEN:]
                        could_be_tag = False
                        
                        # Check if buffer end matches start of any opening tag
                        if self.THINKING_OPEN.startswith(buffer_end) or self.ANSWER_OPEN.startswith(buffer_end):
                            could_be_tag = True
                        
                        if not could_be_tag:
                            # Safe to yield content
                            content_to_yield = self.buffer[:safe_to_yield_len]
                            if content_to_yield.strip():
                                results.append({"section": "answer", "content": content_to_yield})
                                logger.debug(f"TagParser: Yielding buffered content as answer ({len(content_to_yield)} chars)")
                            self.buffer = self.buffer[safe_to_yield_len:]  # Keep last MAX_TAG_LEN chars
                    break
            
            elif self.state == "in_thinking":
                # Look for </thinking> closing tag
                thinking_end = self.buffer.find(self.THINKING_CLOSE)
                
                if thinking_end != -1:
                    # Found closing tag - yield remaining content
                    content_to_yield = self.buffer[:thinking_end]
                    if content_to_yield:
                        results.append({"section": "thinking", "content": content_to_yield})
                        logger.info(f"TagParser: Exiting THINKING mode, yielded {len(content_to_yield)} chars")
                    
                    # Strip closing tag and switch back to outside
                    self.buffer = self.buffer[thinking_end + len(self.THINKING_CLOSE):]
                    self.state = "outside"
                    self.current_content = ""
                    made_progress = True
                else:
                    # No closing tag yet - check if we can safely yield partial content
                    # Keep enough chars to detect split closing tag
                    safe_to_yield_len = len(self.buffer) - len(self.THINKING_CLOSE)
                    if safe_to_yield_len > 0:
                        # Check if buffer end could be start of closing tag
                        buffer_end = self.buffer[-len(self.THINKING_CLOSE):]
                        could_be_closing = self.THINKING_CLOSE.startswith(buffer_end)
                        
                        if not could_be_closing:
                            # Safe to yield - yield only the new portion
                            content_to_yield = self.buffer[:safe_to_yield_len]
                            if content_to_yield:
                                results.append({"section": "thinking", "content": content_to_yield})
                                logger.debug(f"TagParser: Yielding partial thinking content ({len(content_to_yield)} chars)")
                            self.buffer = self.buffer[safe_to_yield_len:]  # Keep last chars for lookahead
                    break
            
            elif self.state == "in_answer":
                # Look for </answer> closing tag
                answer_end = self.buffer.find(self.ANSWER_CLOSE)
                
                if answer_end != -1:
                    # Found closing tag - yield remaining content
                    content_to_yield = self.buffer[:answer_end]
                    if content_to_yield:
                        results.append({"section": "answer", "content": content_to_yield})
                        logger.info(f"TagParser: Exiting ANSWER mode, yielded {len(content_to_yield)} chars")
                    
                    # Strip closing tag and switch back to outside
                    self.buffer = self.buffer[answer_end + len(self.ANSWER_CLOSE):]
                    self.state = "outside"
                    self.current_content = ""
                    made_progress = True
                else:
                    # No closing tag yet - check if we can safely yield partial content
                    # Keep enough chars to detect split closing tag
                    safe_to_yield_len = len(self.buffer) - len(self.ANSWER_CLOSE)
                    if safe_to_yield_len > 0:
                        # Check if buffer end could be start of closing tag
                        buffer_end = self.buffer[-len(self.ANSWER_CLOSE):]
                        could_be_closing = self.ANSWER_CLOSE.startswith(buffer_end)
                        
                        if not could_be_closing:
                            # Safe to yield - yield only the new portion
                            content_to_yield = self.buffer[:safe_to_yield_len]
                            if content_to_yield:
                                results.append({"section": "answer", "content": content_to_yield})
                                logger.debug(f"TagParser: Yielding partial answer content ({len(content_to_yield)} chars)")
                            self.buffer = self.buffer[safe_to_yield_len:]  # Keep last chars for lookahead
                    break
            
            if not made_progress:
                break
        
        return results
    
    def flush(self) -> List[Dict[str, str]]:
        """
        Flush remaining buffer content.
        Call this at the end of streaming to yield any remaining content.
        """
        results = []
        
        # Yield any accumulated content for current section
        if self.state == "in_thinking" and (self.current_content or self.buffer):
            remaining = (self.current_content + self.buffer).strip()
            if remaining:
                results.append({"section": "thinking", "content": remaining})
                logger.info(f"TagParser: Flushing remaining thinking content ({len(remaining)} chars)")
        elif self.state == "in_answer" and (self.current_content or self.buffer):
            remaining = (self.current_content + self.buffer).strip()
            if remaining:
                results.append({"section": "answer", "content": remaining})
                logger.info(f"TagParser: Flushing remaining answer content ({len(remaining)} chars)")
        elif self.buffer:
            # Outside tags but have content - default to answer
            remaining = self.buffer.strip()
            if remaining:
                results.append({"section": "answer", "content": remaining})
                logger.info(f"TagParser: Flushing remaining content as answer ({len(remaining)} chars)")
        
        # Reset state
        self.buffer = ""
        self.current_content = ""
        self.state = "outside"
        
        return results


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

    ALL models use XML tag-based parsing via TagParser.
    Models are instructed via THINKING_PROMPT to output <thinking>...</thinking> and <answer>...</answer> tags.

    Yields dicts with:
    - section: "thinking" | "answer" | "error"
    - content: chunk text (tags stripped)
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

    try:
        # Tag-based parsing for ALL models (unified approach)
        logger.info(f"Using XML tag-based parsing for thinking/answer separation (model: {model})")
        parser = TagParser()
        
        async for chunk_dict in generate_stream(messages, model, api_key, temperature):
            # generate_stream yields content chunks for all models
            chunk_content = chunk_dict.get("content", "")
            full_response += chunk_content
            
            # Process chunk through state machine parser
            parsed_sections = parser.process_chunk(chunk_content)
            
            # Yield each parsed section
            for section in parsed_sections:
                section_type = section["section"]
                section_content = section["content"]
                
                # Skip thinking if include_thinking is False
                if section_type == "thinking" and not include_thinking:
                    continue
                
                yield {
                    "section": section_type,
                    "content": section_content,
                    "full": full_response,
                }
        
        # Flush any remaining buffered content
        final_sections = parser.flush()
        for section in final_sections:
            section_type = section["section"]
            section_content = section["content"]
            
            # Skip thinking if include_thinking is False
            if section_type == "thinking" and not include_thinking:
                continue
            
            yield {
                "section": section_type,
                "content": section_content,
                "full": full_response,
            }

    except Exception as e:
        logger.error(f"Thinking stream error: {e}", exc_info=True)
        yield {
            "section": "error",
            "content": f"\n\n[Error: {str(e)}]",
            "full": full_response,
        }
