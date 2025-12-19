"""API endpoints for ingestion preview."""
from typing import Optional

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.schemas import (
    DocumentPreview,
    DocumentMetadata,
    DocumentSizeInfo,
    IngestionPreviewRequest,
    IngestionPreviewResponse,
)
from app.db.database import get_db
from app.services.assembly import DocumentAssemblyService

router = APIRouter(prefix="/ingest", tags=["ingestion"])


@router.post("/preview", response_model=IngestionPreviewResponse)
async def preview_ingestion(
    request: IngestionPreviewRequest,
    db: Session = Depends(get_db),
):
    """
    Preview documents that would be ingested into the RAG system.

    This endpoint shows what documents would be created from the database
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

