"""Tests for hybrid pipeline service."""

import pytest
from unittest.mock import MagicMock, patch

pytest.importorskip("langchain_core")

from app.rag.hybrid_pipeline import (
    HybridPipelineService,
    SQLResultFormatter,
    get_hybrid_pipeline_service,
)
from app.rag.intent_classification import QueryIntent


class TestSQLResultFormatter:
    """Tests for SQLResultFormatter."""

    def test_format_sql_result_success(self):
        """Formatter should format successful SQL result."""
        sql_result = {
            "success": True,
            "answer": "Има 10 читалища в Пловдив.",
            "sql_query": "SELECT COUNT(*) FROM chitalishte WHERE town = 'Пловдив'",
        }

        formatted = SQLResultFormatter.format_sql_result(sql_result)

        assert "РЕЗУЛТАТИ ОТ БАЗА ДАННИ" in formatted
        assert "10 читалища" in formatted
        assert "SELECT" in formatted

    def test_format_sql_result_failure(self):
        """Formatter should format failed SQL result."""
        sql_result = {
            "success": False,
            "error": "Table not found",
        }

        formatted = SQLResultFormatter.format_sql_result(sql_result)

        assert "не беше успешна" in formatted
        assert "Table not found" in formatted

    def test_format_multiple_sql_results(self):
        """Formatter should format multiple SQL results."""
        sql_results = [
            {
                "success": True,
                "answer": "Резултат 1",
                "sql_query": "SELECT 1",
            },
            {
                "success": True,
                "answer": "Резултат 2",
                "sql_query": "SELECT 2",
            },
        ]

        formatted = SQLResultFormatter.format_sql_results_for_rag(sql_results)

        assert "SQL Резултат 1" in formatted
        assert "SQL Резултат 2" in formatted
        assert "Резултат 1" in formatted
        assert "Резултат 2" in formatted


class TestHybridPipelineService:
    """Tests for HybridPipelineService."""

    @pytest.fixture
    def mock_router(self):
        """Create a mock hybrid router."""
        router = MagicMock()
        return router

    @pytest.fixture
    def mock_sql_agent(self):
        """Create a mock SQL agent."""
        agent = MagicMock()
        agent.query = MagicMock(
            return_value={
                "success": True,
                "answer": "Има 10 читалища.",
                "sql_query": "SELECT COUNT(*) FROM chitalishte",
            }
        )
        return agent

    @pytest.fixture
    def mock_rag_chain(self):
        """Create a mock RAG chain."""
        chain = MagicMock()
        chain.query = MagicMock(
            return_value={
                "answer": "Читалището е културна институция.",
                "metadata": {"db_doc_count": 2, "analysis_doc_count": 1},
            }
        )
        chain.query_with_context = MagicMock(
            return_value={
                "answer": "Читалището е културна институция.",
                "context": "Контекст за читалищата...",
                "retrieved_documents": [],
            }
        )
        chain.llm = MagicMock()
        return chain

    @pytest.fixture
    def mock_llm(self):
        """Create a mock LLM for synthesis."""
        try:
            from langchain_core.language_models.chat_models import BaseChatModel
            from langchain_core.messages import AIMessage

            class MockLLM(BaseChatModel):
                def _generate(self, messages, stop=None, run_manager=None, **kwargs):
                    return self._generate_helper(messages, stop, **kwargs)

                def _generate_helper(self, messages, stop=None, **kwargs):
                    return [
                        type("Generation", (), {
                            "message": AIMessage(content="Комбиниран отговор"),
                            "generation_info": {},
                        })()
                    ]

                @property
                def _llm_type(self):
                    return "mock"

            return MockLLM()
        except ImportError:
            pytest.skip("LangChain not available")

    def test_pipeline_routes_to_sql(self, mock_router, mock_sql_agent, mock_rag_chain):
        """Pipeline should route SQL queries to SQL agent only."""
        # Configure router to return SQL intent
        mock_router.route = MagicMock(
            return_value=MagicMock(
                intent=QueryIntent.SQL,
                confidence=0.9,
                explanation="SQL intent detected",
            )
        )

        pipeline = HybridPipelineService(
            router=mock_router,
            sql_agent=mock_sql_agent,
            rag_chain=mock_rag_chain,
        )

        result = pipeline.query("Колко читалища има?")

        assert result["intent"] == "sql"
        assert result["sql_executed"] is True
        assert result["rag_executed"] is False
        assert "10 читалища" in result["answer"]
        mock_sql_agent.query.assert_called_once()
        mock_rag_chain.query.assert_not_called()

    def test_pipeline_routes_to_rag(self, mock_router, mock_sql_agent, mock_rag_chain):
        """Pipeline should route RAG queries to RAG chain only."""
        # Configure router to return RAG intent
        mock_router.route = MagicMock(
            return_value=MagicMock(
                intent=QueryIntent.RAG,
                confidence=0.9,
                explanation="RAG intent detected",
            )
        )

        pipeline = HybridPipelineService(
            router=mock_router,
            sql_agent=mock_sql_agent,
            rag_chain=mock_rag_chain,
        )

        result = pipeline.query("Какво е читалище?")

        assert result["intent"] == "rag"
        assert result["sql_executed"] is False
        assert result["rag_executed"] is True
        assert "културна институция" in result["answer"]
        mock_rag_chain.query.assert_called_once()
        mock_sql_agent.query.assert_not_called()

    def test_pipeline_routes_to_hybrid(
        self, mock_router, mock_sql_agent, mock_rag_chain, mock_llm
    ):
        """Pipeline should route hybrid queries to both SQL and RAG."""
        # Configure router to return hybrid intent
        mock_router.route = MagicMock(
            return_value=MagicMock(
                intent=QueryIntent.HYBRID,
                confidence=0.8,
                explanation="Hybrid intent detected",
            )
        )

        # Mock synthesis chain
        with patch("app.rag.hybrid_pipeline.ChatPromptTemplate") as mock_prompt, \
             patch("app.rag.hybrid_pipeline.RunnablePassthrough") as mock_passthrough:
            mock_prompt.from_messages.return_value = MagicMock()
            mock_passthrough.return_value = MagicMock()

            # Mock chain invoke
            mock_chain = MagicMock()
            mock_chain.invoke = MagicMock(
                return_value=MagicMock(content="Комбиниран отговор с числа и обяснения")
            )
            mock_prompt.from_messages.return_value.__or__ = MagicMock(return_value=mock_chain)

            pipeline = HybridPipelineService(
                router=mock_router,
                sql_agent=mock_sql_agent,
                rag_chain=mock_rag_chain,
                llm=mock_llm,
            )

            # Replace synthesis chain with mock
            pipeline.synthesis_chain = mock_chain

            result = pipeline.query("Колко читалища има и разкажи за тях?")

            assert result["intent"] == "hybrid"
            assert result["sql_executed"] is True
            assert result["rag_executed"] is True
            mock_sql_agent.query.assert_called_once()
            mock_rag_chain.query.assert_called_once()

    def test_query_with_details(self, mock_router, mock_sql_agent, mock_rag_chain):
        """query_with_details should return full context information."""
        mock_router.route = MagicMock(
            return_value=MagicMock(
                intent=QueryIntent.HYBRID,
                confidence=0.8,
                explanation="Hybrid intent",
            )
        )

        with patch("app.rag.hybrid_pipeline.ChatPromptTemplate") as mock_prompt, \
             patch("app.rag.hybrid_pipeline.RunnablePassthrough") as mock_passthrough:
            mock_prompt.from_messages.return_value = MagicMock()
            mock_passthrough.return_value = MagicMock()

            mock_chain = MagicMock()
            mock_chain.invoke = MagicMock(
                return_value=MagicMock(content="Комбиниран отговор")
            )
            mock_prompt.from_messages.return_value.__or__ = MagicMock(return_value=mock_chain)

            pipeline = HybridPipelineService(
                router=mock_router,
                sql_agent=mock_sql_agent,
                rag_chain=mock_rag_chain,
            )
            pipeline.synthesis_chain = mock_chain

            result = pipeline.query_with_details("Колко читалища има?")

            assert "answer" in result
            assert "rag_context" in result
            assert "sql_formatted" in result
            assert "retrieved_documents" in result

    def test_factory_function(self, mock_router, mock_sql_agent, mock_rag_chain):
        """Factory function should create a pipeline service."""
        with patch("app.rag.hybrid_pipeline.ChatPromptTemplate") as mock_prompt, \
             patch("app.rag.hybrid_pipeline.RunnablePassthrough") as mock_passthrough:
            mock_prompt.from_messages.return_value = MagicMock()
            mock_passthrough.return_value = MagicMock()
            mock_chain = MagicMock()
            mock_prompt.from_messages.return_value.__or__ = MagicMock(return_value=mock_chain)

            pipeline = get_hybrid_pipeline_service(
                router=mock_router,
                sql_agent=mock_sql_agent,
                rag_chain=mock_rag_chain,
            )

            assert isinstance(pipeline, HybridPipelineService)
            assert pipeline.router == mock_router
            assert pipeline.sql_agent == mock_sql_agent
            assert pipeline.rag_chain == mock_rag_chain

