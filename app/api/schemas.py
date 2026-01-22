"""Pydantic schemas for API responses."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class ChitalishteYearDataResponse(BaseModel):
    """ChitalishteYearData response schema - comprehensive yearly data."""

    model_config = ConfigDict(from_attributes=True)

    reg_n: str
    year: int
    absolute_liquidity: Optional[float] = None
    accumulated_loss: Optional[float] = None
    accumulated_profit: Optional[float] = None
    administrative_positions: Optional[int] = None
    art_clubs: Optional[int] = None
    art_clubs_text: Optional[str] = None
    asset_profitability: Optional[float] = None
    assets_per_staff: Optional[float] = None
    average_annual_staff: Optional[float] = None
    borrowed_documents: Optional[int] = None
    cash: Optional[float] = None
    chairman: Optional[str] = None
    classical_dance_groups: Optional[int] = None
    collaborative_projects: Optional[int] = None
    computerized_workstations: Optional[int] = None
    computerized_workstations_alt: Optional[int] = None
    current_assets: Optional[float] = None
    dance_groups: Optional[int] = None
    debt_to_tangible_assets: Optional[float] = None
    disability_work: Optional[str] = None
    equity: Optional[float] = None
    equity_profitability: Optional[float] = None
    event_participations: Optional[int] = None
    external_services_spending: Optional[float] = None
    fast_liquidity: Optional[float] = None
    financial_autonomy: Optional[float] = None
    financial_debt: Optional[float] = None
    fixed_assets: Optional[float] = None
    folklore_groups: Optional[int] = None
    home_visits: Optional[int] = None
    immediate_liquidity: Optional[float] = None
    imposed_sanctions: Optional[int] = None
    income_per_staff: Optional[float] = None
    income_profitability: Optional[float] = None
    independent_projects: Optional[int] = None
    intangible_assets: Optional[float] = None
    international_projects: Optional[int] = None
    internet_access: Optional[int] = None
    investment: Optional[float] = None
    language_schools: Optional[int] = None
    language_schools_text: Optional[str] = None
    liabilities: Optional[float] = None
    liabilities_per_staff: Optional[float] = None
    library_activity: Optional[str] = None
    library_staff_higher_edu: Optional[int] = None
    library_staff_secondary_edu: Optional[int] = None
    library_staff_total: Optional[int] = None
    library_staff_training: Optional[int] = None
    library_units: Optional[int] = None
    library_users: Optional[int] = None
    library_users_online: Optional[int] = None
    local_history_clubs: Optional[int] = None
    local_history_clubs_text: Optional[str] = None
    long_term_liabilities: Optional[float] = None
    loss: Optional[float] = None
    material_reserves: Optional[float] = None
    membership_applications: Optional[int] = None
    museum_collections: Optional[int] = None
    museum_collections_text: Optional[str] = None
    national_projects: Optional[int] = None
    net_income: Optional[float] = None
    new_members: Optional[int] = None
    newly_acquired: Optional[int] = None
    newly_acquired_alt: Optional[int] = None
    operating_income: Optional[float] = None
    other_activities: Optional[str] = None
    other_clubs: Optional[int] = None
    phone_registry: Optional[str] = None
    profit: Optional[float] = None
    profit_per_staff: Optional[float] = None
    reading_room_visits: Optional[int] = None
    receivables: Optional[float] = None
    regional_projects: Optional[int] = None
    rejected_applications: Optional[int] = None
    secretary: Optional[str] = None
    short_term_liabilities: Optional[float] = None
    short_term_liquidity: Optional[float] = None
    specialized_positions: Optional[int] = None
    staff_count: Optional[int] = None
    staff_expenses: Optional[float] = None
    staff_higher_edu: Optional[int] = None
    status: Optional[str] = None
    subsidized_staff_count: Optional[int] = None
    support_staff: Optional[int] = None
    theater_groups: Optional[int] = None
    total_assets: Optional[float] = None
    total_expenditure: Optional[float] = None
    total_income: Optional[float] = None
    total_members: Optional[int] = None
    total_staff_registry: Optional[int] = None
    trade_price: Optional[float] = None
    training_participation: Optional[int] = None
    turnover_count: Optional[float] = None
    turnover_time: Optional[float] = None
    vocal_groups: Optional[int] = None
    chitalishte_id: str


class ChitalishtaResponse(BaseModel):
    """Chitalishta response schema."""

    model_config = ConfigDict(from_attributes=True)

    id: str  # UUID as string
    address: Optional[str] = None
    ekatte_code: Optional[str] = None
    empl_category: Optional[str] = None
    is_munip_center: Optional[str] = None
    mayorality_code: Optional[str] = None
    name: Optional[str] = None
    national_list: Optional[str] = None
    phone: Optional[str] = None
    reg_n: str
    regional_list: Optional[str] = None
    settlement_norm: Optional[str] = None
    slug: Optional[str] = None
    town: Optional[str] = None
    uic: Optional[str] = None
    village_city: Optional[str] = None
    municipality_id: str  # UUID as string
    ekatte: Optional[str] = None


class ChitalishtaWithYearDataResponse(ChitalishtaResponse):
    """Chitalishta response schema with related ChitalishteYearData."""

    chitalishte_year_data: list[ChitalishteYearDataResponse] = []


class ChitalishtaListResponse(BaseModel):
    """Response schema for list of Chitalishta."""

    items: list[ChitalishtaResponse]
    total: int
    limit: Optional[int] = None
    offset: int = 0


class ChitalishteYearDataListResponse(BaseModel):
    """Response schema for list of ChitalishteYearData."""

    items: list[ChitalishteYearDataResponse]
    total: int
    limit: Optional[int] = None
    offset: int = 0


class IngestionPreviewRequest(BaseModel):
    """Request schema for ingestion preview."""

    municipality_id: Optional[str] = None  # UUID as string
    town: Optional[str] = None
    status: Optional[str] = None
    year: Optional[int] = None
    limit: Optional[int] = 10


class DocumentMetadata(BaseModel):
    """Metadata schema for a document."""

    source: str
    # Database document fields
    chitalishta_id: Optional[str] = None  # UUID as string
    chitalishta_name: Optional[str] = None
    reg_n: Optional[str] = None
    municipality_id: Optional[str] = None  # UUID as string
    municipality_code: Optional[str] = None
    town: Optional[str] = None
    status: Optional[str] = None
    year: Optional[int] = None
    ekatte: Optional[str] = None
    counts: dict = {}
    # Analysis document fields
    document_type: Optional[str] = None
    document_name: Optional[str] = None
    author: Optional[str] = None
    document_date: Optional[str] = None
    language: Optional[str] = None
    scope: Optional[str] = None
    version: Optional[str] = None
    section_heading: Optional[str] = None
    section_index: Optional[int] = None
    chunk_index: Optional[int] = None


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


class AnalysisDocumentIngestionRequest(BaseModel):
    """Request schema for analysis document ingestion."""

    document_name: str


class AnalysisDocumentIngestionResponse(BaseModel):
    """Response schema for analysis document ingestion."""

    status: str
    message: str
    chunks_created: int
    chunks: list[DocumentPreview]
    statistics: dict
