"""LangChain integration for Chroma vector store and embedding services."""

from typing import List, Optional

from app.rag.embeddings import EmbeddingService, get_embedding_service
from app.rag.vector_store import ChromaVectorStore

try:
    from langchain_chroma import Chroma as LangChainChroma
    from langchain_core.embeddings import Embeddings as LangChainEmbeddings
except ImportError as _e:  # pragma: no cover - guarded by tests
    LangChainChroma = None  # type: ignore[assignment]
    LangChainEmbeddings = object  # type: ignore[assignment]
    _LANGCHAIN_IMPORT_ERROR = _e
else:
    _LANGCHAIN_IMPORT_ERROR = None


class LangChainEmbeddingAdapter(LangChainEmbeddings):
    """
    Adapter to use existing EmbeddingService implementations with LangChain.

    This keeps our embedding layer as the single source of truth while satisfying
    LangChain's Embeddings interface.
    """

    def __init__(self, embedding_service: Optional[EmbeddingService] = None):
        self.embedding_service = embedding_service or get_embedding_service()

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """
        Embed a list of documents (LangChain API).

        Args:
            texts: List of texts to embed

        Returns:
            List of embedding vectors
        """
        return self.embedding_service.embed_texts(texts)

    def embed_query(self, text: str) -> List[float]:
        """
        Embed a single query (LangChain API).

        Args:
            text: Query text

        Returns:
            Embedding vector
        """
        return self.embedding_service.embed_text(text)


class LangChainChromaFactory:
    """
    Factory for creating LangChain Chroma vectorstores and retrievers.

    This reuses the existing ChromaVectorStore and embedding service, ensuring
    compatibility with the rest of the system.
    """

    def __init__(
        self,
        vector_store: Optional[ChromaVectorStore] = None,
        embedding_service: Optional[EmbeddingService] = None,
    ):
        if _LANGCHAIN_IMPORT_ERROR is not None:
            raise ImportError(
                "LangChain dependencies are required for LangChainChromaFactory.\n"
                "Install them with:\n"
                "  poetry add langchain langchain-openai langchain-community langchain-chroma"
            ) from _LANGCHAIN_IMPORT_ERROR

        self.vector_store = vector_store or ChromaVectorStore()
        self.embedding_service = embedding_service or get_embedding_service()
        self.embedding_adapter = LangChainEmbeddingAdapter(self.embedding_service)

    def get_vectorstore(self) -> LangChainChroma:
        """
        Create a LangChain Chroma vectorstore bound to the existing collection.

        Returns:
            LangChain Chroma vectorstore
        """
        # Validate and fix dimension mismatch if needed
        expected_dimension = self.embedding_service.get_dimension()
        self.vector_store.validate_and_fix_dimension(expected_dimension)

        # We reuse the existing Chroma client and collection configuration.
        client = self.vector_store.get_client()
        # ChromaVectorStore stores collection_name as an instance attribute.
        collection_name = self.vector_store.collection_name

        return LangChainChroma(
            client=client,
            collection_name=collection_name,
            embedding_function=self.embedding_adapter,
        )

    def get_retriever(
        self,
        k: int = 4,
        score_threshold: Optional[float] = None,
    ):
        """
        Create a LangChain retriever over the existing Chroma collection.

        Args:
            k: Number of documents to retrieve
            score_threshold: Optional similarity score threshold

        Returns:
            LangChain retriever
        """
        vectorstore = self.get_vectorstore()

        search_kwargs = {"k": k}
        if score_threshold is not None:
            search_kwargs["score_threshold"] = score_threshold

        return vectorstore.as_retriever(search_kwargs=search_kwargs)


def get_langchain_retriever(
    k: int = 4,
    score_threshold: Optional[float] = None,
    vector_store: Optional[ChromaVectorStore] = None,
    embedding_service: Optional[EmbeddingService] = None,
):
    """
    Convenience function to get a LangChain retriever using existing services.

    This is the main entry point for other parts of the system that want to use
    LangChain for retrieval while preserving the current abstractions.
    """
    factory = LangChainChromaFactory(
        vector_store=vector_store,
        embedding_service=embedding_service,
    )
    return factory.get_retriever(k=k, score_threshold=score_threshold)


