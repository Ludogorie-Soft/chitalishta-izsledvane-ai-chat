"""LangChain callback handler for structured logging and observability."""

import time
from typing import Any, Dict, List, Optional

import structlog
from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.outputs import LLMResult
from langchain_core.tracers.schemas import Run

logger = structlog.get_logger(__name__)


class StructuredLoggingCallbackHandler(BaseCallbackHandler):
    """
    Custom LangChain callback handler that logs all operations to structured logs.

    This handler captures:
    - LLM calls (start, end, token usage, latency)
    - Retrieval operations (queries, results, document sources)
    - Chain execution (inputs, outputs, intermediate steps)
    - Errors with full context

    All logs include request ID from context for correlation.
    """

    def __init__(self):
        """Initialize the callback handler."""
        super().__init__()
        self._run_times: Dict[str, float] = {}  # Track start times for runs

    def _get_request_id(self) -> Optional[str]:
        """Get request ID from structlog context variables."""
        context = structlog.contextvars.get_contextvars()
        return context.get("request_id")

    def _log_with_context(self, event: str, **kwargs):
        """
        Log event with request ID context.

        Args:
            event: Event name/type
            **kwargs: Additional log fields
        """
        request_id = self._get_request_id()
        logger.info(
            event,
            request_id=request_id,
            **kwargs,
        )

    def on_llm_start(
        self,
        serialized: Dict[str, Any],
        prompts: List[str],
        *,
        run_id: str,
        parent_run_id: Optional[str] = None,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> None:
        """
        Log when an LLM starts running.

        Args:
            serialized: Serialized LLM configuration
            prompts: List of prompts being sent to LLM
            run_id: Unique identifier for this run
            parent_run_id: ID of parent run (if part of a chain)
            tags: Optional tags for this run
            metadata: Optional metadata
            **kwargs: Additional arguments
        """
        # Record start time
        self._run_times[run_id] = time.time()

        # Extract model information
        model_name = serialized.get("id", [None])[-1] if isinstance(serialized.get("id"), list) else serialized.get("name", "unknown")

        # Get prompt preview (first 200 chars)
        prompt_preview = prompts[0][:200] if prompts else ""

        self._log_with_context(
            "llm_start",
            run_id=run_id,
            parent_run_id=parent_run_id,
            model=model_name,
            prompt_count=len(prompts),
            prompt_preview=prompt_preview,
            tags=tags,
            metadata=metadata,
        )

    def on_llm_end(
        self,
        response: LLMResult,
        *,
        run_id: str,
        parent_run_id: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        """
        Log when an LLM finishes running.

        Args:
            response: LLM response with generations and token usage
            run_id: Unique identifier for this run
            parent_run_id: ID of parent run (if part of a chain)
            **kwargs: Additional arguments
        """
        # Calculate duration
        start_time = self._run_times.pop(run_id, None)
        duration_ms = None
        if start_time:
            duration_ms = round((time.time() - start_time) * 1000, 2)

        # Extract token usage
        token_usage = {}
        if response.llm_output:
            token_usage = response.llm_output.get("token_usage", {})

        # Get generation preview (first 200 chars)
        generation_preview = ""
        if response.generations and response.generations[0]:
            first_gen = response.generations[0][0]
            if hasattr(first_gen, "text"):
                generation_preview = first_gen.text[:200]

        self._log_with_context(
            "llm_end",
            run_id=run_id,
            parent_run_id=parent_run_id,
            duration_ms=duration_ms,
            generation_count=len(response.generations) if response.generations else 0,
            generation_preview=generation_preview,
            token_usage=token_usage,
        )

    def on_llm_error(
        self,
        error: Exception,
        *,
        run_id: str,
        parent_run_id: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        """
        Log when an LLM encounters an error.

        Args:
            error: The error that occurred
            run_id: Unique identifier for this run
            parent_run_id: ID of parent run (if part of a chain)
            **kwargs: Additional arguments
        """
        # Calculate duration if we have start time
        start_time = self._run_times.pop(run_id, None)
        duration_ms = None
        if start_time:
            duration_ms = round((time.time() - start_time) * 1000, 2)

        logger.error(
            "llm_error",
            request_id=self._get_request_id(),
            run_id=run_id,
            parent_run_id=parent_run_id,
            error_type=type(error).__name__,
            error_message=str(error),
            duration_ms=duration_ms,
            exc_info=True,
        )

    def on_retriever_start(
        self,
        serialized: Dict[str, Any],
        query: str,
        *,
        run_id: str,
        parent_run_id: Optional[str] = None,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> None:
        """
        Log when a retriever starts running.

        Args:
            serialized: Serialized retriever configuration
            query: Query string used for retrieval
            run_id: Unique identifier for this run
            parent_run_id: ID of parent run (if part of a chain)
            tags: Optional tags for this run
            metadata: Optional metadata
            **kwargs: Additional arguments
        """
        # Record start time
        self._run_times[run_id] = time.time()

        self._log_with_context(
            "retriever_start",
            run_id=run_id,
            parent_run_id=parent_run_id,
            query=query,
            retriever_type=serialized.get("name", "unknown"),
            tags=tags,
            metadata=metadata,
        )

    def on_retriever_end(
        self,
        documents: List[Any],
        *,
        run_id: str,
        parent_run_id: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        """
        Log when a retriever finishes running.

        Args:
            documents: Retrieved documents
            run_id: Unique identifier for this run
            parent_run_id: ID of parent run (if part of a chain)
            **kwargs: Additional arguments
        """
        # Calculate duration
        start_time = self._run_times.pop(run_id, None)
        duration_ms = None
        if start_time:
            duration_ms = round((time.time() - start_time) * 1000, 2)

        # Extract document metadata
        document_count = len(documents)
        sources = []
        doc_previews = []

        for doc in documents[:5]:  # Limit to first 5 for logging
            if hasattr(doc, "metadata"):
                source = doc.metadata.get("source", "unknown")
                sources.append(source)
            if hasattr(doc, "page_content"):
                preview = doc.page_content[:100] if doc.page_content else ""
                doc_previews.append(preview)

        self._log_with_context(
            "retriever_end",
            run_id=run_id,
            parent_run_id=parent_run_id,
            duration_ms=duration_ms,
            document_count=document_count,
            sources=sources[:10],  # Limit sources list
            document_previews=doc_previews,
        )

    def on_retriever_error(
        self,
        error: Exception,
        *,
        run_id: str,
        parent_run_id: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        """
        Log when a retriever encounters an error.

        Args:
            error: The error that occurred
            run_id: Unique identifier for this run
            parent_run_id: ID of parent run (if part of a chain)
            **kwargs: Additional arguments
        """
        # Calculate duration if we have start time
        start_time = self._run_times.pop(run_id, None)
        duration_ms = None
        if start_time:
            duration_ms = round((time.time() - start_time) * 1000, 2)

        logger.error(
            "retriever_error",
            request_id=self._get_request_id(),
            run_id=run_id,
            parent_run_id=parent_run_id,
            error_type=type(error).__name__,
            error_message=str(error),
            duration_ms=duration_ms,
            exc_info=True,
        )

    def on_chain_start(
        self,
        serialized: Dict[str, Any],
        inputs: Dict[str, Any],
        *,
        run_id: str,
        parent_run_id: Optional[str] = None,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> None:
        """
        Log when a chain starts running.

        Args:
            serialized: Serialized chain configuration
            inputs: Inputs to the chain
            run_id: Unique identifier for this run
            parent_run_id: ID of parent run (if part of a chain)
            tags: Optional tags for this run
            metadata: Optional metadata
            **kwargs: Additional arguments
        """
        # Record start time
        self._run_times[run_id] = time.time()

        # Extract chain name
        chain_name = serialized.get("name", "unknown")
        if isinstance(chain_name, list):
            chain_name = chain_name[-1] if chain_name else "unknown"

        # Get input preview (limit size) - handle None or non-dict inputs
        input_preview = {}
        input_keys = []
        if inputs is not None and isinstance(inputs, dict):
            try:
                input_keys = list(inputs.keys())
                for key, value in list(inputs.items())[:3]:  # Limit to first 3 inputs
                    if isinstance(value, str):
                        input_preview[key] = value[:200]
                    else:
                        input_preview[key] = str(value)[:200]
            except Exception:
                input_preview = {"raw": str(inputs)[:200]}
        elif inputs is not None:
            input_preview = {"raw": str(inputs)[:200]}

        self._log_with_context(
            "chain_start",
            run_id=run_id,
            parent_run_id=parent_run_id,
            chain_name=chain_name,
            input_keys=input_keys,
            input_preview=input_preview,
            tags=tags,
            metadata=metadata,
        )

    def on_chain_end(
        self,
        outputs: Dict[str, Any],
        *,
        run_id: str,
        parent_run_id: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        """
        Log when a chain finishes running.

        Args:
            outputs: Outputs from the chain
            run_id: Unique identifier for this run
            parent_run_id: ID of parent run (if part of a chain)
            **kwargs: Additional arguments
        """
        # Calculate duration
        start_time = self._run_times.pop(run_id, None)
        duration_ms = None
        if start_time:
            duration_ms = round((time.time() - start_time) * 1000, 2)

        # Get output preview (limit size) - handle None, list, or non-dict outputs
        output_preview = {}
        output_keys = []
        if outputs is not None:
            if isinstance(outputs, dict):
                try:
                    output_keys = list(outputs.keys())
                    for key, value in list(outputs.items())[:3]:  # Limit to first 3 outputs
                        if isinstance(value, str):
                            output_preview[key] = value[:200]
                        else:
                            output_preview[key] = str(value)[:200]
                except Exception:
                    output_preview = {"raw": str(outputs)[:200]}
            elif isinstance(outputs, list):
                output_keys = [f"item_{i}" for i in range(len(outputs))]
                output_preview = {"list_length": len(outputs), "preview": str(outputs[:3])[:200]}
            else:
                output_preview = {"raw": str(outputs)[:200]}

        self._log_with_context(
            "chain_end",
            run_id=run_id,
            parent_run_id=parent_run_id,
            duration_ms=duration_ms,
            output_keys=output_keys,
            output_preview=output_preview,
        )

    def on_chain_error(
        self,
        error: Exception,
        *,
        run_id: str,
        parent_run_id: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        """
        Log when a chain encounters an error.

        Args:
            error: The error that occurred
            run_id: Unique identifier for this run
            parent_run_id: ID of parent run (if part of a chain)
            **kwargs: Additional arguments
        """
        # Calculate duration if we have start time
        start_time = self._run_times.pop(run_id, None)
        duration_ms = None
        if start_time:
            duration_ms = round((time.time() - start_time) * 1000, 2)

        logger.error(
            "chain_error",
            request_id=self._get_request_id(),
            run_id=run_id,
            parent_run_id=parent_run_id,
            error_type=type(error).__name__,
            error_message=str(error),
            duration_ms=duration_ms,
            exc_info=True,
        )


def get_langchain_callback_handler() -> StructuredLoggingCallbackHandler:
    """
    Factory function to get a LangChain callback handler instance.

    Returns:
        Configured StructuredLoggingCallbackHandler
    """
    return StructuredLoggingCallbackHandler()

