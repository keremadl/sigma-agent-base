import asyncio
import atexit
import json
import logging
import os
import signal
from typing import Dict

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from app.core.config import settings
from app.core.prompts import THINKING_PROMPT, SIMPLE_PROMPT, CONTEXT_TEMPLATE
from app.schemas import ChatRequest, ApiKeyRequest, HealthResponse
from app.services.llm import generate_with_thinking, generate_stream
from app.services.memory import memory
from app.services.router import classify_query
from app.services.validator import validate_response


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Sigma Agent Backend",
    description="Local-first AI Agent with Reasoning",
    version="2.0.0",
)

# CORS for Tauri frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict to Tauri's origin
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global state
api_keys: Dict[str, str] = {}  # model_name -> api_key mapping


@app.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Health check endpoint"""
    return HealthResponse(
        status="ok",
        memory_initialized=memory.collection is not None,
        embedder_loaded=memory.embedder is not None,
    )


@app.post("/chat")
async def chat(request: ChatRequest) -> StreamingResponse:
    """
    Main chat endpoint with intelligent routing and reasoning

    Pipeline:
    1. Classify query (simple/factual/complex)
    2. Route to appropriate processing path
    3. Generate response with streaming
    4. Validate response
    5. Store in memory
    """

    last_message = request.messages[-1].content
    api_key = api_keys.get(request.model)

    if not api_key:
        raise HTTPException(
            status_code=401,
            detail=(
                f"API key for model '{request.model}' not configured. "
                f"Use /config/api-key endpoint first."
            ),
        )

    async def event_stream():
        """SSE stream generator"""
        try:
            # STEP 1: Classify query type
            logger.info(f"Classifying query: {last_message[:50]}...")
            query_type = await classify_query(last_message, api_key)

            # Send classification to frontend
            yield (
                "data: "
                + json.dumps({"type": "classification", "query_type": query_type})
                + "\n\n"
            )

            # STEP 2: Route based on query type
            if query_type == "simple":
                # Fast path: No memory, no thinking, use cheap model
                logger.info("Taking SIMPLE path")
                prompt = SIMPLE_PROMPT.format(query=last_message)
                messages = [{"role": "user", "content": prompt}]
                model = "gpt-4o-mini"
                use_thinking = False

            else:
                # Complex/Factual path: Full pipeline
                logger.info(f"Taking {query_type.upper()} path")

                # STEP 2a: Search memory (run in thread to avoid blocking)
                memory_task = asyncio.create_task(
                    asyncio.to_thread(
                        memory.search_memory, last_message, n_results=3
                    )
                )

                # STEP 2b: Search web (placeholder for future Tavily integration)
                search_results = ""
                if query_type == "factual":
                    search_results = "[Web search not yet implemented]"

                # Wait for memory results
                relevant_memories = await memory_task
                memory_context = (
                    "\n".join(relevant_memories)
                    if relevant_memories
                    else "No relevant context found"
                )

                # STEP 2c: Build context block
                context_block = CONTEXT_TEMPLATE.format(
                    memory_context=memory_context,
                    search_results=search_results,
                )

                # STEP 2d: Build thinking prompt
                system_prompt = THINKING_PROMPT.format(
                    context_block=context_block,
                    query=last_message,
                )

                messages = [
                    {"role": "system", "content": system_prompt},
                    *[
                        {"role": m.role, "content": m.content}
                        for m in request.messages
                    ],
                ]
                model = request.model
                use_thinking = request.include_thinking

            # STEP 3: Generate response (streaming)
            logger.info(f"Generating response with model: {model}")
            full_response = ""

            if use_thinking:
                # Stream with thinking/answer parsing
                async for chunk in generate_with_thinking(
                    messages,
                    model,
                    api_key,
                    include_thinking=request.include_thinking,
                ):
                    full_response = chunk["full"]
                    yield (
                        "data: "
                        + json.dumps(
                            {
                                "type": "chunk",
                                "section": chunk["section"],
                                "content": chunk["content"],
                            }
                        )
                        + "\n\n"
                    )
            else:
                # Simple streaming
                async for chunk in generate_stream(messages, model, api_key):
                    full_response += chunk
                    yield (
                        "data: "
                        + json.dumps(
                            {
                                "type": "chunk",
                                "section": "answer",
                                "content": chunk,
                            }
                        )
                        + "\n\n"
                    )

            # STEP 4: Validate response
            logger.info("Validating response...")
            validation = await validate_response(full_response, query_type)
            yield (
                "data: "
                + json.dumps({"type": "validation", "result": validation})
                + "\n\n"
            )

            # STEP 5: Store in memory (skip for simple queries)
            if query_type != "simple":
                memory_text = f"User: {last_message}\n\nAssistant: {full_response}"
                memory_id = memory.add_memory(
                    memory_text,
                    metadata={
                        "model": model,
                        "query_type": query_type,
                        "is_valid": validation["is_valid"],
                    },
                )
                logger.info(f"Stored in memory: {memory_id}")

            # Send completion signal
            yield "data: [DONE]\n\n"

        except Exception as e:
            logger.error(f"Chat error: {e}", exc_info=True)
            yield "data: " + json.dumps({"type": "error", "message": str(e)}) + "\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@app.post("/config/api-key")
async def set_api_key(request: ApiKeyRequest) -> Dict[str, str]:
    """Store API key for a specific model"""
    api_keys[request.model] = request.key
    logger.info(f"API key configured for model: {request.model}")
    return {"status": "ok", "model": request.model}


@app.post("/shutdown")
async def shutdown() -> Dict[str, str]:
    """
    Graceful shutdown endpoint (called by Tauri before killing process)

    This prevents zombie processes on Windows
    """
    logger.info("Shutdown requested, cleaning up...")

    # Give time to send response
    await asyncio.sleep(0.5)

    # Kill self
    os.kill(os.getpid(), signal.SIGTERM)
    return {"status": "shutting down"}


def cleanup() -> None:
    """Called on process exit"""
    logger.info("Cleanup: Closing resources...")
    # ChromaDB client cleanup happens automatically


atexit.register(cleanup)

