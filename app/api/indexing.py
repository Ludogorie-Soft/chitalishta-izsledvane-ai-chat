"""API endpoints for document indexing."""
from typing import Optional

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.schemas import AnalysisDocumentIngestionRequest
from app.db.database import get_db
from app.rag.indexing import IndexingService

router = APIRouter(prefix="/index", tags=["indexing"])


@router.post("/database")
async def index_database_documents(
    region: Optional[str] = None,
    town: Optional[str] = None,
    status: Optional[str] = None,
    year: Optional[int] = None,
    limit: Optional[int] = None,
    offset: int = 0,
    db: Session = Depends(get_db),
):
    """
    Index database documents into the vector store.

    This endpoint extracts documents from the database, embeds them,
    and stores them in Chroma for RAG retrieval.

    Query Parameters:
        region: Optional filter by region (case-sensitive, must match database exactly)
        town: Optional filter by town (case-sensitive, must match database exactly)
        status: Optional filter by status (case-sensitive, must match database exactly)
        year: Optional filter by year
        limit: Optional limit on number of documents to index
        offset: Number of documents to skip

    Returns:
        Indexing statistics
    """
    try:
        indexing_service = IndexingService()
        stats = indexing_service.index_database_documents(
            db=db,
            region=region,
            town=town,
            status=status,
            year=year,
            limit=limit,
            offset=offset,
        )

        return {
            "status": "success",
            "message": f"Indexed {stats['indexed']} documents successfully.",
            **stats,
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Error indexing documents: {str(e)}",
            "indexed": 0,
            "skipped": 0,
            "errors": 0,
            "total": 0,
        }


@router.post("/analysis-document")
async def index_analysis_document(request: AnalysisDocumentIngestionRequest):
    """
    Index an analysis document into the vector store.

    This endpoint processes a DOCX document, chunks it, embeds the chunks,
    and stores them in Chroma for RAG retrieval.

    Args:
        request: Request containing the document name (e.g., "Chitalishta_demo_ver2.docx")

    Returns:
        Indexing statistics
    """
    try:
        indexing_service = IndexingService()
        stats = indexing_service.index_analysis_document(request.document_name)

        return {
            "status": "success",
            "message": f"Indexed {stats['indexed']} chunks from analysis document successfully.",
            **stats,
        }
    except FileNotFoundError as e:
        return {
            "status": "error",
            "message": f"Document file not found: {str(e)}",
            "indexed": 0,
            "skipped": 0,
            "errors": 0,
            "total": 0,
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Error indexing document: {str(e)}",
            "indexed": 0,
            "skipped": 0,
            "errors": 0,
            "total": 0,
        }


@router.get("/stats")
async def get_index_stats():
    """
    Get statistics about the indexed documents.

    Returns:
        Index statistics including total count and source distribution
    """
    try:
        indexing_service = IndexingService()
        stats = indexing_service.get_index_stats()

        return {
            "status": "success",
            **stats,
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Error getting index stats: {str(e)}",
            "total_documents": 0,
            "source_distribution": {},
        }


@router.post("/clear")
async def clear_index():
    """
    Clear all documents from the index.

    This deletes all indexed documents but keeps the collection structure.
    """
    try:
        indexing_service = IndexingService()
        indexing_service.clear_index()

        return {
            "status": "success",
            "message": "Index cleared successfully.",
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Error clearing index: {str(e)}",
        }

