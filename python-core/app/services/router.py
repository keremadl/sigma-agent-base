import os
import logging

import litellm

from app.core.prompts import ROUTER_PROMPT, QueryType


logger = logging.getLogger(__name__)


async def classify_query(query: str, api_key: str) -> QueryType:
    """
    Classify user query as simple/factual/complex using a fast, cheap model

    This is the first step in the pipeline - determines which processing path to take:
    - simple: Skip memory, skip search, use cheap model, no thinking
    - factual: Use memory, may trigger search, show thinking
    - complex: Full pipeline with reasoning

    Args:
        query: User's input text
        api_key: API key for the router model

    Returns:
        QueryType: "simple" | "factual" | "complex"
    """
    try:
        # Set API key for router model
        os.environ["OPENAI_API_KEY"] = api_key  # Assuming OpenAI for router

        prompt = ROUTER_PROMPT.format(query=query)

        response = await litellm.acompletion(
            model="gpt-4o-mini",  # Fast and cheap
            messages=[{"role": "user", "content": prompt}],
            temperature=0,  # Deterministic classification
            max_tokens=10,
        )

        result = response.choices[0].message.content.strip().lower()

        # Validate result
        if result in ["simple", "factual", "complex"]:
            logger.info(f"Query classified as: {result}")
            return result  # type: ignore[return-value]
        else:
            logger.warning(
                f"Invalid classification '{result}', defaulting to 'complex'"
            )
            return "complex"  # Safe default

    except Exception as e:
        logger.error(f"Classification failed: {e}, defaulting to 'complex'")
        return "complex"  # Safe default on error

