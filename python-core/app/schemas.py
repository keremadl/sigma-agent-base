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
    conversation_id: Optional[str] = None


class ApiKeyRequest(BaseModel):
    model: str
    key: str


class HealthResponse(BaseModel):
    status: str
    memory_initialized: bool
    embedder_loaded: bool


class ConversationResponse(BaseModel):
    id: str
    title: str
    created_at: str
    updated_at: str


class MessageResponse(BaseModel):
    id: str
    conversation_id: str
    role: str
    content: str
    thinking: Optional[str] = None
    created_at: str


class ConversationListResponse(BaseModel):
    conversations: List[ConversationResponse]


class MessageListResponse(BaseModel):
    conversation_id: str
    messages: List[MessageResponse]


class TitleUpdateRequest(BaseModel):
    title: str
