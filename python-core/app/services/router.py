import logging

import litellm

from app.core.prompts import ROUTER_PROMPT, QueryType


logger = logging.getLogger(__name__)


async def classify_query(query: str, api_key: str) -> QueryType:
    """
    Classify user query as simple/factual/complex using Gemini model

    This is the first step in the pipeline - determines which processing path to take:
    - simple: Skip memory, skip search, use cheap model, no thinking
    - factual: Use memory, may trigger search, show thinking
    - complex: Full pipeline with reasoning

    Args:
        query: User's input text
        api_key: API key for the router model (Gemini)

    Returns:
        QueryType: "simple" | "factual" | "complex"
    """
    try:
        prompt = ROUTER_PROMPT.format(query=query)

        response = await litellm.acompletion(
            model="gemini-2.0-flash",  # No prefix - routes to Gemini API
            messages=[
                {
                    "role": "system",
                    "content": "You are a query classifier. Respond with ONLY one word: simple, factual, or complex."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            api_key=api_key,
            custom_llm_provider="gemini",  # Explicit provider - forces Gemini API
            temperature=0,  # Deterministic classification
            max_tokens=50,
        )

        result = response.choices[0].message.content.strip().lower()

        # Validate result
        if "simple" in result:
            logger.info("Query classified as: simple")
            return "simple"  # type: ignore[return-value]
        elif "factual" in result:
            logger.info("Query classified as: factual")
            return "factual"  # type: ignore[return-value]
        else:
            logger.info("Query classified as: complex (default)")
            return "complex"  # Safe default

    except Exception as e:
        logger.error(f"Classification failed: {e}, defaulting to 'complex'")
        return "complex"  # Safe default on error
