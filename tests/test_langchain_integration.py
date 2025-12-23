"""Integration tests for LangChain + Chroma integration."""

import pytest

# Skip this test module entirely if LangChain packages are not installed
pytest.importorskip("langchain_chroma")
pytest.importorskip("langchain_core")

from app.rag.embeddings import HuggingFaceEmbeddingService
from app.rag.indexing import IndexingService
from app.rag.langchain_integration import LangChainChromaFactory, get_langchain_retriever


@pytest.fixture
def indexed_test_chroma(test_db_session, test_chroma_vector_store, seeded_test_data):
    """
    Prepare a Chroma index with some database documents for LangChain tests.

    Uses the same Hugging Face embedding service as other integration tests.
    """
    embedding_service = HuggingFaceEmbeddingService()
    indexing_service = IndexingService(
        vector_store=test_chroma_vector_store,
        embedding_service=embedding_service,
    )

    # Index a few documents from the test database
    stats = indexing_service.index_database_documents(
        db=test_db_session,
        limit=5,
    )

    # Ensure we have something indexed
    assert stats["indexed"] > 0

    return {
        "vector_store": test_chroma_vector_store,
        "embedding_service": embedding_service,
        "indexed_count": stats["indexed"],
    }


class TestLangChainChromaIntegration:
    """Tests for LangChain Chroma integration."""

    def test_factory_creates_vectorstore(self, indexed_test_chroma):
        """Factory should create a LangChain Chroma vectorstore tied to existing collection."""
        factory = LangChainChromaFactory(
            vector_store=indexed_test_chroma["vector_store"],
            embedding_service=indexed_test_chroma["embedding_service"],
        )

        vectorstore = factory.get_vectorstore()

        # Basic sanity checks
        assert vectorstore is not None
        # Perform a simple similarity search using LangChain API
        docs = vectorstore.similarity_search("читалище", k=2)
        assert len(docs) > 0

        # Documents should have metadata including source
        for doc in docs:
            assert isinstance(doc.metadata, dict)
            assert doc.metadata.get("source") == "database"

    def test_get_langchain_retriever_returns_results(self, indexed_test_chroma):
        """High-level helper should return a working LangChain retriever."""
        retriever = get_langchain_retriever(
            k=3,
            vector_store=indexed_test_chroma["vector_store"],
            embedding_service=indexed_test_chroma["embedding_service"],
        )

        docs = retriever.invoke("читалище в Пловдив")

        assert isinstance(docs, list)
        assert len(docs) > 0

        # Retrieved docs should carry the original metadata
        for doc in docs:
            assert "source" in doc.metadata
            assert doc.metadata["source"] == "database"
            # We expect chitalishte_id and year from database metadata
            assert "chitalishte_id" in doc.metadata
            assert "year" in doc.metadata


