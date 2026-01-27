from pydantic import BaseModel, Field
from typing import List, Optional, Literal


class Message(BaseModel):
    role: Literal["user", "assistant", "system"]
    content: str


class ChatRequest(BaseModel):
    messages: List[Message]
    model: str = "gpt-4o-mini"
    stream: bool = True
    include_thinking: bool = True  # Show thinking process to user


class ChatResponse(BaseModel):
    response: str
    model: str
    query_type: Optional[str] = None
    thinking: Optional[str] = None
    validation: Optional[dict] = None


class ApiKeyRequest(BaseModel):
    model: str = Field(
        ...,
        description=(
            "Model name (e.g., 'gpt-4o-mini', 'claude-3-5-sonnet-20241022')"
        ),
    )
    key: str = Field(..., description="API key")


class HealthResponse(BaseModel):
    status: str
    memory_initialized: bool
    embedder_loaded: bool

