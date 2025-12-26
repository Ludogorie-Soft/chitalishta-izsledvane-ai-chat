"""API endpoints for chat functionality."""

import asyncio
from typing import AsyncGenerator

import structlog
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.api.chat_schemas import (
    ChatHistoryRequest,
    ChatHistoryResponse,
    ChatMessage,
    ChatRequest,
    ChatResponse,
)
from app.db.database import get_db
from app.rag.chat_memory import get_chat_memory
from app.rag.hallucination_control import HallucinationConfig, HallucinationMode
from app.rag.hybrid_pipeline import get_hybrid_pipeline_service
from app.rag.langchain_callbacks import get_langchain_callback_handler
from app.rag.structured_output import (
    OutputFormat,
    get_structured_output_formatter,
)
from app.services.chat_logger import ChatLogger
from app.services.chat_logger_callbacks import ChatLoggerCallbackHandler

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("/", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    http_request: Request,
    db: Session = Depends(get_db),
):
    """
    Chat endpoint for querying the RAG system.

    Supports:
    - Intent-based routing (SQL, RAG, or Hybrid)
    - Hallucination control modes (low, medium, high tolerance)
    - Chat history management
    - Streaming responses (when stream=True)

    Args:
        request: Chat request with message, conversation_id, mode, and stream flag

    Returns:
        ChatResponse with answer, metadata, and execution details
    """
    # Get request ID from middleware
    request_id = getattr(http_request.state, "request_id", None)
    if not request_id:
        # Fallback: generate one if middleware didn't set it
        import uuid
        request_id = str(uuid.uuid4())

    # Get client information
    client_ip = http_request.client.host if http_request.client else None
    user_agent = http_request.headers.get("user-agent")

    # Initialize chat logger early (conversation_id will be set later)
    chat_logger = ChatLogger(db)
    conversation_id_placeholder = "pending"  # Will be updated after creation

    try:
        # Get or create conversation ID
        memory = get_chat_memory()
        if request.conversation_id:
            if not memory.conversation_exists(request.conversation_id):
                # Create conversation if it doesn't exist
                request.conversation_id = memory.create_conversation()
        else:
            request.conversation_id = memory.create_conversation()

        # Update conversation_id in logger
        conversation_id_placeholder = request.conversation_id

        # Start logging request
        chat_logger.start_request(
            request_id=request_id,
            conversation_id=request.conversation_id,
            user_message=request.message,
            hallucination_mode=request.mode.value if request.mode else "medium",
            output_format=request.output_format.value if request.output_format else "text",
            client_ip=client_ip,
            user_agent=user_agent,
        )

        # Add user message to history
        memory.add_message(
            request.conversation_id, "user", request.message
        )

        # Create hallucination config from mode
        hallucination_config = HallucinationConfig(mode=request.mode)

        # Get conversation context if available
        conversation_context = memory.get_conversation_context(
            request.conversation_id, max_messages=5
        )

        # Enhance query with conversation context if available
        query = request.message
        if conversation_context:
            query = f"Контекст от предишни съобщения:\n{conversation_context}\n\nТекущ въпрос: {request.message}"

        # Create callback handler for chat logging
        chat_logger_callback = ChatLoggerCallbackHandler(chat_logger)
        structured_callback = get_langchain_callback_handler()
        callbacks = [structured_callback, chat_logger_callback]

        # Get hybrid pipeline service with hallucination config and callbacks
        pipeline = get_hybrid_pipeline_service(
            hallucination_config=hallucination_config,
            callbacks=callbacks,
        )

        # Execute query
        result = pipeline.query(query)

        # Extract answer
        answer = result.get("answer", "Не мога да отговоря на този въпрос.")

        # Format structured output if requested
        structured_output = None
        original_answer = answer  # Keep original for history
        if request.output_format and request.output_format != OutputFormat.TEXT:
            formatter = get_structured_output_formatter()
            # Prepare query result for formatter
            query_result = {
                "sql_executed": result.get("sql_executed", False),
                "sql_success": result.get("sql_success", False),
                "sql_answer": answer if result.get("sql_executed") else None,
                "rag_executed": result.get("rag_executed", False),
            }
            structured_output = formatter.format(
                answer, request.output_format, query_result
            )
            # Use formatted answer if available
            if structured_output.get("formatted_answer"):
                answer = structured_output["formatted_answer"]

        # Add assistant message to history (store original answer, not formatted)
        memory.add_message(
            request.conversation_id, "assistant", original_answer
        )

        # Build response
        response = ChatResponse(
            answer=answer,
            conversation_id=request.conversation_id,
            intent=result.get("intent", "rag"),
            routing_confidence=result.get("routing_confidence", 0.5),
            mode=request.mode,
            sql_executed=result.get("sql_executed", False),
            rag_executed=result.get("rag_executed", False),
            metadata={
                "routing_explanation": result.get("routing_explanation"),
                "sql_query": result.get("sql_query"),
                "rag_metadata": result.get("rag_metadata"),
            },
            structured_output=structured_output,
        )

        # Extract SQL query from result
        # It should be directly in result, or in metadata
        sql_query = result.get("sql_query")
        if not sql_query and isinstance(result.get("metadata"), dict):
            sql_query = result.get("metadata", {}).get("sql_query")

        # Log successful request
        chat_logger.log_success(
            answer=answer,
            intent=result.get("intent", "rag"),
            routing_confidence=result.get("routing_confidence", 0.5),
            sql_executed=result.get("sql_executed", False),
            rag_executed=result.get("rag_executed", False),
            sql_query=sql_query,
            metadata=result.get("metadata"),
            structured_output=structured_output,
        )

        return response

    except ValidationError as e:
        logger.error(
            "validation_error",
            error_type="ValidationError",
            error_message=str(e),
            endpoint="chat",
        )
        # Log error to database
        try:
            # Use placeholder conversation_id if not set yet
            if not hasattr(chat_logger, "_conversation_id") or not chat_logger._conversation_id:
                chat_logger.start_request(
                    request_id=request_id,
                    conversation_id=conversation_id_placeholder,
                    user_message=request.message,
                    hallucination_mode=request.mode.value if request.mode else "medium",
                    output_format=request.output_format.value if request.output_format else "text",
                    client_ip=client_ip,
                    user_agent=user_agent,
                )
            chat_logger.log_error(
                error_type="ValidationError",
                error_message=str(e),
                http_status_code=400,
            )
        except Exception:
            pass  # Don't fail if logging fails
        raise HTTPException(status_code=400, detail=f"Invalid request: {str(e)}")
    except Exception as e:
        logger.error(
            "chat_request_error",
            error_type=type(e).__name__,
            error_message=str(e),
            endpoint="chat",
            exc_info=True,
        )
        # Log error to database
        try:
            # Use placeholder conversation_id if not set yet
            if not hasattr(chat_logger, "_conversation_id") or not chat_logger._conversation_id:
                chat_logger.start_request(
                    request_id=request_id,
                    conversation_id=conversation_id_placeholder,
                    user_message=request.message,
                    hallucination_mode=request.mode.value if request.mode else "medium",
                    output_format=request.output_format.value if request.output_format else "text",
                    client_ip=client_ip,
                    user_agent=user_agent,
                )
            chat_logger.log_error(
                error_type=type(e).__name__,
                error_message=str(e),
                http_status_code=500,
            )
        except Exception:
            pass  # Don't fail if logging fails
        raise HTTPException(
            status_code=500, detail=f"Error processing request: {str(e)}"
        )


@router.post("/stream")
async def chat_stream(request: ChatRequest):
    """
    Streaming chat endpoint using Server-Sent Events (SSE).

    Returns a streaming response where tokens are sent as they are generated.

    Args:
        request: Chat request with message, conversation_id, mode

    Returns:
        StreamingResponse with SSE format
    """
    try:
        # Get or create conversation ID
        memory = get_chat_memory()
        if request.conversation_id:
            if not memory.conversation_exists(request.conversation_id):
                memory.create_conversation()
        else:
            request.conversation_id = memory.create_conversation()

        # Add user message to history
        memory.add_message(
            request.conversation_id, "user", request.message
        )

        # Create hallucination config from mode
        hallucination_config = HallucinationConfig(mode=request.mode)

        # Get conversation context if available
        conversation_context = memory.get_conversation_context(
            request.conversation_id, max_messages=5
        )

        # Enhance query with conversation context if available
        query = request.message
        if conversation_context:
            query = f"Контекст от предишни съобщения:\n{conversation_context}\n\nТекущ въпрос: {request.message}"

        # Get hybrid pipeline service with hallucination config
        pipeline = get_hybrid_pipeline_service(
            hallucination_config=hallucination_config
        )

        # Stream response
        async def generate_stream() -> AsyncGenerator[str, None]:
            """Generate SSE stream from pipeline response."""
            try:
                # Execute query (for now, we'll stream the full response)
                # In a more advanced implementation, we could stream tokens as they're generated
                result = pipeline.query(query)

                answer = result.get("answer", "Не мога да отговоря на този въпрос.")

                # Stream answer in chunks (simulate token streaming)
                # In production, this would use LangChain's streaming capabilities
                chunk_size = 10  # Characters per chunk
                for i in range(0, len(answer), chunk_size):
                    chunk = answer[i : i + chunk_size]
                    yield f"data: {chunk}\n\n"
                    await asyncio.sleep(0.01)  # Small delay to simulate streaming

                # Send final metadata
                metadata = {
                    "conversation_id": request.conversation_id,
                    "intent": result.get("intent", "rag"),
                    "routing_confidence": result.get("routing_confidence", 0.5),
                    "mode": request.mode.value,
                    "sql_executed": result.get("sql_executed", False),
                    "rag_executed": result.get("rag_executed", False),
                }
                yield f"data: {metadata}\n\n"
                yield "data: [DONE]\n\n"

                # Add assistant message to history
                memory.add_message(
                    request.conversation_id, "assistant", answer
                )

            except Exception as e:
                logger.error(
                    "stream_generation_error",
                    error_type=type(e).__name__,
                    error_message=str(e),
                    endpoint="chat_stream",
                    exc_info=True,
                )
                yield f"data: {{'error': '{str(e)}'}}\n\n"

        return StreamingResponse(
            generate_stream(), media_type="text/event-stream"
        )

    except ValidationError as e:
        logger.error(
            "validation_error",
            error_type="ValidationError",
            error_message=str(e),
            endpoint="chat_stream",
        )
        raise HTTPException(status_code=400, detail=f"Invalid request: {str(e)}")
    except Exception as e:
        logger.error(
            "chat_stream_request_error",
            error_type=type(e).__name__,
            error_message=str(e),
            endpoint="chat_stream",
            exc_info=True,
        )
        raise HTTPException(
            status_code=500, detail=f"Error processing request: {str(e)}"
        )


@router.post("/history", response_model=ChatHistoryResponse)
async def get_chat_history(request: ChatHistoryRequest):
    """
    Get chat history for a conversation.

    Args:
        request: ChatHistoryRequest with conversation_id

    Returns:
        ChatHistoryResponse with conversation messages
    """
    try:
        memory = get_chat_memory()

        if not memory.conversation_exists(request.conversation_id):
            raise HTTPException(
                status_code=404, detail="Conversation not found"
            )

        messages_data = memory.get_messages(request.conversation_id)
        messages = [
            ChatMessage(role=msg["role"], content=msg["content"])
            for msg in messages_data
        ]

        return ChatHistoryResponse(
            conversation_id=request.conversation_id, messages=messages
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "get_chat_history_error",
            error_type=type(e).__name__,
            error_message=str(e),
            endpoint="chat_history",
            conversation_id=request.conversation_id,
            exc_info=True,
        )
        raise HTTPException(
            status_code=500, detail=f"Error getting history: {str(e)}"
        )


@router.delete("/history/{conversation_id}")
async def delete_chat_history(conversation_id: str):
    """
    Delete chat history for a conversation.

    Args:
        conversation_id: Conversation ID to delete

    Returns:
        Success message
    """
    try:
        memory = get_chat_memory()

        if not memory.conversation_exists(conversation_id):
            raise HTTPException(
                status_code=404, detail="Conversation not found"
            )

        memory.delete_conversation(conversation_id)

        return {"status": "success", "message": "Conversation deleted"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "delete_chat_history_error",
            error_type=type(e).__name__,
            error_message=str(e),
            endpoint="delete_chat_history",
            conversation_id=conversation_id,
            exc_info=True,
        )
        raise HTTPException(
            status_code=500, detail=f"Error deleting history: {str(e)}"
        )



