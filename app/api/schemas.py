"""Pydantic schemas for API responses."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class InformationCardResponse(BaseModel):
    """InformationCard response schema."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    chitalishte_id: int
    year: Optional[int] = None
    created_at: datetime
    administrative_positions: Optional[int] = None
    amateur_arts: Optional[int] = None
    dancing_groups: Optional[int] = None
    disabilities_and_volunteers: Optional[int] = None
    employees_count: Optional[float] = None
    employees_specialized: Optional[int] = None
    employees_with_higher_education: Optional[int] = None
    folklore_formations: Optional[int] = None
    has_pc_and_internet_services: bool
    kraeznanie_clubs: Optional[int] = None
    language_courses: Optional[int] = None
    library_activity: Optional[int] = None
    membership_applications: Optional[int] = None
    modern_ballet: Optional[int] = None
    museum_collections: Optional[int] = None
    new_members: Optional[int] = None
    other_activities: Optional[int] = None
    other_clubs: Optional[int] = None
    participation_in_events: Optional[int] = None
    participation_in_live_human_treasures_national: Optional[int] = None
    participation_in_live_human_treasures_regional: Optional[int] = None
    participation_in_trainings: Optional[int] = None
    projects_participation_leading: Optional[int] = None
    projects_participation_partner: Optional[int] = None
    reg_number: Optional[int] = None
    registration_number: Optional[int] = None
    rejected_members: Optional[int] = None
    subsidiary_count: Optional[float] = None
    supporting_employees: Optional[int] = None
    theatre_formations: Optional[int] = None
    total_members_count: Optional[int] = None
    town_population: Optional[int] = None
    town_users: Optional[int] = None
    vocal_groups: Optional[int] = None
    workshops_clubs_arts: Optional[int] = None
    bulstat: Optional[str] = None
    email: Optional[str] = None
    kraeznanie_clubs_text: Optional[str] = None
    language_courses_text: Optional[str] = None
    museum_collections_text: Optional[str] = None
    sanctions_for31and33: Optional[str] = None
    url: Optional[str] = None
    webpage: Optional[str] = None
    workshops_clubs_arts_text: Optional[str] = None


class ChitalishteResponse(BaseModel):
    """Chitalishte response schema."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    registration_number: int
    created_at: datetime
    address: Optional[str] = None
    bulstat: Optional[str] = None
    chairman: Optional[str] = None
    chitalishta_url: Optional[str] = None
    email: Optional[str] = None
    municipality: Optional[str] = None
    name: Optional[str] = None
    phone: Optional[str] = None
    region: Optional[str] = None
    secretary: Optional[str] = None
    status: Optional[str] = None
    town: Optional[str] = None
    url_to_libraries_site: Optional[str] = None


class ChitalishteWithCardsResponse(ChitalishteResponse):
    """Chitalishte response schema with related InformationCards."""

    information_cards: list[InformationCardResponse] = []


class ChitalishteListResponse(BaseModel):
    """Response schema for list of Chitalishte."""

    items: list[ChitalishteResponse]
    total: int
    limit: Optional[int] = None
    offset: int = 0


class InformationCardListResponse(BaseModel):
    """Response schema for list of InformationCards."""

    items: list[InformationCardResponse]
    total: int
    limit: Optional[int] = None
    offset: int = 0


class IngestionPreviewRequest(BaseModel):
    """Request schema for ingestion preview."""

    region: Optional[str] = None
    town: Optional[str] = None
    status: Optional[str] = None
    year: Optional[int] = None
    limit: Optional[int] = 10


class DocumentMetadata(BaseModel):
    """Metadata schema for a document."""

    source: str
    chitalishte_id: int
    chitalishte_name: Optional[str] = None
    registration_number: Optional[int] = None
    region: Optional[str] = None
    municipality: Optional[str] = None
    town: Optional[str] = None
    status: Optional[str] = None
    year: Optional[int] = None
    information_card_id: Optional[int] = None
    counts: dict = {}


class DocumentSizeInfo(BaseModel):
    """Size information schema for a document."""

    characters: int
    words: int
    estimated_tokens: int


class DocumentPreview(BaseModel):
    """Preview schema for a single document."""

    content: str
    metadata: DocumentMetadata
    size_info: DocumentSizeInfo
    is_valid: bool


class IngestionPreviewResponse(BaseModel):
    """Response schema for ingestion preview."""

    documents: list[DocumentPreview]
    statistics: dict
    total_available: Optional[int] = None

