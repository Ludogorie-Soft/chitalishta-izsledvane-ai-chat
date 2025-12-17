"""API endpoints for Chitalishte."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.schemas import (
    ChitalishteListResponse,
    ChitalishteResponse,
    ChitalishteWithCardsResponse,
    InformationCardListResponse,
)
from app.db.database import get_db
from app.db.repositories import ChitalishteRepository, InformationCardRepository

router = APIRouter(prefix="/chitalishte", tags=["chitalishte"])


@router.get("/{chitalishte_id}", response_model=ChitalishteResponse)
async def get_chitalishte(
    chitalishte_id: int,
    db: Session = Depends(get_db),
):
    """
    Get a single Chitalishte by ID.

    - **chitalishte_id**: The ID of the Chitalishte to retrieve
    """
    repo = ChitalishteRepository(db)
    chitalishte = repo.get_by_id(chitalishte_id)

    if not chitalishte:
        raise HTTPException(status_code=404, detail="Chitalishte not found")

    return chitalishte


@router.get("/{chitalishte_id}/with-cards", response_model=ChitalishteWithCardsResponse)
async def get_chitalishte_with_cards(
    chitalishte_id: int,
    year: Optional[int] = Query(None, description="Filter InformationCards by year"),
    db: Session = Depends(get_db),
):
    """
    Get a Chitalishte by ID with related InformationCards.

    - **chitalishte_id**: The ID of the Chitalishte to retrieve
    - **year**: Optional year filter for InformationCards
    """
    repo = ChitalishteRepository(db)
    chitalishte = repo.get_by_id_with_cards(chitalishte_id, year=year)

    if not chitalishte:
        raise HTTPException(status_code=404, detail="Chitalishte not found")

    return chitalishte


@router.get("", response_model=ChitalishteListResponse)
async def list_chitalishte(
    region: Optional[str] = Query(None, description="Filter by region"),
    town: Optional[str] = Query(None, description="Filter by town"),
    status: Optional[str] = Query(None, description="Filter by status"),
    year: Optional[int] = Query(None, description="Filter by year (via InformationCard)"),
    limit: Optional[int] = Query(100, ge=1, le=1000, description="Maximum number of results"),
    offset: int = Query(0, ge=0, description="Number of results to skip"),
    db: Session = Depends(get_db),
):
    """
    Get a list of Chitalishte records with optional filters.

    - **region**: Filter by region name
    - **town**: Filter by town name
    - **status**: Filter by status
    - **year**: Filter by year (requires InformationCard with matching year)
    - **limit**: Maximum number of results (1-1000, default: 100)
    - **offset**: Number of results to skip (default: 0)
    """
    repo = ChitalishteRepository(db)

    items = repo.get_all(
        region=region,
        town=town,
        status=status,
        year=year,
        limit=limit,
        offset=offset,
    )

    total = repo.count(region=region, town=town, status=status, year=year)

    return ChitalishteListResponse(
        items=items,
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/{chitalishte_id}/cards", response_model=InformationCardListResponse)
async def get_chitalishte_cards(
    chitalishte_id: int,
    year: Optional[int] = Query(None, description="Filter InformationCards by year"),
    limit: Optional[int] = Query(100, ge=1, le=1000, description="Maximum number of results"),
    offset: int = Query(0, ge=0, description="Number of results to skip"),
    db: Session = Depends(get_db),
):
    """
    Get InformationCards for a specific Chitalishte.

    - **chitalishte_id**: The ID of the Chitalishte
    - **year**: Optional year filter for InformationCards
    - **limit**: Maximum number of results (1-1000, default: 100)
    - **offset**: Number of results to skip (default: 0)
    """
    # Verify Chitalishte exists
    chitalishte_repo = ChitalishteRepository(db)
    chitalishte = chitalishte_repo.get_by_id(chitalishte_id)

    if not chitalishte:
        raise HTTPException(status_code=404, detail="Chitalishte not found")

    # Get InformationCards
    card_repo = InformationCardRepository(db)
    items = card_repo.get_by_chitalishte_id(
        chitalishte_id=chitalishte_id,
        year=year,
        limit=limit,
        offset=offset,
    )

    total = card_repo.count(chitalishte_id=chitalishte_id, year=year)

    return InformationCardListResponse(
        items=items,
        total=total,
        limit=limit,
        offset=offset,
    )
