import logging
import re

logger = logging.getLogger(__name__)


async def validate_response(response: str, query_type: str) -> dict:
    """
    Validate AI response based on query type

    Args:
        response: The AI-generated response text
        query_type: "simple" | "factual" | "complex"

    Returns:
        Dict with validation results:
        {
            "is_valid": bool,
            "warnings": List[str],
            "errors": List[str]
        }
    """
    warnings = []
    errors = []

    # Basic validation: non-empty response
    if not response or not response.strip():
        errors.append("Response is empty")
        return {
            "is_valid": False,
            "warnings": warnings,
            "errors": errors,
        }

    # Code validation for complex queries
    if query_type == "complex":
        # Check for code blocks
        code_blocks = re.findall(r"```[\s\S]*?```", response)
        if code_blocks:
            # Basic syntax check (very simple)
            for block in code_blocks:
                # Check for common syntax errors
                if block.count("(") != block.count(")"):
                    warnings.append("Possible syntax error: Unmatched parentheses in code block")
                if block.count("[") != block.count("]"):
                    warnings.append("Possible syntax error: Unmatched brackets in code block")
                if block.count("{") != block.count("}"):
                    warnings.append("Possible syntax error: Unmatched braces in code block")

    # Math validation (basic)
    if query_type == "complex":
        # Check for mathematical expressions
        math_patterns = re.findall(r"\d+\s*[+\-*/]\s*\d+", response)
        if math_patterns:
            # Could add actual evaluation here
            pass

    # Hallucination patterns (very basic)
    if "I don't know" in response.lower() or "I cannot" in response.lower():
        # This might be valid, but worth noting
        pass

    is_valid = len(errors) == 0

    return {
        "is_valid": is_valid,
        "warnings": warnings,
        "errors": errors,
    }
