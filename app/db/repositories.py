"""Repository pattern for data access layer - read-only queries."""

from typing import Optional

from sqlalchemy.orm import Session, joinedload

from app.db.models import Chitalishte, InformationCard


class ChitalishteRepository:
    """Repository for Chitalishte read-only queries."""

    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, chitalishte_id: int) -> Optional[Chitalishte]:
        """Get a Chitalishte by ID."""
        return self.db.query(Chitalishte).filter(Chitalishte.id == chitalishte_id).first()

    def get_by_id_with_cards(
        self, chitalishte_id: int, year: Optional[int] = None
    ) -> Optional[Chitalishte]:
        """
        Get a Chitalishte by ID with related InformationCards.
        Optionally filter cards by year.
        """
        query = (
            self.db.query(Chitalishte)
            .options(joinedload(Chitalishte.information_cards))
            .filter(Chitalishte.id == chitalishte_id)
        )
        chitalishte = query.first()

        if chitalishte and year is not None:
            # Filter cards by year in memory (already loaded)
            chitalishte.information_cards = [
                card for card in chitalishte.information_cards if card.year == year
            ]

        return chitalishte

    def get_all(
        self,
        region: Optional[str] = None,
        town: Optional[str] = None,
        status: Optional[str] = None,
        year: Optional[int] = None,
        limit: Optional[int] = None,
        offset: int = 0,
    ) -> list[Chitalishte]:
        """
        Get all Chitalishte records with optional filters.

        Args:
            region: Filter by region name
            town: Filter by town name
            status: Filter by status
            year: Filter by year (requires join with InformationCard)
            limit: Maximum number of results
            offset: Number of results to skip
        """
        query = self.db.query(Chitalishte)

        # Apply filters
        if region is not None:
            query = query.filter(Chitalishte.region == region)
        if town is not None:
            query = query.filter(Chitalishte.town == town)
        if status is not None:
            query = query.filter(Chitalishte.status == status)

        # Year filter requires join with InformationCard
        if year is not None:
            query = query.join(InformationCard).filter(InformationCard.year == year).distinct()

        # Apply pagination
        if offset > 0:
            query = query.offset(offset)
        if limit is not None:
            query = query.limit(limit)

        return query.all()

    def count(
        self,
        region: Optional[str] = None,
        town: Optional[str] = None,
        status: Optional[str] = None,
        year: Optional[int] = None,
    ) -> int:
        """Count Chitalishte records with optional filters."""
        query = self.db.query(Chitalishte)

        if region is not None:
            query = query.filter(Chitalishte.region == region)
        if town is not None:
            query = query.filter(Chitalishte.town == town)
        if status is not None:
            query = query.filter(Chitalishte.status == status)

        if year is not None:
            query = query.join(InformationCard).filter(InformationCard.year == year).distinct()

        return query.count()


class InformationCardRepository:
    """Repository for InformationCard read-only queries."""

    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, card_id: int) -> Optional[InformationCard]:
        """Get an InformationCard by ID."""
        return self.db.query(InformationCard).filter(InformationCard.id == card_id).first()

    def get_by_id_with_chitalishte(self, card_id: int) -> Optional[InformationCard]:
        """Get an InformationCard by ID with related Chitalishte."""
        return (
            self.db.query(InformationCard)
            .options(joinedload(InformationCard.chitalishte))
            .filter(InformationCard.id == card_id)
            .first()
        )

    def get_by_chitalishte_id(
        self,
        chitalishte_id: int,
        year: Optional[int] = None,
        limit: Optional[int] = None,
        offset: int = 0,
    ) -> list[InformationCard]:
        """
        Get all InformationCards for a specific Chitalishte.

        Args:
            chitalishte_id: The Chitalishte ID
            year: Optional filter by year
            limit: Maximum number of results
            offset: Number of results to skip
        """
        query = self.db.query(InformationCard).filter(
            InformationCard.chitalishte_id == chitalishte_id
        )

        if year is not None:
            query = query.filter(InformationCard.year == year)

        if offset > 0:
            query = query.offset(offset)
        if limit is not None:
            query = query.limit(limit)

        return query.all()

    def get_all(
        self,
        year: Optional[int] = None,
        chitalishte_id: Optional[int] = None,
        limit: Optional[int] = None,
        offset: int = 0,
    ) -> list[InformationCard]:
        """
        Get all InformationCard records with optional filters.

        Args:
            year: Filter by year
            chitalishte_id: Filter by Chitalishte ID
            limit: Maximum number of results
            offset: Number of results to skip
        """
        query = self.db.query(InformationCard)

        if year is not None:
            query = query.filter(InformationCard.year == year)
        if chitalishte_id is not None:
            query = query.filter(InformationCard.chitalishte_id == chitalishte_id)

        if offset > 0:
            query = query.offset(offset)
        if limit is not None:
            query = query.limit(limit)

        return query.all()

    def count(
        self,
        year: Optional[int] = None,
        chitalishte_id: Optional[int] = None,
    ) -> int:
        """Count InformationCard records with optional filters."""
        query = self.db.query(InformationCard)

        if year is not None:
            query = query.filter(InformationCard.year == year)
        if chitalishte_id is not None:
            query = query.filter(InformationCard.chitalishte_id == chitalishte_id)

        return query.count()

