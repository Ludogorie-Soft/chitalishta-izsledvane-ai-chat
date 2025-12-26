"""LangChain callback handler for capturing LLM operations for chat logging."""

from typing import Any, Dict, List, Optional

from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.outputs import LLMResult

from app.services.chat_logger import ChatLogger


class ChatLoggerCallbackHandler(BaseCallbackHandler):
    """
    LangChain callback handler that captures LLM operations for chat logging.

    This handler works alongside StructuredLoggingCallbackHandler to capture
    LLM operation details (model, tokens, latency) for database storage.
    """

    def __init__(self, chat_logger: ChatLogger):
        """
        Initialize the callback handler.

        Args:
            chat_logger: ChatLogger instance to record LLM operations
        """
        super().__init__()
        self.chat_logger = chat_logger
        self._llm_start_times: Dict[str, float] = {}

    def on_tool_start(
        self,
        serialized: Dict[str, Any],
        input_str: Any,  # Can be str, dict, or other types
        *,
        run_id: str,
        **kwargs: Any,
    ) -> None:
        """
        Capture tool calls, specifically SQL tool calls.

        Args:
            serialized: Serialized tool configuration
            input_str: Tool input (can be string or dict)
            run_id: Unique identifier for this run
            **kwargs: Additional arguments
        """
        import structlog
        logger = structlog.get_logger(__name__)

        # Check if this is a SQL tool
        tool_name = serialized.get("name", "")
        if "sql" in tool_name.lower() or "query" in tool_name.lower() or tool_name == "sql_db_query":
            import re
            import json

            # Method 1: Try to parse as JSON first (most reliable)
            if isinstance(input_str, str) and input_str.strip().startswith("{"):
                try:
                    parsed = json.loads(input_str)
                    if isinstance(parsed, dict) and "query" in parsed:
                        sql_query = parsed["query"]
                        if isinstance(sql_query, str) and "SELECT" in sql_query.upper():
                            self.chat_logger.set_sql_query(sql_query)
                            return
                except (json.JSONDecodeError, Exception):
                    pass

            # Method 2: If input_str is already a dict (some LangChain versions)
            if isinstance(input_str, dict):
                if "query" in input_str:
                    sql_query = input_str["query"]
                    if isinstance(sql_query, str) and "SELECT" in sql_query.upper():
                        self.chat_logger.set_sql_query(sql_query)
                        logger.debug("sql_captured_from_tool_dict", tool=tool_name)
                        return
                # Check all values in dict for SQL
                for key, value in input_str.items():
                    if isinstance(value, str) and "SELECT" in value.upper():
                        sql_match = re.search(r"SELECT.*?(?:;|$)", value, re.IGNORECASE | re.DOTALL)
                        if sql_match:
                            self.chat_logger.set_sql_query(sql_match.group(0))
                            logger.debug("sql_captured_from_tool_dict_value", tool=tool_name, key=key)
                            return

            # Method 3: Extract SQL directly from string using regex
            if isinstance(input_str, str):
                # Try to find SELECT statement
                sql_match = re.search(r"SELECT.*?(?:;|$)", input_str, re.IGNORECASE | re.DOTALL)
                if sql_match:
                    self.chat_logger.set_sql_query(sql_match.group(0))
                    return

                # Method 4: Extract from dict-like string with query key
                # Pattern: {'query': 'SELECT...'} or {"query": "SELECT..."}
                # Handle both single and double quotes, and multi-line SQL
                query_match = re.search(
                    r"['\"]query['\"]\s*:\s*['\"](SELECT.*?)['\"]",
                    input_str,
                    re.IGNORECASE | re.DOTALL
                )
                if not query_match:
                    # Try without quotes around SELECT (for multi-line SQL)
                    query_match = re.search(
                        r"['\"]query['\"]\s*:\s*(SELECT.*?)(?:\s*[,\"'}])",
                        input_str,
                        re.IGNORECASE | re.DOTALL
                    )
                if not query_match:
                    # Try with Python dict format: 'query': 'SELECT...'
                    query_match = re.search(
                        r"['\"]query['\"]\s*:\s*['\"]([^'\"]*SELECT[^'\"]*?)['\"]",
                        input_str,
                        re.IGNORECASE | re.DOTALL
                    )
                if query_match:
                    sql_query = query_match.group(1)
                    # Clean up escaped newlines if any
                    sql_query = sql_query.replace("\\n", "\n").replace("\\t", "\t")
                    self.chat_logger.set_sql_query(sql_query)
                    logger.debug("sql_captured_from_tool_string", tool=tool_name)
                    return

            # Method 5: Check kwargs for input (some LangChain versions)
            if kwargs:
                for key, value in kwargs.items():
                    if isinstance(value, dict) and "query" in value:
                        sql_query = value["query"]
                        if isinstance(sql_query, str) and "SELECT" in sql_query.upper():
                            self.chat_logger.set_sql_query(sql_query)
                            logger.debug("sql_captured_from_kwargs", tool=tool_name, kwarg_key=key)
                            return
                    elif isinstance(value, str) and "SELECT" in value.upper():
                        sql_match = re.search(r"SELECT.*?(?:;|$)", value, re.IGNORECASE | re.DOTALL)
                        if sql_match:
                            self.chat_logger.set_sql_query(sql_match.group(0))
                            logger.debug("sql_captured_from_kwargs_string", tool=tool_name, kwarg_key=key)
                            return

            # Method 6: Log what we received for debugging
            logger.debug(
                "sql_tool_called_but_not_extracted",
                tool_name=tool_name,
                input_type=type(input_str).__name__,
                input_preview=str(input_str)[:200] if input_str else None,
                kwargs_keys=list(kwargs.keys()) if kwargs else [],
            )

    def on_tool_end(
        self,
        output: str,
        *,
        run_id: str,
        **kwargs: Any,
    ) -> None:
        """
        Called when a tool finishes executing.

        Args:
            output: Tool output
            run_id: Unique identifier for this run
            **kwargs: Additional arguments
        """
        # Tool execution completed - SQL query should already be captured in on_tool_start
        pass

    def on_llm_start(
        self,
        serialized: Dict[str, Any],
        prompts: List[str],
        *,
        run_id: str,
        **kwargs: Any,
    ) -> None:
        """Record LLM start time."""
        import time

        self._llm_start_times[run_id] = time.time()

    def on_llm_end(
        self,
        response: LLMResult,
        *,
        run_id: str,
        **kwargs: Any,
    ) -> None:
        """
        Capture LLM operation details and add to chat logger.

        Args:
            response: LLM response with token usage
            run_id: Unique identifier for this run
            **kwargs: Additional arguments
        """
        import time

        # Calculate latency
        start_time = self._llm_start_times.pop(run_id, None)
        latency_ms = None
        if start_time:
            latency_ms = (time.time() - start_time) * 1000

        # Extract model information
        model_name = "unknown"
        if response.llm_output:
            # Try to get model from llm_output
            model_name = response.llm_output.get("model_name", "unknown")
            if model_name == "unknown":
                # Try alternative keys
                model_name = (
                    response.llm_output.get("model", "unknown")
                    or response.llm_output.get("_model", "unknown")
                    or "unknown"
                )

        # Extract token usage
        token_usage = response.llm_output.get("token_usage", {}) if response.llm_output else {}
        input_tokens = token_usage.get("prompt_tokens") or token_usage.get("input_tokens")
        output_tokens = token_usage.get("completion_tokens") or token_usage.get("output_tokens")
        total_tokens = token_usage.get("total_tokens")

        # Add to chat logger
        self.chat_logger.add_llm_operation(
            model=model_name,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=total_tokens,
            latency_ms=latency_ms,
        )

