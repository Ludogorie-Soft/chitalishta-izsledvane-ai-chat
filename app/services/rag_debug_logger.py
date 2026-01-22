"""Service for logging RAG debug information to database."""

import asyncio
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import structlog
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.models import RagDebugLog

logger = structlog.get_logger(__name__)


class RagDebugLogger:
    """Service for logging RAG debug information."""

    def __init__(self, db: Session):
        """
        Initialize RAG debug logger.

        Args:
            db: Database session
        """
        self.db = db
        self._debug_data: Optional[Dict[str, Any]] = None

    def start_debug(
        self,
        request_id: str,
        conversation_id: str,
        user_query: str,
    ) -> None:
        """
        Start collecting RAG debug information.

        Args:
            request_id: Unique request ID
            conversation_id: Conversation ID
            user_query: User's query/question
        """
        if not settings.rag_debug_logging_enabled:
            return

        self._debug_data = {
            "request_id": request_id,
            "conversation_id": conversation_id,
            "user_query": user_query,
            "retrieved_documents": None,
            "formatted_context": None,
            "prompt_template_used": None,
            "llm_prompt_sent": None,
            "retrieval_metadata": None,
            "db_doc_count": None,
            "analysis_doc_count": None,
            "retrieval_duration_ms": None,
            "llm_response_received": None,
            "fallback_llm_used": False,
        }

    def set_retrieved_documents(
        self,
        documents: List[Any],
        retrieval_metadata: Optional[Dict[str, Any]] = None,
        retrieval_duration_ms: Optional[float] = None,
    ) -> None:
        """
        Set retrieved documents (with summaries).

        Args:
            documents: List of retrieved document objects
            retrieval_metadata: Optional retrieval metadata
            retrieval_duration_ms: Optional retrieval duration in milliseconds
        """
        if not settings.rag_debug_logging_enabled or not self._debug_data:
            return

        # Create summaries (first 500 chars) for each document
        document_summaries = []
        db_count = 0
        analysis_count = 0

        for doc in documents:
            # Extract content
            content = doc.page_content if hasattr(doc, "page_content") else str(doc)
            full_length = len(content)
            content_summary = content[:500] if len(content) > 500 else content

            # Extract metadata
            metadata = doc.metadata if hasattr(doc, "metadata") else {}
            source = metadata.get("source", "unknown")

            # Count by source
            if source == "database":
                db_count += 1
            elif source == "analysis_document":
                analysis_count += 1

            document_summaries.append(
                {
                    "content_summary": content_summary,
                    "full_length": full_length,
                    "metadata": metadata,
                    "source": source,
                }
            )

        self._debug_data["retrieved_documents"] = document_summaries
        self._debug_data["db_doc_count"] = db_count
        self._debug_data["analysis_doc_count"] = analysis_count
        self._debug_data["retrieval_metadata"] = retrieval_metadata or {}
        self._debug_data["retrieval_duration_ms"] = retrieval_duration_ms

    def set_formatted_context(self, formatted_context: str) -> None:
        """
        Set formatted context sent to LLM.

        Args:
            formatted_context: Formatted context string
        """
        if not settings.rag_debug_logging_enabled or not self._debug_data:
            return

        self._debug_data["formatted_context"] = formatted_context

    def set_prompt_template(self, prompt_template: str) -> None:
        """
        Set prompt template used.

        Args:
            prompt_template: Prompt template string
        """
        if not settings.rag_debug_logging_enabled or not self._debug_data:
            return

        self._debug_data["prompt_template_used"] = prompt_template

    def set_llm_prompt(self, llm_prompt: str) -> None:
        """
        Set actual prompt sent to LLM.

        Args:
            llm_prompt: Full prompt string sent to LLM
        """
        if not settings.rag_debug_logging_enabled or not self._debug_data:
            return

        self._debug_data["llm_prompt_sent"] = llm_prompt

    def set_llm_response(self, llm_response: str) -> None:
        """
        Set raw LLM response.

        Args:
            llm_response: Raw LLM response before post-processing
        """
        if not settings.rag_debug_logging_enabled or not self._debug_data:
            return

        self._debug_data["llm_response_received"] = llm_response

    def set_fallback_used(self, used: bool = True) -> None:
        """
        Set whether fallback LLM was used.

        Args:
            used: Whether fallback LLM was used
        """
        if not settings.rag_debug_logging_enabled or not self._debug_data:
            return

        self._debug_data["fallback_llm_used"] = used

    async def log_async(self) -> None:
        """
        Log RAG debug information to database asynchronously.

        This should be called as a background task to avoid blocking the request.
        Creates a new database session for thread safety.
        """
        if not settings.rag_debug_logging_enabled or not self._debug_data:
            return

        # Run in thread pool to avoid blocking
        # Create a new session for thread safety
        await asyncio.to_thread(self._log_sync)

    def _log_sync(self) -> None:
        """Synchronous logging (called from async context via thread pool)."""
        if not self._debug_data:
            return

        # Create a new database session for this thread
        from app.db.database import SessionLocal
        db = SessionLocal()

        try:
            rag_debug_log = RagDebugLog(
                request_id=self._debug_data["request_id"],
                conversation_id=self._debug_data["conversation_id"],
                user_query=self._debug_data["user_query"],
                retrieved_documents=self._debug_data["retrieved_documents"],
                formatted_context=self._debug_data["formatted_context"],
                prompt_template_used=self._debug_data["prompt_template_used"],
                llm_prompt_sent=self._debug_data["llm_prompt_sent"],
                retrieval_metadata=self._debug_data["retrieval_metadata"],
                db_doc_count=self._debug_data["db_doc_count"],
                analysis_doc_count=self._debug_data["analysis_doc_count"],
                retrieval_duration_ms=self._debug_data["retrieval_duration_ms"],
                llm_response_received=self._debug_data["llm_response_received"],
                fallback_llm_used=self._debug_data["fallback_llm_used"],
            )

            db.add(rag_debug_log)
            db.commit()
        except Exception as e:
            logger.error(
                "failed_to_log_rag_debug",
                error_type=type(e).__name__,
                error_message=str(e),
                request_id=self._debug_data.get("request_id"),
                exc_info=True,
            )
            db.rollback()
        finally:
            db.close()
