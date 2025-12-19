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

    def assemble_document(
        self, chitalishte_id: int, year: int
    ) -> Optional[dict]:
        """
        Assemble a single document for a Chitalishte and year.

        Args:
            chitalishte_id: The Chitalishte ID
            year: The year for the InformationCard

        Returns:
            Dictionary with 'content', 'metadata', and 'size_info', or None if not found
        """
        # Extract Chitalishte with card for specific year
        chitalishte_data = self.extraction_service.extract_chitalishte_with_cards(
            chitalishte_id, year=year
        )

        if not chitalishte_data:
            return None

        # Get the card for this year
        cards = chitalishte_data.get("information_cards", [])
        if not cards:
            return None

        # Transform to text
        chitalishte_text = self.transformation_service.transform_chitalishte_to_text(
            chitalishte_data
        )

        # Transform card to text
        card_text = self.transformation_service.transform_information_card_to_text(
            cards[0], chitalishte_name=chitalishte_data.get("name")
        )

        # Combine content
        content = f"{chitalishte_text}\n\n{card_text}"

        # Normalize text
        content = self.transformation_service.normalize_text(content)

        # Extract metadata
        metadata = self._extract_metadata(chitalishte_data, cards[0])

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
        region: Optional[str] = None,
        town: Optional[str] = None,
        status: Optional[str] = None,
        year: Optional[int] = None,
        limit: Optional[int] = None,
        offset: int = 0,
    ) -> list[dict]:
        """
        Assemble all documents (one per Chitalishte per year).

        Args:
            region: Optional filter by region
            town: Optional filter by town
            status: Optional filter by status
            year: Optional filter by year (if None, creates documents for all years)
            limit: Optional limit on number of Chitalishte records
            offset: Number of Chitalishte records to skip

        Returns:
            List of document dictionaries
        """
        documents = []

        # Get all Chitalishte records
        chitalishte_list = self.extraction_service.extract_chitalishte_data(
            region=region,
            town=town,
            status=status,
            year=year,  # This filters Chitalishte that have cards for this year
            limit=limit,
            offset=offset,
        )

        for chitalishte_data in chitalishte_list:
            chitalishte_id = chitalishte_data["id"]

            # If year is specified, create document for that year only
            if year is not None:
                doc = self.assemble_document(chitalishte_id, year)
                if doc:
                    documents.append(doc)
            else:
                # Create documents for all years this Chitalishte has cards
                chitalishte_with_all_cards = (
                    self.extraction_service.extract_chitalishte_with_cards(
                        chitalishte_id
                    )
                )

                if chitalishte_with_all_cards:
                    cards = chitalishte_with_all_cards.get("information_cards", [])
                    for card in cards:
                        card_year = card.get("year")
                        if card_year:
                            doc = self.assemble_document(chitalishte_id, card_year)
                            if doc:
                                documents.append(doc)

        return documents

    def _extract_metadata(self, chitalishte_data: dict, card_data: dict) -> dict:
        """
        Extract metadata from Chitalishte and InformationCard data.

        Args:
            chitalishte_data: Chitalishte data dictionary
            card_data: InformationCard data dictionary

        Returns:
            Metadata dictionary
        """
        metadata = {
            "source": "database",
            "chitalishte_id": chitalishte_data.get("id"),
            "chitalishte_name": chitalishte_data.get("name"),
            "registration_number": chitalishte_data.get("registration_number"),
            "region": chitalishte_data.get("region"),
            "municipality": chitalishte_data.get("municipality"),
            "town": chitalishte_data.get("town"),
            "status": chitalishte_data.get("status"),
            "year": card_data.get("year"),
            "information_card_id": card_data.get("id"),
        }

        # Add counts for filtering
        counts = {}
        if card_data.get("total_members_count") is not None:
            counts["total_members"] = int(card_data["total_members_count"])
        if card_data.get("employees_count") is not None:
            counts["employees"] = float(card_data["employees_count"])
        if card_data.get("subsidiary_count") is not None:
            counts["subsidiary_count"] = float(card_data["subsidiary_count"])
        if card_data.get("folklore_formations") is not None:
            counts["folklore_formations"] = int(card_data["folklore_formations"])
        if card_data.get("theatre_formations") is not None:
            counts["theatre_formations"] = int(card_data["theatre_formations"])
        if card_data.get("vocal_groups") is not None:
            counts["vocal_groups"] = int(card_data["vocal_groups"])
        if card_data.get("dancing_groups") is not None:
            counts["dancing_groups"] = int(card_data["dancing_groups"])

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

