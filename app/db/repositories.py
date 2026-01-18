"""Repository pattern for data access layer - read-only queries."""

from typing import Optional

from sqlalchemy.orm import Session, joinedload

from app.db.models import Chitalishta, ChitalishteYearData


class ChitalishteRepository:
    """Repository for Chitalishta read-only queries."""

    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, chitalishta_id: str) -> Optional[Chitalishta]:
        """Get a Chitalishta by ID (UUID)."""
        return self.db.query(Chitalishta).filter(Chitalishta.id == chitalishta_id).first()

    def get_by_reg_n(self, reg_n: str) -> Optional[Chitalishta]:
        """Get a Chitalishta by registration number."""
        return self.db.query(Chitalishta).filter(Chitalishta.reg_n == reg_n).first()

    def get_by_id_with_year_data(
        self, chitalishta_id: str, year: Optional[int] = None
    ) -> Optional[Chitalishta]:
        """
        Get a Chitalishta by ID with related ChitalishteYearData.
        Optionally filter year data by year.
        """
        query = (
            self.db.query(Chitalishta)
            .options(joinedload(Chitalishta.chitalishte_year_data))
            .filter(Chitalishta.id == chitalishta_id)
        )
        chitalishta = query.first()

        if chitalishta and year is not None:
            # Filter year data by year in memory (already loaded)
            chitalishta.chitalishte_year_data = [
                yd for yd in chitalishta.chitalishte_year_data if yd.year == year
            ]

        return chitalishta

    def get_all(
        self,
        municipality_id: Optional[str] = None,
        town: Optional[str] = None,
        status: Optional[str] = None,
        year: Optional[int] = None,
        limit: Optional[int] = None,
        offset: int = 0,
    ) -> list[Chitalishta]:
        """
        Get all Chitalishta records with optional filters.

        Args:
            municipality_id: Filter by municipality ID (UUID)
            town: Filter by town name
            status: Filter by status
            year: Filter by year (requires join with ChitalishteYearData)
            limit: Maximum number of results
            offset: Number of results to skip
        """
        query = self.db.query(Chitalishta)

        # Apply filters
        if municipality_id is not None:
            query = query.filter(Chitalishta.municipality_id == municipality_id)
        if town is not None:
            query = query.filter(Chitalishta.town == town)
        # Note: Chitalishta model doesn't have a status field
        # if status is not None:
        #     query = query.filter(Chitalishta.status == status)

        # Year filter requires join with ChitalishteYearData
        if year is not None:
            query = (
                query.join(ChitalishteYearData).filter(ChitalishteYearData.year == year).distinct()
            )

        # Apply pagination
        if offset > 0:
            query = query.offset(offset)
        if limit is not None:
            query = query.limit(limit)

        return query.all()

    def count(
        self,
        municipality_id: Optional[str] = None,
        town: Optional[str] = None,
        status: Optional[str] = None,
        year: Optional[int] = None,
    ) -> int:
        """Count Chitalishta records with optional filters."""
        query = self.db.query(Chitalishta)

        if municipality_id is not None:
            query = query.filter(Chitalishta.municipality_id == municipality_id)
        if town is not None:
            query = query.filter(Chitalishta.town == town)
        # Note: Chitalishta model doesn't have a status field
        # if status is not None:
        #     query = query.filter(Chitalishta.status == status)

        if year is not None:
            query = (
                query.join(ChitalishteYearData).filter(ChitalishteYearData.year == year).distinct()
            )

        return query.count()


class InformationCardRepository:
    """Repository for ChitalishteYearData read-only queries."""

    def __init__(self, db: Session):
        self.db = db

    def get_by_reg_n_and_year(self, reg_n: str, year: int) -> Optional[ChitalishteYearData]:
        """Get a ChitalishteYearData by reg_n and year (composite primary key)."""
        return (
            self.db.query(ChitalishteYearData)
            .filter(ChitalishteYearData.reg_n == reg_n, ChitalishteYearData.year == year)
            .first()
        )

    def get_by_reg_n_and_year_with_chitalishta(
        self, reg_n: str, year: int
    ) -> Optional[ChitalishteYearData]:
        """Get a ChitalishteYearData by reg_n and year with related Chitalishta."""
        return (
            self.db.query(ChitalishteYearData)
            .options(joinedload(ChitalishteYearData.chitalishta))
            .filter(ChitalishteYearData.reg_n == reg_n, ChitalishteYearData.year == year)
            .first()
        )

    def get_by_chitalishta_id(
        self,
        chitalishta_id: str,
        year: Optional[int] = None,
        limit: Optional[int] = None,
        offset: int = 0,
    ) -> list[ChitalishteYearData]:
        """
        Get all ChitalishteYearData for a specific Chitalishta.

        Args:
            chitalishta_id: The Chitalishta ID (UUID)
            year: Optional filter by year
            limit: Maximum number of results
            offset: Number of results to skip
        """
        query = self.db.query(ChitalishteYearData).filter(
            ChitalishteYearData.chitalishte_id == chitalishta_id
        )

        if year is not None:
            query = query.filter(ChitalishteYearData.year == year)

        if offset > 0:
            query = query.offset(offset)
        if limit is not None:
            query = query.limit(limit)

        return query.all()

    def get_all(
        self,
        year: Optional[int] = None,
        chitalishta_id: Optional[str] = None,
        limit: Optional[int] = None,
        offset: int = 0,
    ) -> list[ChitalishteYearData]:
        """
        Get all ChitalishteYearData records with optional filters.

        Args:
            year: Filter by year
            chitalishta_id: Filter by Chitalishta ID (UUID)
            limit: Maximum number of results
            offset: Number of results to skip
        """
        query = self.db.query(ChitalishteYearData)

        if year is not None:
            query = query.filter(ChitalishteYearData.year == year)
        if chitalishta_id is not None:
            query = query.filter(ChitalishteYearData.chitalishte_id == chitalishta_id)

        if offset > 0:
            query = query.offset(offset)
        if limit is not None:
            query = query.limit(limit)

        return query.all()

    def count(
        self,
        year: Optional[int] = None,
        chitalishta_id: Optional[str] = None,
    ) -> int:
        """Count ChitalishteYearData records with optional filters."""
        query = self.db.query(ChitalishteYearData)

        if year is not None:
            query = query.filter(ChitalishteYearData.year == year)
        if chitalishta_id is not None:
            query = query.filter(ChitalishteYearData.chitalishte_id == chitalishta_id)

        return query.count()
