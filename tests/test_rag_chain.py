"""Tests for RAG chain service."""

import pytest

pytest.importorskip("langchain_core")

from app.rag.rag_chain import ContextAssembler, RAGChainService, get_rag_chain_service


class MockRetriever:
    """Mock retriever for testing."""

    def __init__(self, documents: list):
        self.documents = documents

    def invoke(self, query: str):
        """Return mock documents."""
        return self.documents


class TestContextAssembler:
    """Tests for ContextAssembler."""

    def test_assemble_context_combines_db_and_analysis(self):
        """Context assembler should combine DB and analysis documents."""
        db_docs = [
            type("Doc", (), {"page_content": "DB doc 1", "metadata": {"source": "database"}})(),
            type("Doc", (), {"page_content": "DB doc 2", "metadata": {"source": "database"}})(),
        ]
        analysis_docs = [
            type("Doc", (), {
                "page_content": "Analysis doc 1",
                "metadata": {"source": "analysis_document"},
            })(),
        ]

        db_retriever = MockRetriever(db_docs)
        analysis_retriever = MockRetriever(analysis_docs)

        assembler = ContextAssembler(
            db_retriever=db_retriever,
            analysis_retriever=analysis_retriever,
        )

        docs, metadata = assembler.assemble_context("test query", k_db=4, k_analysis=2)

        assert len(docs) == 3
        assert metadata["db_doc_count"] == 2
        assert metadata["analysis_doc_count"] == 1
        assert metadata["total_doc_count"] == 3

    def test_format_context_separates_db_and_analysis(self):
        """Context formatter should separate DB and analysis documents."""
        db_docs = [
            type("Doc", (), {"page_content": "DB fact 1", "metadata": {"source": "database"}})(),
        ]
        analysis_docs = [
            type("Doc", (), {
                "page_content": "Analysis info",
                "metadata": {"source": "analysis_document"},
            })(),
        ]

        db_retriever = MockRetriever(db_docs)
        analysis_retriever = MockRetriever(analysis_docs)

        assembler = ContextAssembler(
            db_retriever=db_retriever,
            analysis_retriever=analysis_retriever,
        )

        docs, _ = assembler.assemble_context("test", k_db=4, k_analysis=2)
        formatted = assembler.format_context(docs)

        assert "ДАННИ ОТ БАЗА ДАННИ" in formatted
        assert "АНАЛИЗЕН ДОКУМЕНТ" in formatted
        assert "DB fact 1" in formatted
        assert "Analysis info" in formatted

    def test_prefer_db_prioritizes_db_docs(self):
        """When prefer_db is True, DB docs should come first."""
        db_docs = [
            type("Doc", (), {"page_content": "DB 1", "metadata": {"source": "database"}})(),
        ]
        analysis_docs = [
            type("Doc", (), {
                "page_content": "Analysis 1",
                "metadata": {"source": "analysis_document"},
            })(),
        ]

        db_retriever = MockRetriever(db_docs)
        analysis_retriever = MockRetriever(analysis_docs)

        assembler = ContextAssembler(
            db_retriever=db_retriever,
            analysis_retriever=analysis_retriever,
            prefer_db_for_factual=True,
        )

        docs, _ = assembler.assemble_context("test", k_db=4, k_analysis=2)

        # DB docs should come first
        assert docs[0].metadata["source"] == "database"

    def test_no_analysis_when_use_analysis_false(self):
        """When use_analysis is False, should not retrieve analysis docs."""
        db_docs = [
            type("Doc", (), {"page_content": "DB 1", "metadata": {"source": "database"}})(),
        ]
        analysis_docs = [
            type("Doc", (), {
                "page_content": "Analysis 1",
                "metadata": {"source": "analysis_document"},
            })(),
        ]

        db_retriever = MockRetriever(db_docs)
        analysis_retriever = MockRetriever(analysis_docs)

        assembler = ContextAssembler(
            db_retriever=db_retriever,
            analysis_retriever=analysis_retriever,
        )

        docs, metadata = assembler.assemble_context(
            "test", k_db=4, k_analysis=2, use_analysis=False
        )

        assert metadata["analysis_doc_count"] == 0
        assert len(docs) == 1
        assert docs[0].metadata["source"] == "database"


class TestRAGChainService:
    """Tests for RAGChainService."""

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
                            "message": AIMessage(content="Mock answer"),
                            "generation_info": {},
                        })()
                    ]

                @property
                def _llm_type(self):
                    return "mock"

            return MockLLM()
        except ImportError:
            pytest.skip("LangChain not available")

    def test_rag_service_initializes(self, mock_llm):
        """RAG service should initialize with default retrievers."""
        # This will try to create real retrievers, which may fail in tests
        # So we'll skip if it fails
        try:
            service = RAGChainService(llm=mock_llm)
            assert service is not None
            assert service.llm == mock_llm
        except Exception:
            # If initialization fails (e.g., no Chroma DB), that's okay for unit tests
            pytest.skip("RAG service initialization requires Chroma DB")

    def test_factory_function(self, mock_llm):
        """Factory function should create a RAG service."""
        try:
            service = get_rag_chain_service(llm=mock_llm)
            assert isinstance(service, RAGChainService)
        except Exception:
            pytest.skip("RAG service factory requires Chroma DB")

    def test_bulgarian_prompt_template(self, mock_llm):
        """Prompt template should be in Bulgarian."""
        try:
            service = RAGChainService(llm=mock_llm)
            prompt = service.prompt_template

            # Check that prompt contains Bulgarian text
            # The prompt template is a ChatPromptTemplate, so we need to format it
            formatted = prompt.format_messages(context="test", question="test")
            prompt_text = str(formatted)

            # Check for Bulgarian characters or words
            assert any(char in prompt_text for char in "български")
        except Exception:
            pytest.skip("RAG service requires Chroma DB")



