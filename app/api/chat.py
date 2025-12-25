"""API endpoints for chat functionality."""

import asyncio
import logging
from typing import AsyncGenerator

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import ValidationError

from app.api.chat_schemas import (
    ChatHistoryRequest,
    ChatHistoryResponse,
    ChatMessage,
    ChatRequest,
    ChatResponse,
)
from app.rag.chat_memory import get_chat_memory
from app.rag.hallucination_control import HallucinationConfig, HallucinationMode
from app.rag.hybrid_pipeline import get_hybrid_pipeline_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("/", response_model=ChatResponse)
async def chat(request: ChatRequest):
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
    try:
        # Get or create conversation ID
        memory = get_chat_memory()
        if request.conversation_id:
            if not memory.conversation_exists(request.conversation_id):
                # Create conversation if it doesn't exist
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

        # Execute query
        result = pipeline.query(query)

        # Extract answer
        answer = result.get("answer", "Не мога да отговоря на този въпрос.")

        # Add assistant message to history
        memory.add_message(
            request.conversation_id, "assistant", answer
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
        )

        return response

    except ValidationError as e:
        logger.error(f"Validation error in chat request: {e}")
        raise HTTPException(status_code=400, detail=f"Invalid request: {str(e)}")
    except Exception as e:
        logger.error(f"Error processing chat request: {e}", exc_info=True)
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
                logger.error(f"Error in stream generation: {e}", exc_info=True)
                yield f"data: {{'error': '{str(e)}'}}\n\n"

        return StreamingResponse(
            generate_stream(), media_type="text/event-stream"
        )

    except ValidationError as e:
        logger.error(f"Validation error in chat stream request: {e}")
        raise HTTPException(status_code=400, detail=f"Invalid request: {str(e)}")
    except Exception as e:
        logger.error(f"Error processing chat stream request: {e}", exc_info=True)
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
        logger.error(f"Error getting chat history: {e}", exc_info=True)
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
        logger.error(f"Error deleting chat history: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Error deleting history: {str(e)}"
        )



