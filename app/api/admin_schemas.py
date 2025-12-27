"""Pydantic schemas for admin endpoints."""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


class ConversationSummary(BaseModel):
    """Summary of a conversation grouped by conversation_id."""

    conversation_id: str = Field(..., description="Unique conversation identifier")
    first_message: str = Field(..., description="First user message in the conversation")
    last_message_timestamp: datetime = Field(
        ..., description="Timestamp of the most recent message"
    )
    message_count: int = Field(..., description="Total number of messages in the conversation")
    total_cost_usd: Optional[float] = Field(
        None, description="Sum of costs for all messages in the conversation (USD)"
    )
    intents_used: List[str] = Field(
        ..., description="List of unique intents used (sql, rag, hybrid)"
    )
    has_errors: bool = Field(
        ..., description="Whether any errors occurred in the conversation"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "conversation_id": "123e4567-e89b-12d3-a456-426614174000",
                "first_message": "Колко читалища има в Пловдив?",
                "last_message_timestamp": "2025-01-15T10:30:00Z",
                "message_count": 5,
                "total_cost_usd": 0.0025,
                "intents_used": ["sql", "rag"],
                "has_errors": False,
            }
        }
    )


class ConversationListResponse(BaseModel):
    """Response for GET /admin/chat - list of conversation summaries."""

    conversations: List[ConversationSummary] = Field(
        ..., description="List of conversation summaries"
    )
    total: int = Field(..., description="Total number of conversations (before pagination)")
    limit: int = Field(..., description="Number of results per page")
    offset: int = Field(..., description="Number of results skipped")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "conversations": [
                    {
                        "conversation_id": "123e4567-e89b-12d3-a456-426614174000",
                        "first_message": "Колко читалища има в Пловдив?",
                        "last_message_timestamp": "2025-01-15T10:30:00Z",
                        "message_count": 5,
                        "total_cost_usd": 0.0025,
                        "intents_used": ["sql", "rag"],
                        "has_errors": False,
                    }
                ],
                "total": 100,
                "limit": 20,
                "offset": 0,
            }
        }
    )


class ChatLogDetail(BaseModel):
    """Detailed chat log entry for a specific conversation."""

    id: int = Field(..., description="Chat log ID")
    request_id: str = Field(..., description="Unique request identifier")
    request_timestamp: datetime = Field(..., description="Timestamp of the request")
    user_message: str = Field(..., description="User's message")
    answer: Optional[str] = Field(None, description="System's answer")
    intent: Optional[str] = Field(None, description="Detected intent (sql/rag/hybrid)")
    routing_confidence: Optional[float] = Field(
        None, description="Confidence score for routing decision"
    )
    sql_executed: bool = Field(..., description="Whether SQL was executed")
    rag_executed: bool = Field(..., description="Whether RAG was executed")
    sql_query: Optional[str] = Field(None, description="SQL query that was executed")
    response_time_ms: Optional[int] = Field(None, description="Response time in milliseconds")
    total_input_tokens: Optional[int] = Field(None, description="Total input tokens used")
    total_output_tokens: Optional[int] = Field(None, description="Total output tokens used")
    total_tokens: Optional[int] = Field(None, description="Total tokens used")
    cost_usd: Optional[float] = Field(None, description="Cost in USD")
    llm_model: Optional[str] = Field(None, description="Primary LLM model used")
    llm_operations: Optional[dict] = Field(
        None, description="Detailed LLM operations (JSONB)"
    )
    response_metadata: Optional[dict] = Field(
        None, description="Response metadata (routing explanation, etc.)"
    )
    structured_output: Optional[dict] = Field(
        None, description="Structured output if requested"
    )
    error_occurred: bool = Field(..., description="Whether an error occurred")
    error_type: Optional[str] = Field(None, description="Type of error if occurred")
    error_message: Optional[str] = Field(None, description="Error message if occurred")
    http_status_code: Optional[int] = Field(None, description="HTTP status code")
    client_ip: Optional[str] = Field(None, description="Client IP address")
    user_agent: Optional[str] = Field(None, description="User agent string")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": 1,
                "request_id": "req-123",
                "request_timestamp": "2025-01-15T10:30:00Z",
                "user_message": "Колко читалища има в Пловдив?",
                "answer": "В Пловдив има 45 читалища.",
                "intent": "sql",
                "routing_confidence": 0.95,
                "sql_executed": True,
                "rag_executed": False,
                "sql_query": "SELECT COUNT(*) FROM chitalishte WHERE town = 'Пловдив'",
                "response_time_ms": 250,
                "total_input_tokens": 100,
                "total_output_tokens": 50,
                "total_tokens": 150,
                "cost_usd": 0.0005,
                "llm_model": "gpt-4o-mini",
                "error_occurred": False,
            }
        }
    )


class ConversationDetailResponse(BaseModel):
    """Response for GET /admin/chat/{conversation_id} - detailed chat logs for a conversation."""

    conversation_id: str = Field(..., description="Conversation identifier")
    chat_logs: List[ChatLogDetail] = Field(
        ..., description="List of chat log entries for this conversation"
    )
    total_messages: int = Field(..., description="Total number of messages in the conversation")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "conversation_id": "123e4567-e89b-12d3-a456-426614174000",
                "total_messages": 5,
                "chat_logs": [
                    {
                        "id": 1,
                        "request_id": "req-123",
                        "request_timestamp": "2025-01-15T10:30:00Z",
                        "user_message": "Колко читалища има в Пловдив?",
                        "answer": "В Пловдив има 45 читалища.",
                        "intent": "sql",
                        "sql_executed": True,
                        "rag_executed": False,
                    }
                ],
            }
        }
    )

