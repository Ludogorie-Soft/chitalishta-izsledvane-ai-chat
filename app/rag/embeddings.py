"""Embedding services for RAG system."""
from abc import ABC, abstractmethod
from typing import List

from app.core.config import settings


class EmbeddingService(ABC):
    """Abstract base class for embedding services."""

    @abstractmethod
    def embed_text(self, text: str) -> List[float]:
        """
        Generate embedding for a single text.

        Args:
            text: Text to embed

        Returns:
            List of floats representing the embedding vector
        """
        pass

    @abstractmethod
    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for multiple texts (batch processing).

        Args:
            texts: List of texts to embed

        Returns:
            List of embedding vectors
        """
        pass

    @abstractmethod
    def get_dimension(self) -> int:
        """
        Get the dimension of embeddings produced by this service.

        Returns:
            Dimension of the embedding vector
        """
        pass


class OpenAIEmbeddingService(EmbeddingService):
    """OpenAI embedding service implementation."""

    def __init__(self, api_key: str = None, model: str = None):
        """
        Initialize OpenAI embedding service.

        Args:
            api_key: OpenAI API key. If None, uses config default.
            model: OpenAI embedding model name. If None, uses config default.
        """
        try:
            from openai import OpenAI
        except ImportError:
            raise ImportError(
                "openai package is required for OpenAI embeddings. "
                "Install it with: poetry add openai"
            )

        self.api_key = api_key or settings.openai_api_key
        self.model = model or settings.openai_embedding_model

        if not self.api_key:
            raise ValueError("OpenAI API key is required. Set OPENAI_API_KEY in .env file.")

        self.client = OpenAI(api_key=self.api_key)
        self._dimension = None  # Will be determined on first call

    def embed_text(self, text: str) -> List[float]:
        """Generate embedding for a single text using OpenAI."""
        response = self.client.embeddings.create(
            model=self.model,
            input=text,
        )
        embedding = response.data[0].embedding
        if self._dimension is None:
            self._dimension = len(embedding)
        return embedding

    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts using OpenAI (batch)."""
        response = self.client.embeddings.create(
            model=self.model,
            input=texts,
        )
        embeddings = [item.embedding for item in response.data]
        if self._dimension is None and embeddings:
            self._dimension = len(embeddings[0])
        return embeddings

    def get_dimension(self) -> int:
        """Get the dimension of OpenAI embeddings."""
        if self._dimension is None:
            # Make a test call to determine dimension
            _ = self.embed_text("test")
        return self._dimension


class HuggingFaceEmbeddingService(EmbeddingService):
    """Hugging Face embedding service implementation."""

    def __init__(self, model_name: str = None):
        """
        Initialize Hugging Face embedding service.

        Args:
            model_name: Hugging Face model name. If None, uses config default.
        """
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError:
            raise ImportError(
                "sentence-transformers package is required for Hugging Face embeddings. "
                "Install it with: poetry add sentence-transformers"
            )

        self.model_name = model_name or settings.huggingface_model_name
        self.model = SentenceTransformer(self.model_name)
        self._dimension = self.model.get_sentence_embedding_dimension()

    def embed_text(self, text: str) -> List[float]:
        """Generate embedding for a single text using Hugging Face."""
        embedding = self.model.encode(text, convert_to_numpy=False)
        return embedding.tolist()

    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts using Hugging Face (batch)."""
        embeddings = self.model.encode(texts, convert_to_numpy=False)
        return [emb.tolist() for emb in embeddings]

    def get_dimension(self) -> int:
        """Get the dimension of Hugging Face embeddings."""
        return self._dimension


def get_embedding_service(provider: str = None) -> EmbeddingService:
    """
    Factory function to get the appropriate embedding service.

    Args:
        provider: Embedding provider name ("openai" or "huggingface").
                  If None, uses config default.

    Returns:
        EmbeddingService instance

    Raises:
        ValueError: If provider is not supported
    """
    provider = provider or settings.embedding_provider

    if provider.lower() == "openai":
        return OpenAIEmbeddingService()
    elif provider.lower() == "huggingface":
        return HuggingFaceEmbeddingService()
    else:
        raise ValueError(
            f"Unsupported embedding provider: {provider}. "
            "Supported providers: 'openai', 'huggingface'"
        )

