"""API endpoints for vector store management."""
from fastapi import APIRouter

from app.rag.vector_store import ChromaVectorStore

router = APIRouter(prefix="/vector-store", tags=["vector-store"])


@router.get("/status")
async def get_vector_store_status():
    """
    Get vector store status and information.

    Returns:
        Status information including collection name, document count, and persistence path
    """
    try:
        vector_store = ChromaVectorStore()
        collection = vector_store.get_collection()
        count = vector_store.get_collection_count()

        return {
            "status": "ok",
            "collection_name": vector_store.collection_name,
            "document_count": count,
            "persist_directory": str(vector_store.persist_path),
            "collection_exists": vector_store.collection_exists(),
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e),
        }


@router.post("/clear")
async def clear_vector_store():
    """
    Clear all documents from the vector store collection.

    This deletes all documents but keeps the collection structure.
    """
    try:
        vector_store = ChromaVectorStore()
        vector_store.clear_collection()
        count = vector_store.get_collection_count()

        return {
            "status": "success",
            "message": "Collection cleared successfully",
            "document_count": count,
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e),
        }


@router.post("/reset")
async def reset_vector_store():
    """
    Reset the entire vector store collection.

    This is a more aggressive reset that deletes and recreates the collection.
    """
    try:
        vector_store = ChromaVectorStore()
        vector_store.reset_collection()
        count = vector_store.get_collection_count()

        return {
            "status": "success",
            "message": "Collection reset successfully",
            "document_count": count,
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e),
        }


