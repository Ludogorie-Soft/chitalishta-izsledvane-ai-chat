"""Chroma vector store service for RAG system."""
from pathlib import Path
from typing import Optional

import chromadb
from chromadb.config import Settings as ChromaSettings

from app.core.config import settings


class ChromaVectorStore:
    """Service for managing Chroma vector store."""

    def __init__(self, persist_directory: Optional[str] = None, collection_name: Optional[str] = None):
        """
        Initialize Chroma vector store.

        Args:
            persist_directory: Directory to persist Chroma data. If None, uses config default.
            collection_name: Name of the collection. If None, uses config default.
        """
        self.persist_directory = persist_directory or settings.chroma_persist_directory
        self.collection_name = collection_name or settings.chroma_collection_name

        # Convert to absolute path
        persist_path = Path(self.persist_directory)
        if not persist_path.is_absolute():
            # Relative to project root
            project_root = Path(__file__).parent.parent.parent
            persist_path = project_root / persist_path

        self.persist_path = persist_path
        self.persist_path.mkdir(parents=True, exist_ok=True)

        # Initialize Chroma client with persistence
        self.client = chromadb.PersistentClient(
            path=str(self.persist_path),
            settings=ChromaSettings(
                anonymized_telemetry=False,
                allow_reset=True,
            ),
        )

        # Get or create collection
        self.collection = self._get_or_create_collection()

    def _get_or_create_collection(self):
        """
        Get existing collection or create a new one.

        Returns:
            Chroma collection
        """
        try:
            # Try to get existing collection
            collection = self.client.get_collection(name=self.collection_name)
            return collection
        except Exception:
            # Collection doesn't exist, create it
            collection = self.client.create_collection(
                name=self.collection_name,
                metadata={"description": "Chitalishta RAG documents collection"},
            )
            return collection

    def clear_collection(self):
        """
        Clear all documents from the collection.

        This deletes all documents but keeps the collection structure.
        """
        # Delete the collection and recreate it
        try:
            self.client.delete_collection(name=self.collection_name)
        except Exception:
            # Collection might not exist, which is fine
            pass

        # Recreate the collection and update reference
        self.collection = self.client.create_collection(
            name=self.collection_name,
            metadata={"description": "Chitalishta RAG documents collection"},
        )

    def reset_collection(self):
        """
        Reset the entire collection (delete and recreate).

        This is a more aggressive reset that ensures a clean state.
        """
        self.clear_collection()

    def get_collection(self):
        """
        Get the Chroma collection instance.

        Returns:
            Chroma collection
        """
        return self.collection

    def get_client(self):
        """
        Get the Chroma client instance.

        Returns:
            Chroma client
        """
        return self.client

    def collection_exists(self) -> bool:
        """
        Check if the collection exists.

        Returns:
            True if collection exists, False otherwise
        """
        try:
            self.client.get_collection(name=self.collection_name)
            return True
        except Exception:
            return False

    def get_collection_count(self) -> int:
        """
        Get the number of documents in the collection.

        Returns:
            Number of documents
        """
        try:
            result = self.collection.count()
            return result
        except Exception:
            return 0

