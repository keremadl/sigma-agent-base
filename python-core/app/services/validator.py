import re
import ast
import logging
from typing import Tuple, List, Dict, Any


logger = logging.getLogger(__name__)


def extract_code_blocks(text: str) -> List[str]:
    """Extract code from markdown code blocks"""
    pattern = r"```(?:python|py)?\n(.*?)```"
    return re.findall(pattern, text, re.DOTALL)


def validate_python_syntax(code: str) -> Tuple[bool, str]:
    """
    Validate Python code syntax without executing

    Args:
        code: Python code string

    Returns:
        (is_valid, error_message)
    """
    try:
        ast.parse(code)
        return True, "Valid syntax"
    except SyntaxError as e:
        return False, f"Syntax Error at line {e.lineno}: {e.msg}"
    except Exception as e:
        return False, f"Parse Error: {str(e)}"


def extract_thinking(text: str) -> Tuple[str, str]:
    """
    Extract thinking and answer sections from response

    Returns:
        (thinking_text, answer_text)
    """
    thinking_match = re.search(r"<thinking>(.*?)</thinking>", text, re.DOTALL)
    answer_match = re.search(r"<answer>(.*?)</answer>", text, re.DOTALL)

    thinking = thinking_match.group(1).strip() if thinking_match else ""
    answer = answer_match.group(1).strip() if answer_match else text

    return thinking, answer


async def validate_response(response: str, query_type: str) -> Dict[str, Any]:
    """
    Validate AI response for common issues

    Checks:
    - Code syntax if code blocks present
    - Thinking process present for complex queries
    - Response not empty
    - No obvious hallucination patterns

    Args:
        response: Full AI response text
        query_type: "simple" | "factual" | "complex"

    Returns:
        Validation result dict with is_valid, errors, warnings
    """
    validation: Dict[str, Any] = {
        "is_valid": True,
        "errors": [],
        "warnings": [],
        "metadata": {},
    }

    # Check if response is empty
    if not response or len(response.strip()) < 5:
        validation["is_valid"] = False
        validation["errors"].append("Response is empty or too short")
        return validation

    # Extract thinking and answer
    thinking, answer = extract_thinking(response)
    validation["metadata"]["has_thinking"] = bool(thinking)
    validation["metadata"]["has_answer"] = bool(answer)

    # For complex queries, thinking should be present
    if query_type == "complex" and not thinking:
        validation["warnings"].append(
            "Complex query but no reasoning process shown (missing <thinking> tags)"
        )

    # Validate Python code blocks
    code_blocks = extract_code_blocks(response)
    if code_blocks:
        validation["metadata"]["code_blocks_found"] = len(code_blocks)

        for i, code in enumerate(code_blocks):
            is_valid, error = validate_python_syntax(code)
            if not is_valid:
                validation["is_valid"] = False
                validation["errors"].append(f"Code block {i+1}: {error}")
                logger.warning(f"Invalid code in response: {error}")

    # Check for common hallucination patterns
    hallucination_markers = [
        "I don't have access to",
        "I cannot browse",
        "As an AI language model",
        "I apologize, but I don't have",
    ]

    for marker in hallucination_markers:
        if marker.lower() in response.lower():
            validation["warnings"].append(
                f"Potential limitation statement detected: '{marker}'"
            )

    logger.info(
        f"Validation result: {validation['is_valid']}, "
        f"{len(validation['errors'])} errors, "
        f"{len(validation['warnings'])} warnings"
    )

    return validation

