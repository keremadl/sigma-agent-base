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

from app.core.config import settings, MODEL_TIERS
from app.core.prompts import THINKING_PROMPT, SIMPLE_PROMPT, CONTEXT_TEMPLATE
from app.schemas import (
    ChatRequest, ApiKeyRequest, HealthResponse,
    ConversationResponse, MessageResponse, ConversationListResponse,
    MessageListResponse, TitleUpdateRequest, Message
)
from app.services.llm import generate_with_thinking, generate_stream
from app.services.memory import memory
from app.services.router import classify_query
from app.services.validator import validate_response
from app.services.database import DatabaseService
import litellm


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
db = DatabaseService()  # Database service instance


def get_api_key(model: str) -> str | None:
    """
    Get API key for a model, handling both prefixed and non-prefixed model names.
    
    This ensures compatibility with keys saved as "gemini/..." or without prefix.
    """
    # Try exact match first
    if model in api_keys:
        return api_keys[model]
    
    # Try with "gemini/" prefix if not present
    prefixed_model = f"gemini/{model}"
    if prefixed_model in api_keys:
        return api_keys[prefixed_model]
    
    # Try without prefix if model has prefix
    if model.startswith("gemini/"):
        clean_model = model.replace("gemini/", "")
        if clean_model in api_keys:
            return api_keys[clean_model]
    
    return None


async def generate_conversation_title(first_message: str, api_key: str, model: str) -> str:
    """
    Generate a conversation title from the first user message using LLM.
    Falls back to first 50 characters if generation fails.
    
    Args:
        first_message: First user message in the conversation
        api_key: API key for the model
        model: Model name to use for title generation (without gemini/ prefix)
        
    Returns:
        Generated title (max 60 chars) or fallback
    """
    try:
        prompt = f"Generate a short title (max 60 characters) for this conversation based on the first message: {first_message}"
        
        # Use gemini/ prefix to force API key method (not Vertex AI)
        gemini_model = f"gemini/{model}" if not model.startswith("gemini/") else model
        
        response = await litellm.acompletion(
            model=gemini_model,
            messages=[{"role": "user", "content": prompt}],
            api_key=api_key,
            custom_llm_provider="gemini",  # Explicitly use Gemini API (not Vertex AI)
            max_tokens=20,
            temperature=0.7,
        )
        
        # Check if content is None before calling strip()
        content = response.choices[0].message.content
        if content is None:
            logger.warning("Title generation returned None content, using fallback")
            return first_message[:50].strip() if len(first_message) > 50 else first_message.strip()
        
        title = content.strip()
        # Ensure max 60 chars
        if len(title) > 60:
            title = title[:60].rstrip()
        
        if title:
            return title
    except Exception as e:
        logger.warning(f"Title generation failed: {e}, using fallback")
    
    # Fallback to first 50 chars
    return first_message[:50].strip() if len(first_message) > 50 else first_message.strip()


@app.on_event("startup")
async def startup():
    """Log configuration on startup"""
    logger.info(f"Loaded MODEL_TIERS: {MODEL_TIERS}")
    db.initialize()
    logger.info("Application startup complete")


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

    # Handle conversation management
    conversation_id = request.conversation_id
    
    # If no conversation_id provided, create new conversation
    if not conversation_id:
        # Generate title from first message
        router_model = MODEL_TIERS["auto"]
        router_api_key = get_api_key(router_model) or next(iter(api_keys.values()), None)
        if router_api_key:
            title = await generate_conversation_title(last_message, router_api_key, router_model)
        else:
            title = last_message[:50].strip() if len(last_message) > 50 else last_message.strip()
        
        conversation_id = db.create_conversation(title)
        logger.info(f"Created new conversation: {conversation_id}")
    else:
        # Verify conversation exists
        conversation = db.get_conversation(conversation_id)
        if not conversation:
            raise HTTPException(status_code=404, detail=f"Conversation {conversation_id} not found")
        
        # Load previous messages from DB for context
        db_messages = db.get_messages(conversation_id)
        if db_messages:
            # Prepend DB messages to request messages (excluding the last user message which is in request)
            # Convert DB messages to Message format
            previous_messages = [
                {"role": msg["role"], "content": msg["content"]}
                for msg in db_messages
            ]
            # Merge with request messages (request.messages already contains the new user message)
            request.messages = [
                Message(role=msg["role"], content=msg["content"])
                for msg in previous_messages
            ] + request.messages
            logger.info(f"Loaded {len(previous_messages)} previous messages for conversation {conversation_id}")

    # Ensure at least one API key is available for router classification
    if not api_keys:
        raise HTTPException(
            status_code=401,
            detail="No API keys configured. Use /config/api-key endpoint first.",
        )

    mode = request.mode or "auto"

    # Get API key for classification (use auto tier model)
    router_model = MODEL_TIERS["auto"]
    router_api_key = get_api_key(router_model)

    if not router_api_key:
        # Fallback to any available key
        if api_keys:
            router_api_key = next(iter(api_keys.values()))
            logger.warning(
                f"No API key for router model '{router_model}', using fallback key"
            )
        else:
            raise HTTPException(
                status_code=401,
                detail="No API keys configured. Use /config/api-key endpoint first.",
            )

    # STEP 1: Classify query type
    logger.info(f"Classifying query: {last_message[:50]}...")
    query_type = await classify_query(last_message, router_api_key)

    # STEP 2: Determine base model & thinking behaviour from mode + query type
    if mode == "auto":
        if query_type == "simple":
            base_model = MODEL_TIERS["fast"]
            use_thinking = False
        else:
            base_model = MODEL_TIERS["auto"]
            use_thinking = True
    elif mode == "pro":
        base_model = MODEL_TIERS["pro"]
        use_thinking = True
    else:  # fast
        base_model = MODEL_TIERS["fast"]
        use_thinking = False

    # Allow explicit model override from client
    model = request.model or base_model

    # Final thinking flag (client can override)
    include_thinking = (
        request.include_thinking
        if request.include_thinking is not None
        else use_thinking
    )

    # STEP 3: Look up API key for the determined model
    api_key = get_api_key(model)
    if not api_key:
        raise HTTPException(
            status_code=401,
            detail=(
                f"API key for '{model}' not configured. "
                f"Use /config/api-key endpoint first."
            ),
        )

    # STEP 4: Build messages / context based on query type and mode
    if query_type == "simple" and mode != "pro":
        # Fast path: No memory, no thinking, use simple prompt
        logger.info("Taking SIMPLE path")
        prompt = SIMPLE_PROMPT.format(query=last_message)
        messages = [{"role": "user", "content": prompt}]
        effective_use_thinking = False
        context_block = None
    else:
        # Complex/Factual path: Full pipeline
        logger.info(f"Taking {query_type.upper()} path (mode={mode})")

        # Search memory (run in thread to avoid blocking)
        memory_task = asyncio.create_task(
            asyncio.to_thread(memory.search_memory, last_message, n_results=3)
        )

        # Search web (placeholder for future Tavily integration)
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

        # Build context block (not currently injected into prompt text,
        # but kept for future use)
        context_block = CONTEXT_TEMPLATE.format(
            memory_context=memory_context,
            search_results=search_results,
        )

        system_prompt = THINKING_PROMPT

        messages = [
            {"role": "system", "content": system_prompt},
            *[{"role": m.role, "content": m.content} for m in request.messages],
        ]
        effective_use_thinking = include_thinking

    async def event_stream():
        """SSE stream generator"""
        thinking_content = ""
        answer_content = ""
        
        try:
            # Send conversation_id and classification to frontend first
            yield (
                "data: "
                + json.dumps({
                    "type": "conversation",
                    "conversation_id": conversation_id
                })
                + "\n\n"
            )
            yield (
                "data: "
                + json.dumps({"type": "classification", "query_type": query_type})
                + "\n\n"
            )

            # STEP 5: Generate response (streaming)
            logger.info(f"Generating response with model: {model}")
            full_response = ""

            if effective_use_thinking:
                # Stream with thinking/answer parsing
                async for chunk in generate_with_thinking(
                    messages,
                    model,
                    api_key,
                    include_thinking=include_thinking,
                ):
                    full_response = chunk["full"]
                    section = chunk["section"]
                    content = chunk["content"]
                    
                    # Track thinking and answer separately
                    if section == "thinking":
                        thinking_content += content
                    elif section == "answer":
                        answer_content += content
                    
                    yield (
                        "data: "
                        + json.dumps(
                            {
                                "type": "chunk",
                                "section": section,
                                "content": content,
                            }
                        )
                        + "\n\n"
                    )
            else:
                # Simple streaming
                async for chunk in generate_stream(messages, model, api_key):
                    chunk_content = chunk.get("content", "")
                    full_response += chunk_content
                    answer_content += chunk_content
                    yield (
                        "data: "
                        + json.dumps(
                            {
                                "type": "chunk",
                                "section": "answer",
                                "content": chunk_content,
                            }
                        )
                        + "\n\n"
                    )

            # STEP 6: Validate response
            logger.info("Validating response...")
            validation = await validate_response(full_response, query_type)
            yield (
                "data: "
                + json.dumps({"type": "validation", "result": validation})
                + "\n\n"
            )

            # STEP 7: Save messages to database
            thinking_to_store = None
            answer_to_store = full_response.strip()
            try:
                # Save user message
                db.add_message(conversation_id, "user", last_message)
                
                # Save assistant message (with thinking if present)
                thinking_to_store = thinking_content.strip() if thinking_content.strip() else None
                answer_to_store = answer_content.strip() if answer_content.strip() else full_response.strip()
                db.add_message(
                    conversation_id,
                    "assistant",
                    answer_to_store,
                    thinking=thinking_to_store
                )
                logger.info(f"Saved messages to conversation {conversation_id}")
            except Exception as db_error:
                logger.error(f"Failed to save messages to database: {db_error}", exc_info=True)
                # Don't fail the request, just log the error

            # STEP 8: Store in memory (skip for simple queries)
            if query_type != "simple":
                memory_text = f"User: {last_message}\n\nAssistant: {answer_to_store}"
                memory_id = memory.add_memory(
                    memory_text,
                    metadata={
                        "model": model,
                        "query_type": query_type,
                        "is_valid": validation["is_valid"],
                        "conversation_id": conversation_id,
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


@app.get("/conversations", response_model=ConversationListResponse)
async def get_conversations(limit: int = 50) -> ConversationListResponse:
    """Get list of conversations (most recent first)"""
    try:
        conversations = db.get_conversations(limit=limit)
        return ConversationListResponse(
            conversations=[
                ConversationResponse(**conv) for conv in conversations
            ]
        )
    except Exception as e:
        logger.error(f"Failed to get conversations: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to retrieve conversations")


@app.get("/conversations/{conversation_id}", response_model=MessageListResponse)
async def get_conversation(conversation_id: str) -> MessageListResponse:
    """Get conversation metadata and all messages"""
    try:
        conversation = db.get_conversation(conversation_id)
        if not conversation:
            raise HTTPException(status_code=404, detail=f"Conversation {conversation_id} not found")
        
        messages = db.get_messages(conversation_id)
        return MessageListResponse(
            conversation_id=conversation_id,
            messages=[MessageResponse(**msg) for msg in messages]
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get conversation: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to retrieve conversation")


@app.delete("/conversations/{conversation_id}")
async def delete_conversation(conversation_id: str) -> Dict[str, str]:
    """Delete a conversation and all its messages"""
    try:
        db.delete_conversation(conversation_id)
        return {"status": "ok", "conversation_id": conversation_id}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to delete conversation: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to delete conversation")


@app.patch("/conversations/{conversation_id}/title", response_model=ConversationResponse)
async def update_conversation_title(
    conversation_id: str,
    request: TitleUpdateRequest
) -> ConversationResponse:
    """Update conversation title"""
    try:
        db.update_conversation_title(conversation_id, request.title)
        conversation = db.get_conversation(conversation_id)
        if not conversation:
            raise HTTPException(status_code=404, detail=f"Conversation {conversation_id} not found")
        return ConversationResponse(**conversation)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to update conversation title: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to update conversation title")


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
