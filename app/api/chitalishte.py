"""API endpoints for Chitalishta."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.schemas import (
    ChitalishtaListResponse,
    ChitalishtaResponse,
    ChitalishtaWithYearDataResponse,
    ChitalishteYearDataListResponse,
)
from app.db.database import get_db
from app.db.repositories import ChitalishteRepository, InformationCardRepository

router = APIRouter(prefix="/chitalishte", tags=["System API"])


@router.get("/{chitalishta_id}", response_model=ChitalishtaResponse)
async def get_chitalishta(
    chitalishta_id: str,
    db: Session = Depends(get_db),
):
    """
    Get a single Chitalishta by ID (UUID).

    - **chitalishta_id**: The UUID of the Chitalishta to retrieve
    """
    repo = ChitalishteRepository(db)
    chitalishta = repo.get_by_id(chitalishta_id)

    if not chitalishta:
        raise HTTPException(status_code=404, detail="Chitalishta not found")

    return chitalishta


@router.get("/by-reg-n/{reg_n}", response_model=ChitalishtaResponse)
async def get_chitalishta_by_reg_n(
    reg_n: str,
    db: Session = Depends(get_db),
):
    """
    Get a single Chitalishta by registration number.

    - **reg_n**: The registration number of the Chitalishta to retrieve
    """
    repo = ChitalishteRepository(db)
    chitalishta = repo.get_by_reg_n(reg_n)

    if not chitalishta:
        raise HTTPException(status_code=404, detail="Chitalishta not found")

    return chitalishta


@router.get("/{chitalishta_id}/with-year-data", response_model=ChitalishtaWithYearDataResponse)
async def get_chitalishta_with_year_data(
    chitalishta_id: str,
    year: Optional[int] = Query(None, description="Filter ChitalishteYearData by year"),
    db: Session = Depends(get_db),
):
    """
    Get a Chitalishta by ID with related ChitalishteYearData.

    - **chitalishta_id**: The UUID of the Chitalishta to retrieve
    - **year**: Optional year filter for ChitalishteYearData
    """
    repo = ChitalishteRepository(db)
    chitalishta = repo.get_by_id_with_year_data(chitalishta_id, year=year)

    if not chitalishta:
        raise HTTPException(status_code=404, detail="Chitalishta not found")

    return chitalishta


@router.get("", response_model=ChitalishtaListResponse)
async def list_chitalishta(
    municipality_id: Optional[str] = Query(None, description="Filter by municipality ID (UUID)"),
    town: Optional[str] = Query(None, description="Filter by town"),
    status: Optional[str] = Query(None, description="Filter by status"),
    year: Optional[int] = Query(None, description="Filter by year (via ChitalishteYearData)"),
    limit: Optional[int] = Query(100, ge=1, le=1000, description="Maximum number of results"),
    offset: int = Query(0, ge=0, description="Number of results to skip"),
    db: Session = Depends(get_db),
):
    """
    Get a list of Chitalishta records with optional filters.

    - **municipality_id**: Filter by municipality ID (UUID)
    - **town**: Filter by town name
    - **status**: Filter by status
    - **year**: Filter by year (requires ChitalishteYearData with matching year)
    - **limit**: Maximum number of results (1-1000, default: 100)
    - **offset**: Number of results to skip (default: 0)
    """
    repo = ChitalishteRepository(db)

    items = repo.get_all(
        municipality_id=municipality_id,
        town=town,
        status=status,
        year=year,
        limit=limit,
        offset=offset,
    )

    total = repo.count(municipality_id=municipality_id, town=town, status=status, year=year)

    return ChitalishtaListResponse(
        items=items,
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/{chitalishta_id}/year-data", response_model=ChitalishteYearDataListResponse)
async def get_chitalishta_year_data(
    chitalishta_id: str,
    year: Optional[int] = Query(None, description="Filter ChitalishteYearData by year"),
    limit: Optional[int] = Query(100, ge=1, le=1000, description="Maximum number of results"),
    offset: int = Query(0, ge=0, description="Number of results to skip"),
    db: Session = Depends(get_db),
):
    """
    Get ChitalishteYearData for a specific Chitalishta.

    - **chitalishta_id**: The UUID of the Chitalishta
    - **year**: Optional year filter for ChitalishteYearData
    - **limit**: Maximum number of results (1-1000, default: 100)
    - **offset**: Number of results to skip (default: 0)
    """
    # Verify Chitalishta exists
    chitalishta_repo = ChitalishteRepository(db)
    chitalishta = chitalishta_repo.get_by_id(chitalishta_id)

    if not chitalishta:
        raise HTTPException(status_code=404, detail="Chitalishta not found")

    # Get ChitalishteYearData
    year_data_repo = InformationCardRepository(db)
    items = year_data_repo.get_by_chitalishta_id(
        chitalishta_id=chitalishta_id,
        year=year,
        limit=limit,
        offset=offset,
    )

    total = year_data_repo.count(chitalishta_id=chitalishta_id, year=year)

    return ChitalishteYearDataListResponse(
        items=items,
        total=total,
        limit=limit,
        offset=offset,
    )
