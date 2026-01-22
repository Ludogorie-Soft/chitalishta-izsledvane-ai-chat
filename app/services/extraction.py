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
        self.chitalishta_repo = ChitalishteRepository(db)
        self.year_data_repo = InformationCardRepository(db)

    def extract_chitalishta_data(
        self,
        municipality_id: Optional[str] = None,
        town: Optional[str] = None,
        status: Optional[str] = None,
        year: Optional[int] = None,
        limit: Optional[int] = None,
        offset: int = 0,
    ) -> list[dict]:
        """
        Extract Chitalishta data as dictionaries.

        Args:
            municipality_id: Optional filter by municipality ID (UUID)
            town: Optional filter by town
            status: Optional filter by status
            year: Optional filter by year (via ChitalishteYearData)
            limit: Optional limit on number of results
            offset: Number of results to skip

        Returns:
            List of dictionaries containing Chitalishta data
        """
        chitalishta_list = self.chitalishta_repo.get_all(
            municipality_id=municipality_id,
            town=town,
            status=status,
            year=year,
            limit=limit,
            offset=offset,
        )

        return [self._chitalishta_to_dict(ch) for ch in chitalishta_list]

    def extract_chitalishte_year_data(
        self,
        chitalishta_id: Optional[str] = None,
        year: Optional[int] = None,
        limit: Optional[int] = None,
        offset: int = 0,
    ) -> list[dict]:
        """
        Extract ChitalishteYearData as dictionaries.

        Args:
            chitalishta_id: Optional filter by Chitalishta ID (UUID)
            year: Optional filter by year
            limit: Optional limit on number of results
            offset: Number of results to skip

        Returns:
            List of dictionaries containing ChitalishteYearData
        """
        year_data_list = self.year_data_repo.get_all(
            chitalishta_id=chitalishta_id,
            year=year,
            limit=limit,
            offset=offset,
        )

        return [self._chitalishte_year_data_to_dict(yd) for yd in year_data_list]

    def extract_chitalishta_with_year_data(
        self,
        chitalishta_id: str,
        year: Optional[int] = None,
    ) -> Optional[dict]:
        """
        Extract a Chitalishta with its related ChitalishteYearData.

        Args:
            chitalishta_id: The Chitalishta ID (UUID)
            year: Optional filter for ChitalishteYearData by year

        Returns:
            Dictionary containing Chitalishta data with related ChitalishteYearData,
            or None if not found
        """
        chitalishta = self.chitalishta_repo.get_by_id_with_year_data(chitalishta_id, year=year)

        if not chitalishta:
            return None

        result = self._chitalishta_to_dict(chitalishta)
        result["chitalishte_year_data"] = [
            self._chitalishte_year_data_to_dict(yd) for yd in chitalishta.chitalishte_year_data
        ]

        return result

    def extract_all_chitalishta_with_year_data(
        self,
        municipality_id: Optional[str] = None,
        town: Optional[str] = None,
        status: Optional[str] = None,
        year: Optional[int] = None,
        limit: Optional[int] = None,
        offset: int = 0,
    ) -> list[dict]:
        """
        Extract all Chitalishta records with their ChitalishteYearData.

        Args:
            municipality_id: Optional filter by municipality ID (UUID)
            town: Optional filter by town
            status: Optional filter by status
            year: Optional filter by year (filters both Chitalishta and year data)
            limit: Optional limit on number of Chitalishta results
            offset: Number of Chitalishta results to skip

        Returns:
            List of dictionaries containing Chitalishta data with related ChitalishteYearData
        """
        chitalishta_list = self.chitalishta_repo.get_all(
            municipality_id=municipality_id,
            town=town,
            status=status,
            year=year,
            limit=limit,
            offset=offset,
        )

        results = []
        for chitalishta in chitalishta_list:
            # Load year data for each chitalishta
            chitalishta_with_year_data = self.chitalishta_repo.get_by_id_with_year_data(
                chitalishta.id, year=year
            )

            if chitalishta_with_year_data:
                result = self._chitalishta_to_dict(chitalishta_with_year_data)
                result["chitalishte_year_data"] = [
                    self._chitalishte_year_data_to_dict(yd)
                    for yd in chitalishta_with_year_data.chitalishte_year_data
                ]
                results.append(result)

        return results

    def _chitalishta_to_dict(self, chitalishta) -> dict:
        """Convert Chitalishta model to dictionary."""
        return {
            "id": chitalishta.id,
            "address": chitalishta.address,
            "ekatte_code": chitalishta.ekatte_code,
            "empl_category": chitalishta.empl_category,
            "is_munip_center": chitalishta.is_munip_center,
            "mayorality_code": chitalishta.mayorality_code,
            "name": chitalishta.name,
            "national_list": chitalishta.national_list,
            "phone": chitalishta.phone,
            "reg_n": chitalishta.reg_n,
            "regional_list": chitalishta.regional_list,
            "settlement_norm": chitalishta.settlement_norm,
            "slug": chitalishta.slug,
            "town": chitalishta.town,
            "uic": chitalishta.uic,
            "village_city": chitalishta.village_city,
            "municipality_id": chitalishta.municipality_id,
            "ekatte": chitalishta.ekatte,
        }

    def _chitalishte_year_data_to_dict(self, year_data) -> dict:
        """Convert ChitalishteYearData model to dictionary."""
        # Get all attributes from the model
        result = {
            "reg_n": year_data.reg_n,
            "year": year_data.year,
            "chitalishte_id": year_data.chitalishte_id,
        }

        # Add all other fields (there are many, so we'll use a more efficient approach)
        # Get all column names from the model
        for column in year_data.__table__.columns:
            if column.name not in ["reg_n", "year", "chitalishte_id"]:
                value = getattr(year_data, column.name, None)
                result[column.name] = value

        return result
