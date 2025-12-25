"""Schemas for chat API endpoints."""

from typing import List, Optional

from pydantic import BaseModel, Field

from app.rag.hallucination_control import HallucinationMode


class ChatMessage(BaseModel):
    """A single chat message."""

    role: str = Field(..., description="Message role: 'user' or 'assistant'")
    content: str = Field(..., description="Message content")


class ChatRequest(BaseModel):
    """Request for chat endpoint."""

    message: str = Field(..., description="User's message/question in Bulgarian")
    conversation_id: Optional[str] = Field(
        None, description="Optional conversation ID for maintaining chat history"
    )
    mode: Optional[HallucinationMode] = Field(
        HallucinationMode.MEDIUM_TOLERANCE,
        description="Hallucination control mode: 'low', 'medium', or 'high'",
    )
    stream: bool = Field(
        False, description="Whether to stream the response (SSE)"
    )


class ChatResponse(BaseModel):
    """Response from chat endpoint."""

    answer: str = Field(..., description="Assistant's answer")
    conversation_id: str = Field(..., description="Conversation ID for this chat")
    intent: str = Field(..., description="Detected intent: 'sql', 'rag', or 'hybrid'")
    routing_confidence: float = Field(
        ..., description="Confidence in intent classification (0.0-1.0)"
    )
    mode: HallucinationMode = Field(..., description="Hallucination mode used")
    sql_executed: bool = Field(..., description="Whether SQL was executed")
    rag_executed: bool = Field(..., description="Whether RAG was executed")
    metadata: Optional[dict] = Field(
        None, description="Additional metadata about the response"
    )


class ChatHistoryRequest(BaseModel):
    """Request to get chat history."""

    conversation_id: str = Field(..., description="Conversation ID")


class ChatHistoryResponse(BaseModel):
    """Response with chat history."""

    conversation_id: str = Field(..., description="Conversation ID")
    messages: List[ChatMessage] = Field(..., description="List of messages in the conversation")



