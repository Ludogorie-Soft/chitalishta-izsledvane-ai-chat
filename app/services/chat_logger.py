"""Service for logging chat requests and responses to database."""

import time
from datetime import datetime
from typing import Any, Dict, List, Optional

import structlog
from sqlalchemy.orm import Session

from app.db.models import ChatLog

logger = structlog.get_logger(__name__)


class ChatLogger:
    """Service for logging chat requests and responses."""

    def __init__(self, db: Session):
        """
        Initialize chat logger.

        Args:
            db: Database session
        """
        self.db = db
        self._llm_operations: List[Dict[str, Any]] = []
        self._start_time: Optional[float] = None
        self._sql_query: Optional[str] = None  # Store SQL query when captured from callbacks
        self._sql_query: Optional[str] = None  # Store SQL query when captured

    def set_sql_query(self, sql_query: str) -> None:
        """
        Set the SQL query that was executed.

        Args:
            sql_query: SQL query string
        """
        self._sql_query = sql_query

    def set_sql_query(self, sql_query: str) -> None:
        """
        Set the SQL query that was executed (captured from callbacks).

        Args:
            sql_query: SQL query string
        """
        self._sql_query = sql_query

    def start_request(
        self,
        request_id: str,
        conversation_id: str,
        user_message: str,
        hallucination_mode: str,
        output_format: Optional[str] = None,
        client_ip: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> None:
        """
        Start logging a chat request.

        Args:
            request_id: Unique request ID from middleware
            conversation_id: Conversation ID
            user_message: User's message/question
            hallucination_mode: Hallucination mode ('low', 'medium', 'high')
            output_format: Output format ('text', 'table', 'bullets', 'statistics')
            client_ip: Client IP address
            user_agent: User agent string
        """
        self._start_time = time.time()
        self._llm_operations = []
        self._sql_query = None  # Reset SQL query for new request
        self._request_id = request_id
        self._conversation_id = conversation_id
        self._user_message = user_message
        self._hallucination_mode = hallucination_mode
        self._output_format = output_format
        self._client_ip = client_ip
        self._user_agent = user_agent
        self._request_timestamp = datetime.now()

    def add_llm_operation(
        self,
        model: str,
        input_tokens: Optional[int] = None,
        output_tokens: Optional[int] = None,
        total_tokens: Optional[int] = None,
        latency_ms: Optional[float] = None,
    ) -> None:
        """
        Add an LLM operation to the log.

        Args:
            model: Model name used
            input_tokens: Input tokens used
            output_tokens: Output tokens used
            total_tokens: Total tokens used
            latency_ms: Latency in milliseconds
        """
        operation = {
            "model": model,
            "timestamp": datetime.now().isoformat(),
        }

        if input_tokens is not None:
            operation["input_tokens"] = input_tokens
        if output_tokens is not None:
            operation["output_tokens"] = output_tokens
        if total_tokens is not None:
            operation["total_tokens"] = total_tokens
        if latency_ms is not None:
            operation["latency_ms"] = round(latency_ms, 2)

        self._llm_operations.append(operation)

    def log_success(
        self,
        answer: str,
        intent: str,
        routing_confidence: float,
        sql_executed: bool,
        rag_executed: bool,
        sql_query: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        structured_output: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Log a successful chat response.

        Args:
            answer: Assistant's answer
            intent: Detected intent ('sql', 'rag', 'hybrid')
            routing_confidence: Confidence in intent classification (0.0-1.0)
            sql_executed: Whether SQL was executed
            rag_executed: Whether RAG was executed
            sql_query: SQL query if executed (will use self._sql_query if None)
            metadata: Additional metadata
            structured_output: Structured output if requested
        """
        # Use SQL query from callbacks if available, otherwise use provided one
        final_sql_query = self._sql_query or sql_query
        if self._start_time is None:
            logger.warning("log_success called without start_request")
            return

        response_time_ms = int((time.time() - self._start_time) * 1000)

        # Calculate total token usage from all LLM operations
        total_input_tokens = sum(
            op.get("input_tokens", 0) for op in self._llm_operations
        )
        total_output_tokens = sum(
            op.get("output_tokens", 0) for op in self._llm_operations
        )
        total_tokens = sum(op.get("total_tokens", 0) for op in self._llm_operations)

        # If total_tokens is 0 but we have input/output, calculate it
        if total_tokens == 0 and (total_input_tokens > 0 or total_output_tokens > 0):
            total_tokens = total_input_tokens + total_output_tokens

        chat_log = ChatLog(
            request_id=self._request_id,
            conversation_id=self._conversation_id,
            request_timestamp=self._request_timestamp,
            user_message=self._user_message,
            hallucination_mode=self._hallucination_mode,
            output_format=self._output_format,
            answer=answer,
            intent=intent,
            routing_confidence=float(routing_confidence),
            sql_executed=sql_executed,
            rag_executed=rag_executed,
            sql_query=final_sql_query,
            response_time_ms=response_time_ms,
            total_input_tokens=total_input_tokens if total_input_tokens > 0 else None,
            total_output_tokens=total_output_tokens if total_output_tokens > 0 else None,
            total_tokens=total_tokens if total_tokens > 0 else None,
            llm_operations=self._llm_operations if self._llm_operations else None,
            response_metadata=metadata,
            structured_output=structured_output,
            error_occurred=False,
            client_ip=self._client_ip,
            user_agent=self._user_agent,
            http_status_code=200,
        )

        try:
            self.db.add(chat_log)
            self.db.commit()
        except Exception as e:
            logger.error(
                "failed_to_log_chat",
                error_type=type(e).__name__,
                error_message=str(e),
                request_id=self._request_id,
                exc_info=True,
            )
            self.db.rollback()

    def log_error(
        self,
        error_type: str,
        error_message: str,
        http_status_code: int = 500,
        intent: Optional[str] = None,
        sql_executed: bool = False,
        rag_executed: bool = False,
    ) -> None:
        """
        Log a failed chat request.

        Args:
            error_type: Type of error (e.g., 'ValidationError', 'Exception')
            error_message: Error message
            http_status_code: HTTP status code (400, 500, etc.)
            intent: Detected intent if available
            sql_executed: Whether SQL was attempted
            rag_executed: Whether RAG was attempted
        """
        if self._start_time is None:
            logger.warning("log_error called without start_request")
            return

        response_time_ms = int((time.time() - self._start_time) * 1000)

        # Calculate total token usage even for errors (if LLM was called)
        total_input_tokens = sum(
            op.get("input_tokens", 0) for op in self._llm_operations
        )
        total_output_tokens = sum(
            op.get("output_tokens", 0) for op in self._llm_operations
        )
        total_tokens = sum(op.get("total_tokens", 0) for op in self._llm_operations)

        if total_tokens == 0 and (total_input_tokens > 0 or total_output_tokens > 0):
            total_tokens = total_input_tokens + total_output_tokens

        chat_log = ChatLog(
            request_id=self._request_id,
            conversation_id=self._conversation_id or "unknown",
            request_timestamp=self._request_timestamp,
            user_message=self._user_message,
            hallucination_mode=self._hallucination_mode,
            output_format=self._output_format,
            answer=None,
            intent=intent,
            routing_confidence=None,
            sql_executed=sql_executed,
            rag_executed=rag_executed,
            sql_query=None,
            response_time_ms=response_time_ms,
            total_input_tokens=total_input_tokens if total_input_tokens > 0 else None,
            total_output_tokens=total_output_tokens if total_output_tokens > 0 else None,
            total_tokens=total_tokens if total_tokens > 0 else None,
            llm_operations=self._llm_operations if self._llm_operations else None,
            response_metadata=None,
            structured_output=None,
            error_occurred=True,
            error_type=error_type,
            error_message=error_message,
            http_status_code=http_status_code,
            client_ip=self._client_ip,
            user_agent=self._user_agent,
        )

        try:
            self.db.add(chat_log)
            self.db.commit()
        except Exception as e:
            logger.error(
                "failed_to_log_chat_error",
                error_type=type(e).__name__,
                error_message=str(e),
                request_id=self._request_id,
                exc_info=True,
            )
            self.db.rollback()

