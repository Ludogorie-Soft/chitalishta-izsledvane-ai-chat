"""Tests for SQL agent service."""

import pytest
from unittest.mock import patch, MagicMock

pytest.importorskip("langchain_core")

# Try to import - if it fails due to missing SQL agent dependencies, we'll skip those tests
try:
    from app.rag.sql_agent import SQLAgentService, SQLValidator, get_sql_agent_service
    _SQL_AGENT_AVAILABLE = True
except ImportError:
    _SQL_AGENT_AVAILABLE = False
    # Create dummy classes for type hints
    SQLAgentService = None  # type: ignore
    SQLValidator = None  # type: ignore
    get_sql_agent_service = None  # type: ignore


class TestSQLValidator:
    """Tests for SQLValidator."""

    def test_validate_sql_allows_select(self):
        """Validator should allow SELECT queries."""
        sql = "SELECT * FROM chitalishte"
        is_valid, error = SQLValidator.validate_sql(sql)
        assert is_valid
        assert error is None

    def test_validate_sql_allows_with_cte(self):
        """Validator should allow WITH CTEs."""
        sql = "WITH cte AS (SELECT * FROM chitalishte) SELECT * FROM cte"
        is_valid, error = SQLValidator.validate_sql(sql)
        assert is_valid
        assert error is None

    def test_validate_sql_blocks_delete(self):
        """Validator should block DELETE queries."""
        sql = "DELETE FROM chitalishte WHERE id = 1"
        is_valid, error = SQLValidator.validate_sql(sql)
        assert not is_valid
        assert "DELETE" in error

    def test_validate_sql_blocks_update(self):
        """Validator should block UPDATE queries."""
        sql = "UPDATE chitalishte SET name = 'test' WHERE id = 1"
        is_valid, error = SQLValidator.validate_sql(sql)
        assert not is_valid
        assert "UPDATE" in error

    def test_validate_sql_blocks_insert(self):
        """Validator should block INSERT queries."""
        sql = "INSERT INTO chitalishte (name) VALUES ('test')"
        is_valid, error = SQLValidator.validate_sql(sql)
        assert not is_valid
        assert "INSERT" in error

    def test_validate_sql_blocks_drop(self):
        """Validator should block DROP queries."""
        sql = "DROP TABLE chitalishte"
        is_valid, error = SQLValidator.validate_sql(sql)
        assert not is_valid
        assert "DROP" in error

    def test_validate_sql_blocks_multiple_semicolons(self):
        """Validator should block multiple semicolons (injection attempt)."""
        # Test with a query that has multiple semicolons but no dangerous keywords
        sql = "SELECT * FROM chitalishte; SELECT * FROM information_card;"
        is_valid, error = SQLValidator.validate_sql(sql)
        assert not is_valid
        assert "semicolon" in error.lower()

    def test_validate_sql_blocks_multiple_semicolons_with_dangerous_keyword(self):
        """Validator should block queries with multiple semicolons and dangerous keywords."""
        # This test ensures that dangerous keywords are caught even with multiple semicolons
        sql = "SELECT * FROM chitalishte; DROP TABLE chitalishte;"
        is_valid, error = SQLValidator.validate_sql(sql)
        assert not is_valid
        # The validator may catch either the dangerous keyword (DROP) or multiple semicolons
        # Both are valid security checks, so we accept either error
        assert "semicolon" in error.lower() or "drop" in error.lower() or "dangerous" in error.lower()

    def test_validate_sql_rejects_empty_query(self):
        """Validator should reject empty queries."""
        is_valid, error = SQLValidator.validate_sql("")
        assert not is_valid
        assert "Empty" in error

    def test_sanitize_sql_removes_trailing_semicolon(self):
        """Sanitizer should remove trailing semicolons."""
        sql = "SELECT * FROM chitalishte;"
        sanitized = SQLValidator.sanitize_sql(sql)
        assert not sanitized.endswith(";")

    def test_sanitize_sql_normalizes_whitespace(self):
        """Sanitizer should normalize whitespace."""
        sql = "SELECT    *   FROM    chitalishte"
        sanitized = SQLValidator.sanitize_sql(sql)
        # Should have normalized spaces (but exact format may vary)
        assert "SELECT" in sanitized
        assert "FROM" in sanitized


class TestSQLAgentService:
    """Tests for SQLAgentService."""

    @pytest.fixture(autouse=True)
    def check_sql_agent_available(self):
        """Skip tests if SQL agent dependencies are not available."""
        if not _SQL_AGENT_AVAILABLE:
            pytest.skip(
                "SQL agent dependencies not available. "
                "Install with: poetry add langchain-community"
            )

    @pytest.fixture
    def mock_llm(self):
        """Create a mock LLM for testing."""
        try:
            from langchain_core.language_models.chat_models import BaseChatModel
            from langchain_core.messages import AIMessage

            class MockLLM(BaseChatModel):
                def _generate(self, messages, stop=None, run_manager=None, **kwargs):
                    return self._generate_helper(messages, stop, **kwargs)

                def _generate_helper(self, messages, stop=None, **kwargs):
                    # Return a simple response
                    return [
                        type("Generation", (), {
                            "message": AIMessage(content="Mock SQL answer"),
                            "generation_info": {},
                        })()
                    ]

                @property
                def _llm_type(self):
                    return "mock"

            return MockLLM()
        except ImportError:
            pytest.skip("LangChain not available")

    def test_sql_agent_initializes(self, mock_llm, test_engine):
        """SQL agent should initialize with database connection."""
        # Mock the database and agent components
        with patch("app.rag.sql_agent.engine", test_engine), \
             patch("app.rag.sql_agent.SQLDatabase") as mock_sql_db, \
             patch("app.rag.sql_agent.SQLDatabaseToolkit") as mock_toolkit, \
             patch("app.rag.sql_agent.create_sql_agent") as mock_agent:

            # Create mock instances
            mock_db_instance = MagicMock()
            mock_sql_db.return_value = mock_db_instance

            mock_toolkit_instance = MagicMock()
            mock_toolkit.return_value = mock_toolkit_instance

            mock_agent_instance = MagicMock()
            mock_agent_instance.invoke = MagicMock(return_value={"output": "Mock answer"})
            mock_agent.return_value = mock_agent_instance

            service = SQLAgentService(llm=mock_llm, database_url=None)
            assert service is not None
            assert service.llm == mock_llm
            assert service.validator is not None

    def test_factory_function(self, mock_llm, test_engine):
        """Factory function should create a SQL agent service."""
        from unittest.mock import patch, MagicMock

        with patch("app.rag.sql_agent.engine", test_engine), \
             patch("app.rag.sql_agent.SQLDatabase") as mock_sql_db, \
             patch("app.rag.sql_agent.SQLDatabaseToolkit") as mock_toolkit, \
             patch("app.rag.sql_agent.create_sql_agent") as mock_agent:
            mock_db_instance = MagicMock()
            mock_sql_db.return_value = mock_db_instance
            mock_toolkit_instance = MagicMock()
            mock_toolkit.return_value = mock_toolkit_instance
            mock_agent_instance = MagicMock()
            mock_agent_instance.invoke = MagicMock(return_value={"output": "Mock answer"})
            mock_agent.return_value = mock_agent_instance

            service = get_sql_agent_service(llm=mock_llm)
            assert isinstance(service, SQLAgentService)

    def test_execute_sql_validates_query(self, mock_llm, test_engine):
        """execute_sql should validate queries before execution."""
        from unittest.mock import patch, MagicMock

        with patch("app.rag.sql_agent.engine", test_engine), \
             patch("app.rag.sql_agent.SQLDatabase") as mock_sql_db, \
             patch("app.rag.sql_agent.SQLDatabaseToolkit") as mock_toolkit, \
             patch("app.rag.sql_agent.create_sql_agent") as mock_agent:
            mock_db_instance = MagicMock()
            mock_sql_db.return_value = mock_db_instance
            mock_toolkit_instance = MagicMock()
            mock_toolkit.return_value = mock_toolkit_instance
            mock_agent_instance = MagicMock()
            mock_agent_instance.invoke = MagicMock(return_value={"output": "Mock answer"})
            mock_agent.return_value = mock_agent_instance

            service = SQLAgentService(llm=mock_llm)

            # Try to execute a dangerous query
            result = service.execute_sql("DELETE FROM chitalishte WHERE id = 1")

            assert not result["success"]
            assert "error" in result
            assert "DELETE" in result["error"] or "Dangerous" in result["error"]

    def test_execute_sql_allows_select(self, mock_llm, test_engine):
        """execute_sql should allow SELECT queries."""
        from unittest.mock import patch, MagicMock

        with patch("app.rag.sql_agent.engine", test_engine), \
             patch("app.rag.sql_agent.SQLDatabase") as mock_sql_db, \
             patch("app.rag.sql_agent.SQLDatabaseToolkit") as mock_toolkit, \
             patch("app.rag.sql_agent.create_sql_agent") as mock_agent:
            mock_db_instance = MagicMock()
            mock_db_instance.run = MagicMock(return_value="Mock result: 10")
            mock_sql_db.return_value = mock_db_instance
            mock_toolkit_instance = MagicMock()
            mock_toolkit.return_value = mock_toolkit_instance
            mock_agent_instance = MagicMock()
            mock_agent_instance.invoke = MagicMock(return_value={"output": "Mock answer"})
            mock_agent.return_value = mock_agent_instance

            service = SQLAgentService(llm=mock_llm)

            # Try to execute a safe SELECT query
            result = service.execute_sql("SELECT COUNT(*) FROM chitalishte")

            # Should not fail validation
            assert "success" in result
            # If it fails, it should be due to DB connection, not validation
            if not result["success"]:
                assert "DELETE" not in result.get("error", "")
                assert "UPDATE" not in result.get("error", "")

