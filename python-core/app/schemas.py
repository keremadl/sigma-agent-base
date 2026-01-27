from typing import List, Literal, Optional
from pydantic import BaseModel


class Message(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    messages: List[Message]
    mode: Literal["auto", "pro", "fast"] = "auto"
    model: Optional[str] = None
    stream: bool = True
    include_thinking: Optional[bool] = None


class ApiKeyRequest(BaseModel):
    model: str
    key: str


class HealthResponse(BaseModel):
    status: str
    memory_initialized: bool
    embedder_loaded: bool
