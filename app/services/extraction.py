"""Data extraction service for RAG ingestion pipeline."""
from typing import Optional

from sqlalchemy.orm import Session

from app.db.repositories import ChitalishteRepository, InformationCardRepository


class DataExtractionService:
    """Service for extracting raw data from database for RAG ingestion."""

    def __init__(self, db: Session):
        """
        Initialize the data extraction service.

        Args:
            db: Database session
        """
        self.db = db
        self.chitalishte_repo = ChitalishteRepository(db)
        self.card_repo = InformationCardRepository(db)

    def extract_chitalishte_data(
        self,
        region: Optional[str] = None,
        town: Optional[str] = None,
        status: Optional[str] = None,
        year: Optional[int] = None,
        limit: Optional[int] = None,
        offset: int = 0,
    ) -> list[dict]:
        """
        Extract Chitalishte data as dictionaries.

        Args:
            region: Optional filter by region
            town: Optional filter by town
            status: Optional filter by status
            year: Optional filter by year (via InformationCard)
            limit: Optional limit on number of results
            offset: Number of results to skip

        Returns:
            List of dictionaries containing Chitalishte data
        """
        chitalishte_list = self.chitalishte_repo.get_all(
            region=region,
            town=town,
            status=status,
            year=year,
            limit=limit,
            offset=offset,
        )

        return [self._chitalishte_to_dict(chitalishte) for chitalishte in chitalishte_list]

    def extract_information_card_data(
        self,
        chitalishte_id: Optional[int] = None,
        year: Optional[int] = None,
        limit: Optional[int] = None,
        offset: int = 0,
    ) -> list[dict]:
        """
        Extract InformationCard data as dictionaries.

        Args:
            chitalishte_id: Optional filter by Chitalishte ID
            year: Optional filter by year
            limit: Optional limit on number of results
            offset: Number of results to skip

        Returns:
            List of dictionaries containing InformationCard data
        """
        cards = self.card_repo.get_all(
            chitalishte_id=chitalishte_id,
            year=year,
            limit=limit,
            offset=offset,
        )

        return [self._information_card_to_dict(card) for card in cards]

    def extract_chitalishte_with_cards(
        self,
        chitalishte_id: int,
        year: Optional[int] = None,
    ) -> Optional[dict]:
        """
        Extract a Chitalishte with its related InformationCards.

        Args:
            chitalishte_id: The Chitalishte ID
            year: Optional filter for InformationCards by year

        Returns:
            Dictionary containing Chitalishte data with related InformationCards,
            or None if not found
        """
        chitalishte = self.chitalishte_repo.get_by_id_with_cards(
            chitalishte_id, year=year
        )

        if not chitalishte:
            return None

        result = self._chitalishte_to_dict(chitalishte)
        result["information_cards"] = [
            self._information_card_to_dict(card) for card in chitalishte.information_cards
        ]

        return result

    def extract_all_chitalishte_with_cards(
        self,
        region: Optional[str] = None,
        town: Optional[str] = None,
        status: Optional[str] = None,
        year: Optional[int] = None,
        limit: Optional[int] = None,
        offset: int = 0,
    ) -> list[dict]:
        """
        Extract all Chitalishte records with their InformationCards.

        Args:
            region: Optional filter by region
            town: Optional filter by town
            status: Optional filter by status
            year: Optional filter by year (filters both Chitalishte and cards)
            limit: Optional limit on number of Chitalishte results
            offset: Number of Chitalishte results to skip

        Returns:
            List of dictionaries containing Chitalishte data with related InformationCards
        """
        chitalishte_list = self.chitalishte_repo.get_all(
            region=region,
            town=town,
            status=status,
            year=year,
            limit=limit,
            offset=offset,
        )

        results = []
        for chitalishte in chitalishte_list:
            # Load cards for each chitalishte
            chitalishte_with_cards = self.chitalishte_repo.get_by_id_with_cards(
                chitalishte.id, year=year
            )

            if chitalishte_with_cards:
                result = self._chitalishte_to_dict(chitalishte_with_cards)
                result["information_cards"] = [
                    self._information_card_to_dict(card)
                    for card in chitalishte_with_cards.information_cards
                ]
                results.append(result)

        return results

    def _chitalishte_to_dict(self, chitalishte) -> dict:
        """Convert Chitalishte model to dictionary."""
        return {
            "id": chitalishte.id,
            "registration_number": chitalishte.registration_number,
            "created_at": chitalishte.created_at.isoformat() if chitalishte.created_at else None,
            "address": chitalishte.address,
            "bulstat": chitalishte.bulstat,
            "chairman": chitalishte.chairman,
            "chitalishta_url": chitalishte.chitalishta_url,
            "email": chitalishte.email,
            "municipality": chitalishte.municipality,
            "name": chitalishte.name,
            "phone": chitalishte.phone,
            "region": chitalishte.region,
            "secretary": chitalishte.secretary,
            "status": chitalishte.status,
            "town": chitalishte.town,
            "url_to_libraries_site": chitalishte.url_to_libraries_site,
        }

    def _information_card_to_dict(self, card) -> dict:
        """Convert InformationCard model to dictionary."""
        return {
            "id": card.id,
            "chitalishte_id": card.chitalishte_id,
            "year": card.year,
            "created_at": card.created_at.isoformat() if card.created_at else None,
            "administrative_positions": card.administrative_positions,
            "amateur_arts": card.amateur_arts,
            "dancing_groups": card.dancing_groups,
            "disabilities_and_volunteers": card.disabilities_and_volunteers,
            "employees_count": card.employees_count,
            "employees_specialized": card.employees_specialized,
            "employees_with_higher_education": card.employees_with_higher_education,
            "folklore_formations": card.folklore_formations,
            "has_pc_and_internet_services": card.has_pc_and_internet_services,
            "kraeznanie_clubs": card.kraeznanie_clubs,
            "language_courses": card.language_courses,
            "library_activity": card.library_activity,
            "membership_applications": card.membership_applications,
            "modern_ballet": card.modern_ballet,
            "museum_collections": card.museum_collections,
            "new_members": card.new_members,
            "other_activities": card.other_activities,
            "other_clubs": card.other_clubs,
            "participation_in_events": card.participation_in_events,
            "participation_in_live_human_treasures_national": (
                card.participation_in_live_human_treasures_national
            ),
            "participation_in_live_human_treasures_regional": (
                card.participation_in_live_human_treasures_regional
            ),
            "participation_in_trainings": card.participation_in_trainings,
            "projects_participation_leading": card.projects_participation_leading,
            "projects_participation_partner": card.projects_participation_partner,
            "reg_number": card.reg_number,
            "registration_number": card.registration_number,
            "rejected_members": card.rejected_members,
            "subsidiary_count": card.subsidiary_count,
            "supporting_employees": card.supporting_employees,
            "theatre_formations": card.theatre_formations,
            "total_members_count": card.total_members_count,
            "town_population": card.town_population,
            "town_users": card.town_users,
            "vocal_groups": card.vocal_groups,
            "workshops_clubs_arts": card.workshops_clubs_arts,
            "bulstat": card.bulstat,
            "email": card.email,
            "kraeznanie_clubs_text": card.kraeznanie_clubs_text,
            "language_courses_text": card.language_courses_text,
            "museum_collections_text": card.museum_collections_text,
            "sanctions_for31and33": card.sanctions_for31and33,
            "url": card.url,
            "webpage": card.webpage,
            "workshops_clubs_arts_text": card.workshops_clubs_arts_text,
        }

