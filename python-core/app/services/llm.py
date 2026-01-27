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
) -> AsyncGenerator[str, None]:
    """
    Generate streaming response from LLM

    Simple streaming without thinking tag parsing - yields raw chunks

    Args:
        messages: List of message dicts with role and content
        model: Model name (e.g., "gpt-4o-mini", "claude-3-5-sonnet-20241022")
        api_key: API key for the model provider
        temperature: Randomness (0-1)
        max_tokens: Maximum response length

    Yields:
        Text chunks as they arrive
    """
    try:
        # Set appropriate API key
        if "gpt" in model.lower() or "o1" in model.lower():
            os.environ["OPENAI_API_KEY"] = api_key
        elif "claude" in model.lower():
            os.environ["ANTHROPIC_API_KEY"] = api_key
        elif "gemini" in model.lower():
            os.environ["GOOGLE_API_KEY"] = api_key

        logger.info(f"Starting stream with model: {model}")

        response = await litellm.acompletion(
            model=model,
            messages=messages,
            stream=True,
            temperature=temperature,
            max_tokens=max_tokens,
        )

        async for chunk in response:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content

    except Exception as e:
        logger.error(f"LLM streaming error: {e}")
        yield f"\n\n[Error: {str(e)}]"


async def generate_with_thinking(
    messages: List[Dict[str, Any]],
    model: str,
    api_key: str,
    include_thinking: bool = True,
    temperature: float = 0.7,
) -> AsyncGenerator[Dict[str, Any], None]:
    """
    Generate streaming response with thinking/answer section parsing

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
    current_section = None
    buffer = ""

    try:
        async for chunk in generate_stream(messages, model, api_key, temperature):
            full_response += chunk
            buffer += chunk

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
        logger.error(f"Thinking stream error: {e}")
        yield {
            "section": "error",
            "content": f"\n\n[Error: {str(e)}]",
            "full": full_response,
        }

