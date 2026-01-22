"""Document assembly service - creates documents ready for embedding."""

from typing import Optional

from sqlalchemy.orm import Session

from app.services.extraction import DataExtractionService
from app.services.transformation import SemanticTransformationService


class DocumentAssemblyService:
    """Service for assembling documents from extracted and transformed data."""

    # Approximate tokens per character for Bulgarian text
    # Bulgarian text typically has ~3-4 characters per token
    CHARS_PER_TOKEN = 3.5

    # Maximum recommended tokens per document (for embedding)
    MAX_TOKENS = 8000  # Conservative limit for most embedding models

    def __init__(self, db: Session):
        """
        Initialize the document assembly service.

        Args:
            db: Database session
        """
        self.db = db
        self.extraction_service = DataExtractionService(db)
        self.transformation_service = SemanticTransformationService()

    def assemble_document(self, chitalishta_id: str, year: int) -> Optional[dict]:
        """
        Assemble a single document for a Chitalishta and year.

        Args:
            chitalishta_id: The Chitalishta ID (UUID)
            year: The year for the ChitalishteYearData

        Returns:
            Dictionary with 'content', 'metadata', and 'size_info', or None if not found
        """
        # Extract Chitalishta with year data for specific year
        chitalishta_data = self.extraction_service.extract_chitalishta_with_year_data(
            chitalishta_id, year=year
        )

        if not chitalishta_data:
            return None

        # Get the year data for this year
        year_data_list = chitalishta_data.get("chitalishte_year_data", [])
        if not year_data_list:
            return None

        # Transform to text
        chitalishta_text = self.transformation_service.transform_chitalishta_to_text(
            chitalishta_data
        )

        # Transform year data to text
        year_data_text = self.transformation_service.transform_chitalishte_year_data_to_text(
            year_data_list[0], chitalishta_name=chitalishta_data.get("name")
        )

        # Combine content
        content = f"{chitalishta_text}\n\n{year_data_text}"

        # Normalize text
        content = self.transformation_service.normalize_text(content)

        # Extract metadata
        metadata = self._extract_metadata(chitalishta_data, year_data_list[0])

        # Calculate size info
        size_info = self._calculate_size_info(content)

        # Validate size
        is_valid = self._validate_document_size(content)

        return {
            "content": content,
            "metadata": metadata,
            "size_info": size_info,
            "is_valid": is_valid,
        }

    def assemble_all_documents(
        self,
        municipality_id: Optional[str] = None,
        town: Optional[str] = None,
        status: Optional[str] = None,
        year: Optional[int] = None,
        limit: Optional[int] = None,
        offset: int = 0,
    ) -> list[dict]:
        """
        Assemble all documents (one per Chitalishta per year).

        Args:
            municipality_id: Optional filter by municipality ID (UUID)
            town: Optional filter by town
            status: Optional filter by status
            year: Optional filter by year (if None, creates documents for all years)
            limit: Optional limit on number of Chitalishta records
            offset: Number of Chitalishta records to skip

        Returns:
            List of document dictionaries
        """
        documents = []

        # Get all Chitalishta records
        chitalishta_list = self.extraction_service.extract_chitalishta_data(
            municipality_id=municipality_id,
            town=town,
            status=status,
            year=year,  # This filters Chitalishta that have year data for this year
            limit=limit,
            offset=offset,
        )

        for chitalishta_data in chitalishta_list:
            chitalishta_id = chitalishta_data["id"]

            # If year is specified, create document for that year only
            if year is not None:
                doc = self.assemble_document(chitalishta_id, year)
                if doc:
                    documents.append(doc)
            else:
                # Create documents for all years this Chitalishta has year data
                chitalishta_with_all_year_data = (
                    self.extraction_service.extract_chitalishta_with_year_data(chitalishta_id)
                )

                if chitalishta_with_all_year_data:
                    year_data_list = chitalishta_with_all_year_data.get("chitalishte_year_data", [])
                    for year_data in year_data_list:
                        year_data_year = year_data.get("year")
                        if year_data_year:
                            doc = self.assemble_document(chitalishta_id, year_data_year)
                            if doc:
                                documents.append(doc)

        return documents

    def _extract_metadata(self, chitalishta_data: dict, year_data: dict) -> dict:
        """
        Extract metadata from Chitalishta and ChitalishteYearData.

        Args:
            chitalishta_data: Chitalishta data dictionary
            year_data: ChitalishteYearData data dictionary

        Returns:
            Metadata dictionary
        """
        metadata = {
            "source": "database",
            "chitalishta_id": chitalishta_data.get("id"),
            "chitalishta_name": chitalishta_data.get("name"),
            "reg_n": chitalishta_data.get("reg_n"),
            "municipality_id": chitalishta_data.get("municipality_id"),
            "town": chitalishta_data.get("town"),
            "status": year_data.get("status"),  # Status is in year_data, not chitalishta
            "year": year_data.get("year"),
            "ekatte": chitalishta_data.get("ekatte"),
        }

        # Add counts for filtering
        counts = {}
        if year_data.get("total_members") is not None:
            counts["total_members"] = int(year_data["total_members"])
        if year_data.get("staff_count") is not None:
            counts["staff_count"] = int(year_data["staff_count"])
        if year_data.get("folklore_groups") is not None:
            counts["folklore_groups"] = int(year_data["folklore_groups"])
        if year_data.get("theater_groups") is not None:
            counts["theater_groups"] = int(year_data["theater_groups"])
        if year_data.get("vocal_groups") is not None:
            counts["vocal_groups"] = int(year_data["vocal_groups"])
        if year_data.get("dance_groups") is not None:
            counts["dance_groups"] = int(year_data["dance_groups"])

        metadata["counts"] = counts

        return metadata

    def _calculate_size_info(self, content: str) -> dict:
        """
        Calculate document size information.

        Args:
            content: Document content text

        Returns:
            Dictionary with size information
        """
        char_count = len(content)
        estimated_tokens = int(char_count / self.CHARS_PER_TOKEN)
        word_count = len(content.split())

        return {
            "characters": char_count,
            "words": word_count,
            "estimated_tokens": estimated_tokens,
        }

    def _validate_document_size(self, content: str) -> bool:
        """
        Validate that document size is within acceptable limits.

        Args:
            content: Document content text

        Returns:
            True if document size is valid, False otherwise
        """
        size_info = self._calculate_size_info(content)
        return size_info["estimated_tokens"] <= self.MAX_TOKENS

    def get_document_statistics(self, documents: list[dict]) -> dict:
        """
        Get statistics about a collection of documents.

        Args:
            documents: List of document dictionaries

        Returns:
            Statistics dictionary
        """
        if not documents:
            return {
                "total_documents": 0,
                "valid_documents": 0,
                "invalid_documents": 0,
                "average_size": 0,
                "min_size": 0,
                "max_size": 0,
            }

        sizes = [doc["size_info"]["estimated_tokens"] for doc in documents]
        valid_count = sum(1 for doc in documents if doc.get("is_valid", False))

        return {
            "total_documents": len(documents),
            "valid_documents": valid_count,
            "invalid_documents": len(documents) - valid_count,
            "average_size": int(sum(sizes) / len(sizes)) if sizes else 0,
            "min_size": min(sizes) if sizes else 0,
            "max_size": max(sizes) if sizes else 0,
        }
