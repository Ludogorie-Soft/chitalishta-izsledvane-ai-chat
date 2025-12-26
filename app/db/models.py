from datetime import datetime

from sqlalchemy import Boolean, DateTime, Double, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import INET, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base


class Chitalishte(Base):
    """Chitalishte (reading room/cultural center) model."""

    __tablename__ = "chitalishte"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    registration_number: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False)
    address: Mapped[str | None] = mapped_column(String(255), nullable=True)
    bulstat: Mapped[str | None] = mapped_column(String(255), nullable=True)
    chairman: Mapped[str | None] = mapped_column(String(255), nullable=True)
    chitalishta_url: Mapped[str | None] = mapped_column(String(255), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    municipality: Mapped[str | None] = mapped_column(String(255), nullable=True)
    name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(255), nullable=True)
    region: Mapped[str | None] = mapped_column(String(255), nullable=True)
    secretary: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[str | None] = mapped_column(String(255), nullable=True)
    town: Mapped[str | None] = mapped_column(String(255), nullable=True)
    url_to_libraries_site: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Relationship
    information_cards: Mapped[list["InformationCard"]] = relationship(
        "InformationCard", back_populates="chitalishte", cascade="all, delete-orphan"
    )


class InformationCard(Base):
    """Information card model - contains yearly data for a Chitalishte."""

    __tablename__ = "information_card"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    chitalishte_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("chitalishte.id"), nullable=False
    )
    year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False)

    # Numeric fields
    administrative_positions: Mapped[int | None] = mapped_column(Integer, nullable=True)
    amateur_arts: Mapped[int | None] = mapped_column(Integer, nullable=True)
    dancing_groups: Mapped[int | None] = mapped_column(Integer, nullable=True)
    disabilities_and_volunteers: Mapped[int | None] = mapped_column(Integer, nullable=True)
    employees_count: Mapped[float | None] = mapped_column(Double, nullable=True)
    employees_specialized: Mapped[int | None] = mapped_column(Integer, nullable=True)
    employees_with_higher_education: Mapped[int | None] = mapped_column(Integer, nullable=True)
    folklore_formations: Mapped[int | None] = mapped_column(Integer, nullable=True)
    kraeznanie_clubs: Mapped[int | None] = mapped_column(Integer, nullable=True)
    language_courses: Mapped[int | None] = mapped_column(Integer, nullable=True)
    library_activity: Mapped[int | None] = mapped_column(Integer, nullable=True)
    membership_applications: Mapped[int | None] = mapped_column(Integer, nullable=True)
    modern_ballet: Mapped[int | None] = mapped_column(Integer, nullable=True)
    museum_collections: Mapped[int | None] = mapped_column(Integer, nullable=True)
    new_members: Mapped[int | None] = mapped_column(Integer, nullable=True)
    other_activities: Mapped[int | None] = mapped_column(Integer, nullable=True)
    other_clubs: Mapped[int | None] = mapped_column(Integer, nullable=True)
    participation_in_events: Mapped[int | None] = mapped_column(Integer, nullable=True)
    participation_in_live_human_treasures_national: Mapped[int | None] = mapped_column(
        Integer, nullable=True
    )
    participation_in_live_human_treasures_regional: Mapped[int | None] = mapped_column(
        Integer, nullable=True
    )
    participation_in_trainings: Mapped[int | None] = mapped_column(Integer, nullable=True)
    projects_participation_leading: Mapped[int | None] = mapped_column(Integer, nullable=True)
    projects_participation_partner: Mapped[int | None] = mapped_column(Integer, nullable=True)
    reg_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    registration_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    rejected_members: Mapped[int | None] = mapped_column(Integer, nullable=True)
    subsidiary_count: Mapped[float | None] = mapped_column(Double, nullable=True)
    supporting_employees: Mapped[int | None] = mapped_column(Integer, nullable=True)
    theatre_formations: Mapped[int | None] = mapped_column(Integer, nullable=True)
    total_members_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    town_population: Mapped[int | None] = mapped_column(Integer, nullable=True)
    town_users: Mapped[int | None] = mapped_column(Integer, nullable=True)
    vocal_groups: Mapped[int | None] = mapped_column(Integer, nullable=True)
    workshops_clubs_arts: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Boolean fields
    has_pc_and_internet_services: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )

    # Text fields
    bulstat: Mapped[str | None] = mapped_column(String(255), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    kraeznanie_clubs_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    language_courses_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    museum_collections_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    sanctions_for31and33: Mapped[str | None] = mapped_column(String(255), nullable=True)
    url: Mapped[str | None] = mapped_column(String(255), nullable=True)
    webpage: Mapped[str | None] = mapped_column(String(255), nullable=True)
    workshops_clubs_arts_text: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationship
    chitalishte: Mapped["Chitalishte"] = relationship(
        "Chitalishte", back_populates="information_cards"
    )


class ChatLog(Base):
    """Chat log model - stores all POST /chat requests and responses for admin analysis."""

    __tablename__ = "chat_logs"

    # Primary identification
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    request_id: Mapped[str] = mapped_column(
        String(36), nullable=False, unique=True
    )  # UUID as string for compatibility
    conversation_id: Mapped[str] = mapped_column(
        String(36), nullable=False
    )  # UUID as string

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default="now()"
    )
    request_timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    # Request data
    user_message: Mapped[str] = mapped_column(Text, nullable=False)
    hallucination_mode: Mapped[str] = mapped_column(String(20), nullable=False)
    output_format: Mapped[str | None] = mapped_column(String(20), nullable=True)

    # Response data
    answer: Mapped[str | None] = mapped_column(Text, nullable=True)  # Nullable for failed requests
    intent: Mapped[str | None] = mapped_column(String(20), nullable=True)
    routing_confidence: Mapped[float | None] = mapped_column(Numeric(3, 2), nullable=True)

    # Execution flags
    sql_executed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    rag_executed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # SQL query (when executed)
    sql_query: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Performance metrics
    response_time_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Cost tracking (token usage totals)
    total_input_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    total_output_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    total_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # LLM operations (stored as JSONB array)
    # Format: [{"model": "gpt-4o-mini", "input_tokens": 100, "output_tokens": 50, "latency_ms": 500, "timestamp": "..."}, ...]
    llm_operations: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # Response metadata (routing_explanation, rag_metadata, etc.)
    response_metadata: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # Structured output (if requested)
    structured_output: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # Error information
    error_occurred: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    error_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    http_status_code: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Client information
    client_ip: Mapped[str | None] = mapped_column(String(45), nullable=True)  # IPv6 max length
    user_agent: Mapped[str | None] = mapped_column(Text, nullable=True)
