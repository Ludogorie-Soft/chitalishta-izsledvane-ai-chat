"""SQL agent using LangChain for querying the database."""

import logging
import re
from typing import Dict, List, Optional

from app.core.config import settings
from app.db.database import engine
from app.rag.llm_intent_classification import get_default_llm
from app.rag.hallucination_control import (
    HallucinationConfig,
    PromptEnhancer,
    get_default_hallucination_config,
)

logger = logging.getLogger(__name__)

try:
    # Try different import paths for create_sql_agent (varies by LangChain version)
    try:
        from langchain_community.agent_toolkits import create_sql_agent
    except ImportError:
        try:
            from langchain.agents import create_sql_agent
        except ImportError:
            from langchain_experimental.agents import create_sql_agent

    # SQLDatabaseToolkit and SQLDatabase are typically in langchain_community
    try:
        from langchain_community.agent_toolkits import SQLDatabaseToolkit
        from langchain_community.utilities import SQLDatabase
    except ImportError:
        from langchain.agents.agent_toolkits import SQLDatabaseToolkit
        from langchain.sql_database import SQLDatabase

    from langchain_core.language_models.chat_models import BaseChatModel
except ImportError as _e:  # pragma: no cover - guarded by tests
    create_sql_agent = None  # type: ignore[assignment]
    SQLDatabaseToolkit = None  # type: ignore[assignment]
    SQLDatabase = None  # type: ignore[assignment]
    BaseChatModel = object  # type: ignore[assignment]
    _LANGCHAIN_IMPORT_ERROR = _e
else:
    _LANGCHAIN_IMPORT_ERROR = None


class SQLValidator:
    """Validator for SQL queries to ensure safety and correctness."""

    # Dangerous SQL keywords that should be blocked
    DANGEROUS_KEYWORDS = [
        "DELETE",
        "DROP",
        "TRUNCATE",
        "ALTER",
        "CREATE",
        "INSERT",
        "UPDATE",
        "GRANT",
        "REVOKE",
        "EXEC",
        "EXECUTE",
    ]

    # Allowed SQL keywords for read-only operations
    ALLOWED_KEYWORDS = [
        "SELECT",
        "WITH",
        "FROM",
        "WHERE",
        "JOIN",
        "INNER",
        "LEFT",
        "RIGHT",
        "FULL",
        "OUTER",
        "ON",
        "GROUP",
        "BY",
        "HAVING",
        "ORDER",
        "LIMIT",
        "OFFSET",
        "UNION",
        "INTERSECT",
        "EXCEPT",
        "DISTINCT",
        "AS",
        "AND",
        "OR",
        "NOT",
        "IN",
        "LIKE",
        "IS",
        "NULL",
        "COUNT",
        "SUM",
        "AVG",
        "MIN",
        "MAX",
        "CASE",
        "WHEN",
        "THEN",
        "ELSE",
        "END",
    ]

    @classmethod
    def validate_sql(cls, sql: str) -> tuple[bool, Optional[str]]:
        """
        Validate SQL query for safety.

        Args:
            sql: SQL query string

        Returns:
            Tuple of (is_valid, error_message)
        """
        if not sql or not sql.strip():
            return False, "Empty SQL query"

        sql_upper = sql.upper().strip()

        # Check for dangerous keywords
        for keyword in cls.DANGEROUS_KEYWORDS:
            # Use word boundaries to avoid false positives
            pattern = r"\b" + re.escape(keyword) + r"\b"
            if re.search(pattern, sql_upper):
                return False, f"Dangerous SQL keyword detected: {keyword}. Only SELECT queries are allowed."

        # Ensure it starts with SELECT or WITH (for CTEs)
        if not (sql_upper.startswith("SELECT") or sql_upper.startswith("WITH")):
            return False, "Query must start with SELECT or WITH (for CTEs). Only read operations are allowed."

        # Check for semicolon injection attempts
        if ";" in sql and sql.count(";") > 1:
            return False, "Multiple semicolons detected. Possible SQL injection attempt."

        # Check for comment-based injection attempts
        if "--" in sql or "/*" in sql:
            # Allow comments in reasonable places, but be cautious
            if sql_upper.count("--") > 2 or sql_upper.count("/*") > 1:
                return False, "Excessive comments detected. Possible SQL injection attempt."

        return True, None

    @classmethod
    def sanitize_sql(cls, sql: str) -> str:
        """
        Sanitize SQL query by removing potentially dangerous patterns.

        Args:
            sql: SQL query string

        Returns:
            Sanitized SQL query
        """
        # Remove trailing semicolons (not needed for single queries)
        sql = sql.rstrip(";")

        # Remove excessive whitespace
        sql = re.sub(r"\s+", " ", sql)

        return sql.strip()


class SQLAuditLogger:
    """Logger for SQL query auditing."""

    @staticmethod
    def log_query(
        query: str,
        generated_sql: str,
        result: Optional[Dict] = None,
        error: Optional[str] = None,
    ):
        """
        Log SQL query execution for auditing.

        Args:
            query: Original user query
            generated_sql: Generated SQL query
            result: Query result (if successful)
            error: Error message (if failed)
        """
        log_data = {
            "type": "sql_query",
            "user_query": query,
            "generated_sql": generated_sql,
            "success": error is None,
        }

        if result:
            log_data["result_rows"] = result.get("row_count", 0)
            log_data["result_preview"] = result.get("preview", [])

        if error:
            log_data["error"] = error

        # Log as structured JSON for easy parsing
        logger.info("SQL_QUERY_AUDIT", extra=log_data)


class SQLAgentService:
    """
    SQL agent service using LangChain for generating and executing SQL queries.

    This service ensures read-only access and validates all SQL queries.
    """

    def __init__(
        self,
        llm: Optional[BaseChatModel] = None,
        database_url: Optional[str] = None,
        enable_audit_logging: bool = True,
        hallucination_config: Optional[HallucinationConfig] = None,
    ):
        """
        Initialize SQL agent service.

        Args:
            llm: Optional LLM instance. If None, creates one from settings.
            database_url: Optional database URL. If None, uses config default.
            enable_audit_logging: Whether to enable audit logging of SQL queries
            hallucination_config: Optional hallucination control configuration. If None, uses default (MEDIUM_TOLERANCE).
        """
        if _LANGCHAIN_IMPORT_ERROR is not None:
            raise ImportError(
                "LangChain SQL dependencies are required for SQLAgentService.\n"
                "Install them with:\n"
                "  poetry add langchain langchain-community langchain-openai"
            ) from _LANGCHAIN_IMPORT_ERROR

        self.hallucination_config = hallucination_config or get_default_hallucination_config()

        # Configure LLM with hallucination settings
        base_llm = llm or get_default_llm()
        self.llm = self.hallucination_config.get_llm_with_config(base_llm)
        self.database_url = database_url or settings.database_url
        self.enable_audit_logging = enable_audit_logging

        # Create SQLDatabase instance (read-only)
        self.db = SQLDatabase(
            engine=engine,
            # Include only the tables we want to expose
            include_tables=["chitalishte", "information_card"],
            # Sample rows for schema understanding (limit to avoid large samples)
            sample_rows_in_table_info=3,
        )

        # Create SQL toolkit
        self.toolkit = SQLDatabaseToolkit(db=self.db, llm=self.llm)

        # Create SQL agent with Bulgarian prompt
        self.agent = self._create_sql_agent()

        # Initialize validator and logger
        self.validator = SQLValidator()
        self.audit_logger = SQLAuditLogger() if enable_audit_logging else None

    def _create_sql_agent(self):
        """Create SQL agent with Bulgarian language support."""
        # Create agent with custom prompt for Bulgarian
        # Note: create_sql_agent API may vary by LangChain version
        # Using the standard parameters that work across versions
        agent = create_sql_agent(
            llm=self.llm,
            toolkit=self.toolkit,
            verbose=True,  # Enable verbose logging for debugging
            agent_type="openai-tools",  # Use OpenAI tools format
        )

        return agent

    def _get_bulgarian_system_message(self) -> str:
        """Get Bulgarian system message for SQL agent with hallucination control."""
        base_message = (
            "Ти си SQL агент за база данни за читалища в България.\n"
            "Твоята задача е да генерираш SQL заявки на базата на потребителските въпроси.\n"
            "\n"
            "ВАЖНИ ПРАВИЛА:\n"
            "1. Генерирай САМО SELECT заявки. Никога не използвай DELETE, UPDATE, INSERT, DROP или други модифициращи команди.\n"
            "2. Използвай таблиците 'chitalishte' и 'information_card'.\n"
            "3. За агрегации използвай COUNT, SUM, AVG, MIN, MAX.\n"
            "4. За JOIN операции използвай правилните ключове:\n"
            "   - chitalishte.id = information_card.chitalishte_id\n"
            "5. Бъди точен с имената на колоните.\n"
            "6. Ако потребителят пита за статистика, използвай GROUP BY.\n"
            "7. Връщай резултатите на български език, когато е възможно.\n"
        )

        # Enhance with hallucination control instructions
        return PromptEnhancer.enhance_sql_prompt(base_message, self.hallucination_config)

    def _validate_and_sanitize_sql(self, sql: str) -> tuple[str, Optional[str]]:
        """
        Validate and sanitize SQL query.

        Args:
            sql: SQL query string

        Returns:
            Tuple of (sanitized_sql, error_message)
        """
        # Validate
        is_valid, error = self.validator.validate_sql(sql)
        if not is_valid:
            return sql, error

        # Sanitize
        sanitized = self.validator.sanitize_sql(sql)

        return sanitized, None

    def query(self, question: str) -> Dict[str, any]:
        """
        Execute SQL query based on user question.

        Args:
            question: User question in Bulgarian

        Returns:
            Dictionary with answer, SQL query, and metadata
        """
        try:
            # Invoke the agent
            result = self.agent.invoke({"input": question})

            # Extract SQL query from agent execution
            # The agent returns a dict with 'output' and potentially intermediate steps
            answer = result.get("output", str(result))

            # Try to extract SQL from intermediate steps if available
            generated_sql = None
            if "intermediate_steps" in result:
                for step in result["intermediate_steps"]:
                    if isinstance(step, tuple) and len(step) >= 2:
                        action = step[0]
                        if hasattr(action, "tool_input") and "query" in str(action.tool_input):
                            # Extract SQL from tool input
                            tool_input = action.tool_input
                            if isinstance(tool_input, dict) and "query" in tool_input:
                                generated_sql = tool_input["query"]
                            elif isinstance(tool_input, str):
                                # Try to extract SQL from string
                                sql_match = re.search(r"SELECT.*?(?:;|$)", tool_input, re.IGNORECASE | re.DOTALL)
                                if sql_match:
                                    generated_sql = sql_match.group(0)

            # If we couldn't extract SQL from steps, try to find it in the output
            if not generated_sql:
                sql_match = re.search(r"SELECT.*?(?:;|$)", answer, re.IGNORECASE | re.DOTALL)
                if sql_match:
                    generated_sql = sql_match.group(0)

            # Validate SQL if we found it
            if generated_sql:
                sanitized_sql, error = self._validate_and_sanitize_sql(generated_sql)
                if error:
                    logger.warning(f"SQL validation failed: {error}")
                    # Still return the answer, but log the warning
                generated_sql = sanitized_sql

            # Audit log
            if self.audit_logger:
                self.audit_logger.log_query(
                    query=question,
                    generated_sql=generated_sql or "N/A",
                    result={"answer": answer},
                )

            return {
                "answer": answer,
                "sql_query": generated_sql,
                "question": question,
                "success": True,
            }

        except Exception as e:
            error_msg = str(e)

            # Audit log error
            if self.audit_logger:
                self.audit_logger.log_query(
                    query=question,
                    generated_sql="N/A",
                    error=error_msg,
                )

            logger.error(f"SQL agent error: {error_msg}", exc_info=True)

            return {
                "answer": f"Грешка при изпълнение на заявката: {error_msg}",
                "sql_query": None,
                "question": question,
                "success": False,
                "error": error_msg,
            }

    def execute_sql(self, sql: str) -> Dict[str, any]:
        """
        Execute a SQL query directly (with validation).

        This method allows direct SQL execution but still validates the query.

        Args:
            sql: SQL query string

        Returns:
            Dictionary with results and metadata
        """
        # Validate and sanitize
        sanitized_sql, error = self._validate_and_sanitize_sql(sql)
        if error:
            return {
                "success": False,
                "error": error,
                "sql_query": sql,
                "results": None,
            }

        try:
            # Execute query
            result = self.db.run(sanitized_sql)

            # Parse result
            # The result is typically a string representation of rows
            rows = []
            if result:
                # Try to parse the result (format depends on SQLDatabase implementation)
                # For now, just return the raw result
                rows = [result] if isinstance(result, str) else result

            # Audit log
            if self.audit_logger:
                self.audit_logger.log_query(
                    query="Direct SQL execution",
                    generated_sql=sanitized_sql,
                    result={"row_count": len(rows) if isinstance(rows, list) else 1},
                )

            return {
                "success": True,
                "sql_query": sanitized_sql,
                "results": rows,
                "row_count": len(rows) if isinstance(rows, list) else 1,
            }

        except Exception as e:
            error_msg = str(e)

            # Audit log error
            if self.audit_logger:
                self.audit_logger.log_query(
                    query="Direct SQL execution",
                    generated_sql=sanitized_sql,
                    error=error_msg,
                )

            logger.error(f"SQL execution error: {error_msg}", exc_info=True)

            return {
                "success": False,
                "error": error_msg,
                "sql_query": sanitized_sql,
                "results": None,
            }


def get_sql_agent_service(
    llm: Optional[BaseChatModel] = None,
    enable_audit_logging: bool = True,
    hallucination_config: Optional[HallucinationConfig] = None,
) -> SQLAgentService:
    """
    Factory function to get a default SQLAgentService.

    Args:
        llm: Optional LLM instance. If None, creates one from settings.
        enable_audit_logging: Whether to enable audit logging

    Returns:
        SQLAgentService instance
    """
    return SQLAgentService(
        llm=llm,
        enable_audit_logging=enable_audit_logging,
        hallucination_config=hallucination_config,
    )

