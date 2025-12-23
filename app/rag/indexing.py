"""Indexing service for embedding and storing documents in Chroma."""
import hashlib
import json
from typing import List, Optional

from sqlalchemy.orm import Session

from app.rag.embeddings import EmbeddingService, get_embedding_service
from app.rag.vector_store import ChromaVectorStore


class IndexingService:
    """Service for indexing documents into Chroma vector store."""

    # Batch size for embedding generation
    EMBEDDING_BATCH_SIZE = 100

    def __init__(
        self,
        vector_store: Optional[ChromaVectorStore] = None,
        embedding_service: Optional[EmbeddingService] = None,
    ):
        """
        Initialize the indexing service.

        Args:
            vector_store: ChromaVectorStore instance. If None, creates a new one.
            embedding_service: EmbeddingService instance. If None, uses config default.
        """
        self.vector_store = vector_store or ChromaVectorStore()
        self.embedding_service = embedding_service or get_embedding_service()
        self.collection = self.vector_store.get_collection()

    def _generate_document_id(self, document: dict) -> str:
        """
        Generate a unique ID for a document based on its content and metadata.

        This ensures idempotent indexing - same document won't be indexed twice.

        Args:
            document: Document dictionary with content and metadata

        Returns:
            Unique document ID (hash)
        """
        # Create a unique identifier based on source and key fields
        metadata = document.get("metadata", {})
        source = metadata.get("source", "unknown")

        if source == "database":
            # For DB documents: use chitalishte_id + year + information_card_id
            chitalishte_id = metadata.get("chitalishte_id")
            year = metadata.get("year")
            card_id = metadata.get("information_card_id")
            unique_key = f"db_{chitalishte_id}_{year}_{card_id}"
        elif source == "analysis_document":
            # For analysis documents: use document_name + section_index + chunk_index
            doc_name = metadata.get("document_name", "")
            section_idx = metadata.get("section_index", 0)
            chunk_idx = metadata.get("chunk_index", 0)
            unique_key = f"analysis_{doc_name}_{section_idx}_{chunk_idx}"
        else:
            # Fallback: use content hash
            content = document.get("content", "")
            unique_key = f"fallback_{hashlib.md5(content.encode()).hexdigest()}"

        # Generate hash for the unique key
        return hashlib.sha256(unique_key.encode()).hexdigest()[:16]

    def _prepare_metadata_for_chroma(self, metadata: dict) -> dict:
        """
        Prepare metadata for Chroma storage.

        Chroma requires metadata values to be strings, numbers, or booleans.
        We convert complex types to strings.

        Args:
            metadata: Original metadata dictionary

        Returns:
            Chroma-compatible metadata dictionary
        """
        chroma_metadata = {}
        for key, value in metadata.items():
            if value is None:
                continue
            elif isinstance(value, (str, int, float, bool)):
                chroma_metadata[key] = value
            elif isinstance(value, dict):
                # Convert dict to JSON string (Chroma doesn't support nested dicts)
                chroma_metadata[key] = json.dumps(value, ensure_ascii=False)
            else:
                # Convert other types to string
                chroma_metadata[str(key)] = str(value)

        return chroma_metadata

    def index_documents(self, documents: List[dict], batch_size: Optional[int] = None) -> dict:
        """
        Index a list of documents into Chroma.

        Args:
            documents: List of document dictionaries with 'content' and 'metadata'
            batch_size: Batch size for embedding generation. If None, uses default.

        Returns:
            Dictionary with indexing statistics
        """
        if not documents:
            return {
                "indexed": 0,
                "skipped": 0,
                "errors": 0,
                "total": 0,
            }

        batch_size = batch_size or self.EMBEDDING_BATCH_SIZE

        # Filter valid documents
        valid_documents = [doc for doc in documents if doc.get("is_valid", True)]
        skipped = len(documents) - len(valid_documents)

        if not valid_documents:
            return {
                "indexed": 0,
                "skipped": skipped,
                "errors": 0,
                "total": len(documents),
            }

        # Extract contents for embedding
        contents = [doc["content"] for doc in valid_documents]

        # Generate embeddings in batches
        all_embeddings = []
        for i in range(0, len(contents), batch_size):
            batch = contents[i : i + batch_size]
            try:
                batch_embeddings = self.embedding_service.embed_texts(batch)
                all_embeddings.extend(batch_embeddings)
            except Exception as e:
                # If embedding fails, skip this batch
                print(f"Error embedding batch {i}: {e}")
                # Add None placeholders for failed embeddings
                all_embeddings.extend([None] * len(batch))

        # Prepare data for Chroma
        ids = []
        embeddings = []
        metadatas = []
        documents_list = []

        indexed = 0
        errors = 0

        for doc, embedding in zip(valid_documents, all_embeddings):
            if embedding is None:
                errors += 1
                continue

            try:
                # Generate unique ID
                doc_id = self._generate_document_id(doc)

                # Prepare metadata
                chroma_metadata = self._prepare_metadata_for_chroma(doc.get("metadata", {}))

                ids.append(doc_id)
                embeddings.append(embedding)
                metadatas.append(chroma_metadata)
                documents_list.append(doc["content"])

                indexed += 1
            except Exception as e:
                print(f"Error preparing document for indexing: {e}")
                errors += 1

        # Add to Chroma collection
        if ids:
            try:
                self.collection.add(
                    ids=ids,
                    embeddings=embeddings,
                    metadatas=metadatas,
                    documents=documents_list,
                )
            except Exception as e:
                print(f"Error adding documents to Chroma: {e}")
                errors += indexed  # Count all as errors if batch add fails
                indexed = 0

        return {
            "indexed": indexed,
            "skipped": skipped,
            "errors": errors,
            "total": len(documents),
        }

    def index_database_documents(
        self,
        db: Session,
        region: Optional[str] = None,
        town: Optional[str] = None,
        status: Optional[str] = None,
        year: Optional[int] = None,
        limit: Optional[int] = None,
        offset: int = 0,
    ) -> dict:
        """
        Index database documents into Chroma.

        Args:
            db: Database session
            region: Optional filter by region
            town: Optional filter by town
            status: Optional filter by status
            year: Optional filter by year
            limit: Optional limit on number of documents
            offset: Number of documents to skip

        Returns:
            Dictionary with indexing statistics
        """
        from app.services.assembly import DocumentAssemblyService

        assembly_service = DocumentAssemblyService(db)
        documents = assembly_service.assemble_all_documents(
            region=region,
            town=town,
            status=status,
            year=year,
            limit=limit,
            offset=offset,
        )

        return self.index_documents(documents)

    def index_analysis_document(self, document_name: str) -> dict:
        """
        Index an analysis document into Chroma.

        Args:
            document_name: Name of the DOCX file (e.g., "Chitalishta_demo_ver2.docx")

        Returns:
            Dictionary with indexing statistics
        """
        from app.services.document_processor import DocumentProcessor

        processor = DocumentProcessor(document_name=document_name)
        chunks = processor.chunk_document()

        return self.index_documents(chunks)

    def clear_index(self):
        """Clear all documents from the index."""
        self.vector_store.clear_collection()

    def get_index_stats(self) -> dict:
        """
        Get statistics about the index.

        Returns:
            Dictionary with index statistics
        """
        count = self.vector_store.get_collection_count()

        # Query for each source type to get accurate counts
        sources = {}
        known_sources = ["database", "analysis_document"]

        for source in known_sources:
            try:
                # Query Chroma for documents with this source type
                results = self.collection.get(
                    where={"source": source},
                    limit=10000,  # Large limit to get all documents of this type
                )
                if results.get("ids"):
                    sources[source] = len(results["ids"])
            except Exception:
                # If query fails, try to count from sample
                pass

        # If we couldn't get counts via queries, fall back to sampling
        if not sources and count > 0:
            try:
                # Get all documents (or as many as possible)
                results = self.collection.get(limit=min(10000, count))
                if results.get("metadatas"):
                    for metadata in results["metadatas"]:
                        source = metadata.get("source", "unknown")
                        sources[source] = sources.get(source, 0) + 1
            except Exception:
                pass

        return {
            "total_documents": count,
            "source_distribution": sources,
        }

