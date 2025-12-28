"""API endpoints for ingestion preview."""
from typing import Optional

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.schemas import (
    AnalysisDocumentIngestionRequest,
    AnalysisDocumentIngestionResponse,
    DocumentPreview,
    DocumentMetadata,
    DocumentSizeInfo,
    IngestionPreviewRequest,
    IngestionPreviewResponse,
)
from app.db.database import get_db
from app.services.assembly import DocumentAssemblyService
from app.services.document_processor import DocumentProcessor

router = APIRouter(prefix="/ingest", tags=["Setup API"])


@router.post("/database", response_model=IngestionPreviewResponse)
async def preview_ingestion(
    request: IngestionPreviewRequest,
    db: Session = Depends(get_db),
):
    """
    Preview documents that would be ingested into the RAG system.

    This endpoint shows what documents would be created from the PostgreSQL database
    before actually ingesting them into the vector store.

    - **region**: Optional filter by region
    - **town**: Optional filter by town
    - **status**: Optional filter by status
    - **year**: Optional filter by year (if None, creates documents for all years)
    - **limit**: Maximum number of documents to preview (default: 10, max: 100)
    """
    # Limit the preview to reasonable size
    limit = min(request.limit or 10, 100)

    assembly_service = DocumentAssemblyService(db)

    # Assemble documents
    documents = assembly_service.assemble_all_documents(
        region=request.region,
        town=request.town,
        status=request.status,
        year=request.year,
        limit=limit,
        offset=0,
    )

    # Get statistics
    statistics = assembly_service.get_document_statistics(documents)

    # Convert to Pydantic models
    preview_documents = []
    for doc in documents:
        preview_documents.append(
            DocumentPreview(
                content=doc["content"],
                metadata=DocumentMetadata(**doc["metadata"]),
                size_info=DocumentSizeInfo(**doc["size_info"]),
                is_valid=doc["is_valid"],
            )
        )

    return IngestionPreviewResponse(
        documents=preview_documents,
        statistics=statistics,
        total_available=None,  # Could calculate total if needed
    )


@router.post("/analysis-document", response_model=AnalysisDocumentIngestionResponse)
async def ingest_analysis_document(request: AnalysisDocumentIngestionRequest):
    """
    Ingest an analysis document into the system.

    This endpoint processes a DOCX document from the documents/ directory,
    chunks it, and prepares it for embedding. The document is chunked using
    hierarchical strategy:
    - Step 1: Split by headings/sections
    - Step 2: Split long sections by paragraphs (keep chunks under 700-900 tokens)
    - Step 3: Apply light overlap (10-15% overlap between chunks)

    Args:
        request: Request containing the document name (e.g., "Chitalishta_demo_ver2.docx")

    Returns:
        Ingestion status, chunk count, and preview of created chunks
    """
    try:
        processor = DocumentProcessor(document_name=request.document_name)
        chunks = processor.chunk_document()

        # Convert to Pydantic models
        chunk_previews = []
        for chunk in chunks:
            chunk_previews.append(
                DocumentPreview(
                    content=chunk["content"],
                    metadata=DocumentMetadata(**chunk["metadata"]),
                    size_info=DocumentSizeInfo(**chunk["size_info"]),
                    is_valid=chunk["is_valid"],
                )
            )

        # Calculate statistics
        valid_chunks = sum(1 for chunk in chunks if chunk["is_valid"])
        invalid_chunks = len(chunks) - valid_chunks
        sizes = [chunk["size_info"]["estimated_tokens"] for chunk in chunks]
        avg_size = int(sum(sizes) / len(sizes)) if sizes else 0

        statistics = {
            "total_chunks": len(chunks),
            "valid_chunks": valid_chunks,
            "invalid_chunks": invalid_chunks,
            "average_size": avg_size,
            "min_size": min(sizes) if sizes else 0,
            "max_size": max(sizes) if sizes else 0,
        }

        return AnalysisDocumentIngestionResponse(
            status="success",
            message=f"Analysis document processed successfully. Created {len(chunks)} chunks.",
            chunks_created=len(chunks),
            chunks=chunk_previews,
            statistics=statistics,
        )

    except FileNotFoundError as e:
        return AnalysisDocumentIngestionResponse(
            status="error",
            message=f"Document file not found: {str(e)}",
            chunks_created=0,
            chunks=[],
            statistics={},
        )
    except Exception as e:
        return AnalysisDocumentIngestionResponse(
            status="error",
            message=f"Error processing document: {str(e)}",
            chunks_created=0,
            chunks=[],
            statistics={},
        )

