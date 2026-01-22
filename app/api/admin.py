"""API endpoints for administrator features."""

from datetime import datetime
from typing import List, Optional

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.api.admin_schemas import (
    ChatLogDetail,
    ConversationDetailResponse,
    ConversationListResponse,
    ConversationSummary,
    RagDebugLogDetail,
    RagDebugLogListResponse,
    RagDebugLogSummary,
)
from app.core.auth import CurrentUser, require_administrator
from app.db.database import get_db
from app.db.models import ChatLog, RagDebugLog

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/admin", tags=["Admin API"])


@router.get("/chat", response_model=ConversationListResponse)
async def list_conversations(
    limit: int = Query(default=20, ge=1, le=100, description="Number of results per page"),
    offset: int = Query(default=0, ge=0, description="Number of results to skip"),
    start_date: Optional[datetime] = Query(
        None, description="Filter conversations from this date (ISO format)"
    ),
    end_date: Optional[datetime] = Query(
        None, description="Filter conversations until this date (ISO format)"
    ),
    has_errors: Optional[bool] = Query(
        None, description="Filter by whether conversations have errors"
    ),
    intent: Optional[str] = Query(
        None, description="Filter by intent type (sql, rag, hybrid)"
    ),
    current_user: CurrentUser = Depends(require_administrator),
    db: Session = Depends(get_db),
):
    """
    Get list of all conversations with summary data.

    Returns brief chat data from chat_logs table, grouped by conversation_id.
    Supports pagination and filtering by date range, errors, and intent.

    **Authentication**: Requires administrator role (placeholder for now).
    """
    try:
        # Build base query to get all conversation IDs
        base_query = db.query(ChatLog.conversation_id)

        # Apply date filters
        if start_date:
            base_query = base_query.filter(ChatLog.request_timestamp >= start_date)
        if end_date:
            base_query = base_query.filter(ChatLog.request_timestamp <= end_date)
        if intent:
            base_query = base_query.filter(ChatLog.intent == intent)

        # Get all unique conversation IDs (we'll filter by has_errors after aggregation)
        all_conversation_ids = [row[0] for row in base_query.distinct().all()]

        if not all_conversation_ids:
            return ConversationListResponse(
                conversations=[], total=0, limit=limit, offset=offset
            )

        # For each conversation, get aggregated data
        all_conversations = []
        for conv_id in all_conversation_ids:
            # Get all logs for this conversation
            logs = (
                db.query(ChatLog)
                .filter(ChatLog.conversation_id == conv_id)
                .order_by(ChatLog.request_timestamp.asc())
                .all()
            )

            if not logs:
                continue

            # Aggregate data
            first_log = logs[0]
            last_log = logs[-1]

            # Get unique intents
            intents_used = list(
                set(log.intent for log in logs if log.intent is not None)
            )

            # Check for errors
            has_errors_flag = any(log.error_occurred for log in logs)

            # Calculate total cost
            total_cost = sum(
                float(log.cost_usd) if log.cost_usd is not None else 0.0 for log in logs
            )

            all_conversations.append(
                ConversationSummary(
                    conversation_id=conv_id,
                    first_message=first_log.user_message,
                    last_message_timestamp=last_log.request_timestamp,
                    message_count=len(logs),
                    total_cost_usd=total_cost if total_cost > 0 else None,
                    intents_used=intents_used,
                    has_errors=has_errors_flag,
                )
            )

        # Apply has_errors filter after aggregation (if specified)
        if has_errors is not None:
            all_conversations = [
                c for c in all_conversations if c.has_errors == has_errors
            ]

        # Sort by last_message_timestamp (most recent first)
        all_conversations.sort(key=lambda x: x.last_message_timestamp, reverse=True)

        # Apply pagination
        total = len(all_conversations)
        conversations = all_conversations[offset : offset + limit]

        return ConversationListResponse(
            conversations=conversations, total=total, limit=limit, offset=offset
        )

    except Exception as e:
        logger.error("error_listing_conversations", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error listing conversations: {str(e)}")


@router.get("/chat/{conversation_id}", response_model=ConversationDetailResponse)
async def get_conversation_details(
    conversation_id: str,
    current_user: CurrentUser = Depends(require_administrator),
    db: Session = Depends(get_db),
):
    """
    Get detailed chat logs for a specific conversation.

    Returns all chat_logs rows for the given conversation_id, ordered chronologically.

    **Authentication**: Requires administrator role (placeholder for now).
    """
    try:
        # Get all logs for this conversation
        logs = (
            db.query(ChatLog)
            .filter(ChatLog.conversation_id == conversation_id)
            .order_by(ChatLog.request_timestamp.asc())
            .all()
        )

        if not logs:
            raise HTTPException(
                status_code=404, detail=f"Conversation {conversation_id} not found"
            )

        # Convert to response models
        chat_logs = []
        for log in logs:
            chat_logs.append(
                ChatLogDetail(
                    id=log.id,
                    request_id=log.request_id,
                    request_timestamp=log.request_timestamp,
                    user_message=log.user_message,
                    answer=log.answer,
                    intent=log.intent,
                    routing_confidence=(
                        float(log.routing_confidence) if log.routing_confidence else None
                    ),
                    sql_executed=log.sql_executed,
                    rag_executed=log.rag_executed,
                    sql_query=log.sql_query,
                    response_time_ms=log.response_time_ms,
                    total_input_tokens=log.total_input_tokens,
                    total_output_tokens=log.total_output_tokens,
                    total_tokens=log.total_tokens,
                    cost_usd=float(log.cost_usd) if log.cost_usd is not None else None,
                    llm_model=log.llm_model,
                    llm_operations=log.llm_operations,
                    response_metadata=log.response_metadata,
                    structured_output=log.structured_output,
                    error_occurred=log.error_occurred,
                    error_type=log.error_type,
                    error_message=log.error_message,
                    http_status_code=log.http_status_code,
                    client_ip=log.client_ip,
                    user_agent=log.user_agent,
                )
            )

        return ConversationDetailResponse(
            conversation_id=conversation_id,
            chat_logs=chat_logs,
            total_messages=len(chat_logs),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "error_getting_conversation_details",
            conversation_id=conversation_id,
            error=str(e),
            exc_info=True,
        )
        raise HTTPException(
            status_code=500, detail=f"Error getting conversation details: {str(e)}"
        )


@router.get("/rag-debug/{request_id}", response_model=RagDebugLogDetail)
async def get_rag_debug_log(
    request_id: str,
    current_user: CurrentUser = Depends(require_administrator),
    db: Session = Depends(get_db),
):
    """
    Get full RAG debug log for a specific request.

    Returns complete debug information including retrieved documents, prompts, and responses.

    **Authentication**: Requires administrator role (placeholder for now).
    """
    try:
        rag_debug_log = (
            db.query(RagDebugLog).filter(RagDebugLog.request_id == request_id).first()
        )

        if not rag_debug_log:
            raise HTTPException(
                status_code=404, detail=f"RAG debug log not found for request_id: {request_id}"
            )

        return RagDebugLogDetail(
            id=rag_debug_log.id,
            request_id=rag_debug_log.request_id,
            conversation_id=rag_debug_log.conversation_id,
            user_query=rag_debug_log.user_query,
            retrieved_documents=rag_debug_log.retrieved_documents,
            formatted_context=rag_debug_log.formatted_context,
            prompt_template_used=rag_debug_log.prompt_template_used,
            llm_prompt_sent=rag_debug_log.llm_prompt_sent,
            retrieval_metadata=rag_debug_log.retrieval_metadata,
            db_doc_count=rag_debug_log.db_doc_count,
            analysis_doc_count=rag_debug_log.analysis_doc_count,
            retrieval_duration_ms=float(rag_debug_log.retrieval_duration_ms)
            if rag_debug_log.retrieval_duration_ms is not None
            else None,
            llm_response_received=rag_debug_log.llm_response_received,
            fallback_llm_used=rag_debug_log.fallback_llm_used,
            created_at=rag_debug_log.created_at,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "error_getting_rag_debug_log",
            request_id=request_id,
            error=str(e),
            exc_info=True,
        )
        raise HTTPException(
            status_code=500, detail=f"Error getting RAG debug log: {str(e)}"
        )


@router.get("/rag-debug", response_model=RagDebugLogListResponse)
async def list_rag_debug_logs(
    limit: int = Query(default=50, ge=1, le=100, description="Number of results per page"),
    offset: int = Query(default=0, ge=0, description="Number of results to skip"),
    conversation_id: Optional[str] = Query(
        None, description="Filter by conversation ID"
    ),
    start_date: Optional[datetime] = Query(
        None, description="Filter debug logs from this date (ISO format)"
    ),
    end_date: Optional[datetime] = Query(
        None, description="Filter debug logs until this date (ISO format)"
    ),
    current_user: CurrentUser = Depends(require_administrator),
    db: Session = Depends(get_db),
):
    """
    Get list of RAG debug logs with summary data.

    Supports pagination and filtering by conversation_id and date range.

    **Authentication**: Requires administrator role (placeholder for now).
    """
    try:
        # Build base query
        query = db.query(RagDebugLog)

        # Apply filters
        if conversation_id:
            query = query.filter(RagDebugLog.conversation_id == conversation_id)
        if start_date:
            query = query.filter(RagDebugLog.created_at >= start_date)
        if end_date:
            query = query.filter(RagDebugLog.created_at <= end_date)

        # Get total count
        total = query.count()

        # Apply pagination and ordering
        debug_logs = (
            query.order_by(RagDebugLog.created_at.desc())
            .limit(limit)
            .offset(offset)
            .all()
        )

        # Convert to summary models
        debug_log_summaries = [
            RagDebugLogSummary(
                id=log.id,
                request_id=log.request_id,
                conversation_id=log.conversation_id,
                user_query=log.user_query,
                db_doc_count=log.db_doc_count,
                analysis_doc_count=log.analysis_doc_count,
                created_at=log.created_at,
            )
            for log in debug_logs
        ]

        return RagDebugLogListResponse(
            debug_logs=debug_log_summaries, total=total, limit=limit, offset=offset
        )

    except Exception as e:
        logger.error(
            "error_listing_rag_debug_logs",
            error=str(e),
            exc_info=True,
        )
        raise HTTPException(
            status_code=500, detail=f"Error listing RAG debug logs: {str(e)}"
        )

