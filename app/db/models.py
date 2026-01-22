from datetime import datetime

from sqlalchemy import Boolean, DateTime, Double, Float, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import INET, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base


class ChatLog(Base):
    """Chat log model - stores all POST /chat requests and responses for admin analysis."""

    __tablename__ = "chat_logs"

    # Primary identification
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    request_id: Mapped[str] = mapped_column(
        String(36), nullable=False, unique=True
    )  # UUID as string for compatibility
    conversation_id: Mapped[str] = mapped_column(String(36), nullable=False)  # UUID as string

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default="now()"
    )
    request_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    # Request data
    user_message: Mapped[str] = mapped_column(Text, nullable=False)
    hallucination_mode: Mapped[str] = mapped_column(String(20), nullable=False)
    output_format: Mapped[str | None] = mapped_column(String(20), nullable=True)

    # Response data
    answer: Mapped[str | None] = mapped_column(Text, nullable=True)  # Nullable for failed requests
    intent: Mapped[str | None] = mapped_column(String(20), nullable=True)
    routing_confidence: Mapped[float | None] = mapped_column(Numeric(3, 2), nullable=True)
    reply_certainty: Mapped[float | None] = mapped_column(Numeric(3, 2), nullable=True)

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

    # Cost and model tracking
    cost_usd: Mapped[float | None] = mapped_column(
        Numeric(10, 6), nullable=True
    )  # Cost in USD (up to $9999.999999)
    llm_model: Mapped[str | None] = mapped_column(
        String(100), nullable=True
    )  # Primary LLM model used

    # LLM operations (stored as JSONB array)
    # Format: [{"model": "gpt-4o-mini", "input_tokens": 100, "output_tokens": 50, "latency_ms": 500, "timestamp": "..."}, ...]
    llm_operations: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # Response metadata (routing_explanation, rag_metadata, certainty_breakdown, etc.)
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


class BaselineQuery(Base):
    """Baseline query model - stores known-good query-answer pairs for regression testing."""

    __tablename__ = "baseline_queries"

    # Primary key
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Query information
    query: Mapped[str] = mapped_column(Text, nullable=False)  # Bulgarian query text

    # Expected results
    expected_intent: Mapped[str] = mapped_column(String(20), nullable=False)  # sql/rag/hybrid
    expected_answer: Mapped[str | None] = mapped_column(
        Text, nullable=True
    )  # Expected answer text or pattern
    expected_sql_query: Mapped[str | None] = mapped_column(
        Text, nullable=True
    )  # Optional, if SQL is expected
    expected_rag_executed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    expected_sql_executed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # Flexible metadata (JSONB for additional expectations)
    # Can store: answer_patterns, semantic_similarity_threshold, etc.
    # Note: Named 'baseline_metadata' to avoid SQLAlchemy reserved 'metadata' attribute
    baseline_metadata: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default="now()"
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default="now()"
    )

    # Source tracking
    source: Mapped[str] = mapped_column(
        String(50), nullable=False, default="manual_test_query"
    )  # Source of baseline: 'manual_test_query' (manual test baselines) or 'real_user_query' (from real user queries)

    # Tracking
    created_by: Mapped[str | None] = mapped_column(
        String(100), nullable=True
    )  # Optional, for tracking who added the baseline

    # Management
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True
    )  # Enable/disable specific baselines


class User(Base):
    """User model - stores administrator and other user accounts."""

    __tablename__ = "users"

    # Primary key
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Authentication fields
    username: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True, unique=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)

    # Role-based access control
    role: Mapped[str] = mapped_column(
        String(50), nullable=False, default="administrator"
    )  # Initially only 'administrator', but extensible for future roles (e.g., 'moderator', 'viewer')

    # User status
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True
    )  # Enable/disable users

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default="now()"
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default="now()"
    )
    last_login: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )  # Optional timestamp for last login


class RateLimitState(Base):
    """Rate limit state model - tracks current rate limit counters per IP and session."""

    __tablename__ = "rate_limit_state"

    # Primary key
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Identification (can be IP address or session/conversation_id)
    identifier: Mapped[str] = mapped_column(
        String(255), nullable=False, index=True
    )  # IP address or conversation_id
    identifier_type: Mapped[str] = mapped_column(String(20), nullable=False)  # 'ip' or 'session'

    # Rate limit counters (sliding window approach)
    requests_minute: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    requests_hour: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    requests_day: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # Timestamps for sliding windows
    first_request_minute: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )  # First request in current minute window
    first_request_hour: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )  # First request in current hour window
    first_request_day: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )  # First request in current day window

    # Last request timestamp
    last_request_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default="now()"
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default="now()"
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default="now()"
    )


class RateLimitViolation(Base):
    """Rate limit violation model - logs all rate limit violations for analysis."""

    __tablename__ = "rate_limit_violations"

    # Primary key
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Identification
    identifier: Mapped[str] = mapped_column(
        String(255), nullable=False, index=True
    )  # IP address or conversation_id
    identifier_type: Mapped[str] = mapped_column(String(20), nullable=False)  # 'ip' or 'session'

    # Violation details
    violation_type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # 'rate_limit', 'abuse_dos', 'abuse_long_query', 'abuse_sql_injection', 'abuse_malformed'
    limit_exceeded: Mapped[str] = mapped_column(
        String(20), nullable=True
    )  # 'minute', 'hour', 'day' (for rate limit violations)

    # Request details
    endpoint: Mapped[str] = mapped_column(String(255), nullable=False)
    method: Mapped[str] = mapped_column(String(10), nullable=False)
    user_agent: Mapped[str | None] = mapped_column(Text, nullable=True)
    request_body_preview: Mapped[str | None] = mapped_column(
        Text, nullable=True
    )  # First 500 chars of request body for debugging

    # Additional context
    violation_details: Mapped[dict | None] = mapped_column(
        JSONB, nullable=True
    )  # Additional context (e.g., query length, request count, etc.)

    # Timestamp
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default="now()"
    )


class BlockedIP(Base):
    """Blocked IP model - tracks temporarily blocked IP addresses."""

    __tablename__ = "blocked_ips"

    # Primary key
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # IP address
    ip_address: Mapped[str] = mapped_column(
        String(45), nullable=False, unique=True, index=True
    )  # IPv6 max length

    # Block details
    blocked_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default="now()"
    )
    blocked_until: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )  # When the block expires
    block_reason: Mapped[str] = mapped_column(
        String(100), nullable=False
    )  # Reason for blocking (e.g., 'rate_limit_violation', 'abuse_dos', etc.)

    # Additional context
    violation_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=1
    )  # Number of violations that led to block
    block_details: Mapped[dict | None] = mapped_column(
        JSONB, nullable=True
    )  # Additional context about the block

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default="now()"
    )


class Municipality(Base):
    """Municipality model - stores municipality information."""

    __tablename__ = "municipalities"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True)
    district: Mapped[str | None] = mapped_column(String(100), nullable=True)
    district_code: Mapped[str | None] = mapped_column(String(10), nullable=True)
    migration_coefficient: Mapped[float | None] = mapped_column(Double, nullable=True)
    mrrb_category: Mapped[str | None] = mapped_column(String(100), nullable=True)
    municipality: Mapped[str | None] = mapped_column(String(100), nullable=True)
    municipality_code: Mapped[str] = mapped_column(String(10), nullable=False, unique=True)
    municipality_norm: Mapped[str | None] = mapped_column(String(100), nullable=True)
    nuts1: Mapped[str | None] = mapped_column(String(10), nullable=True)
    nuts2: Mapped[str | None] = mapped_column(String(10), nullable=True)
    nuts3: Mapped[str | None] = mapped_column(String(10), nullable=True)
    population_over_65_aggregate: Mapped[int | None] = mapped_column(Integer, nullable=True)
    population_under_15_aggregate: Mapped[int | None] = mapped_column(Integer, nullable=True)
    share_bulgarian: Mapped[float | None] = mapped_column(Double, nullable=True)
    share_others: Mapped[float | None] = mapped_column(Double, nullable=True)
    share_roma: Mapped[float | None] = mapped_column(Double, nullable=True)
    share_turkish: Mapped[float | None] = mapped_column(Double, nullable=True)
    total_chitalishta: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Relationships
    municipality_metrics: Mapped["MunicipalityMetric | None"] = relationship(
        "MunicipalityMetric", back_populates="municipality", uselist=False
    )
    municipality_year_data: Mapped[list["MunicipalityYearData"]] = relationship(
        "MunicipalityYearData", back_populates="municipality", cascade="all, delete-orphan"
    )
    settlements: Mapped[list["Settlement"]] = relationship(
        "Settlement", back_populates="municipality", cascade="all, delete-orphan"
    )


class MunicipalityMetric(Base):
    """Municipality metrics model - stores aggregated metrics for municipalities."""

    __tablename__ = "municipality_metrics"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True)
    additional_positions: Mapped[float | None] = mapped_column(Double, nullable=True)
    average_insurance_income: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    chitalishta_no_training_percent: Mapped[float | None] = mapped_column(
        Numeric(10, 2), nullable=True
    )
    chitalishta_per_10k_residents: Mapped[float | None] = mapped_column(
        Numeric(10, 1), nullable=True
    )
    chitalishta_per_1k_children_under_15: Mapped[float | None] = mapped_column(
        Numeric(10, 1), nullable=True
    )
    chitalishta_per_1k_elderly: Mapped[float | None] = mapped_column(Numeric(10, 1), nullable=True)
    chitalishta_per_1k_kindergarten: Mapped[float | None] = mapped_column(
        Numeric(10, 1), nullable=True
    )
    chitalishta_per_1k_students: Mapped[float | None] = mapped_column(Numeric(10, 1), nullable=True)
    city_chitalishta: Mapped[int | None] = mapped_column(Integer, nullable=True)
    expenses_for_salaries_percent: Mapped[float | None] = mapped_column(
        Numeric(10, 2), nullable=True
    )
    expenses_other_percent: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    revenue_from_other_percent: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    revenue_from_rent_percent: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    revenue_from_subsidies_percent: Mapped[float | None] = mapped_column(
        Numeric(10, 2), nullable=True
    )
    secretaries_count: Mapped[float | None] = mapped_column(Double, nullable=True)
    secretaries_higher_education_percent: Mapped[float | None] = mapped_column(
        Numeric(10, 2), nullable=True
    )
    staff_higher_education_percent: Mapped[float | None] = mapped_column(
        Numeric(10, 2), nullable=True
    )
    staff_secondary_education_percent: Mapped[float | None] = mapped_column(
        Numeric(10, 2), nullable=True
    )
    state_subsidy_amount: Mapped[float | None] = mapped_column(Numeric(15, 2), nullable=True)
    state_subsidy_per_capita: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    total_chitalishta: Mapped[int | None] = mapped_column(Integer, nullable=True)
    total_staff: Mapped[float | None] = mapped_column(Double, nullable=True)
    unique_employment_contracts: Mapped[int | None] = mapped_column(Integer, nullable=True)
    village_chitalishta: Mapped[int | None] = mapped_column(Integer, nullable=True)
    municipality_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("municipalities.id"), nullable=False, unique=True
    )

    # Relationship
    municipality: Mapped["Municipality"] = relationship(
        "Municipality", back_populates="municipality_metrics"
    )


class MunicipalityYearData(Base):
    """Municipality year data model - stores yearly data for municipalities."""

    __tablename__ = "municipality_year_data"

    municipality_code: Mapped[str] = mapped_column(String(10), primary_key=True)
    year: Mapped[int] = mapped_column(Integer, primary_key=True)
    additional_positions: Mapped[float | None] = mapped_column(Double, nullable=True)
    average_insurance_income: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    companies_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    companies_per_capita: Mapped[float | None] = mapped_column(Double, nullable=True)
    employment_rate: Mapped[float | None] = mapped_column(Double, nullable=True)
    expenses_salaries_thousands: Mapped[float | None] = mapped_column(Numeric(15, 2), nullable=True)
    expenses_social_security_thousands: Mapped[float | None] = mapped_column(
        Numeric(15, 2), nullable=True
    )
    gross_value_added_per_person: Mapped[float | None] = mapped_column(Double, nullable=True)
    gross_wage_monthly: Mapped[float | None] = mapped_column(Double, nullable=True)
    hospitals: Mapped[int | None] = mapped_column(Integer, nullable=True)
    kids_kindergartens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    municipality_population: Mapped[int | None] = mapped_column(Integer, nullable=True)
    poor_health: Mapped[float | None] = mapped_column(Double, nullable=True)
    revenue_from_rent_thousands: Mapped[float | None] = mapped_column(Numeric(15, 2), nullable=True)
    revenue_from_subsidies_thousands: Mapped[float | None] = mapped_column(
        Numeric(15, 2), nullable=True
    )
    secretaries_count: Mapped[float | None] = mapped_column(Double, nullable=True)
    secretaries_higher_education_count: Mapped[float | None] = mapped_column(Double, nullable=True)
    staff_higher_education_count: Mapped[float | None] = mapped_column(Double, nullable=True)
    staff_secondary_education_count: Mapped[float | None] = mapped_column(Double, nullable=True)
    students_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    students_per_1000: Mapped[float | None] = mapped_column(Double, nullable=True)
    subsidized_positions: Mapped[float | None] = mapped_column(Double, nullable=True)
    total_expenses_thousands: Mapped[float | None] = mapped_column(Numeric(15, 2), nullable=True)
    total_revenue_thousands: Mapped[float | None] = mapped_column(Numeric(15, 2), nullable=True)
    total_staff_count: Mapped[float | None] = mapped_column(Double, nullable=True)
    unemployment_rate: Mapped[float | None] = mapped_column(Double, nullable=True)
    unemployment_rate_15_29: Mapped[float | None] = mapped_column(Double, nullable=True)
    unique_employment_contracts: Mapped[int | None] = mapped_column(Integer, nullable=True)
    urban_population_percent: Mapped[float | None] = mapped_column(Double, nullable=True)
    municipality_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("municipalities.id"), nullable=False
    )

    # Relationship
    municipality: Mapped["Municipality"] = relationship(
        "Municipality", back_populates="municipality_year_data"
    )


class Settlement(Base):
    """Settlement model - stores settlement information."""

    __tablename__ = "settlements"

    ekatte: Mapped[str] = mapped_column(String(10), primary_key=True)
    elementary_education: Mapped[int | None] = mapped_column(Integer, nullable=True)
    higher_education: Mapped[int | None] = mapped_column(Integer, nullable=True)
    illiterate: Mapped[int | None] = mapped_column(Integer, nullable=True)
    literate: Mapped[int | None] = mapped_column(Integer, nullable=True)
    no_education: Mapped[int | None] = mapped_column(Integer, nullable=True)
    population_15_64: Mapped[int | None] = mapped_column(Integer, nullable=True)
    population_over_65: Mapped[int | None] = mapped_column(Integer, nullable=True)
    population_under_15: Mapped[int | None] = mapped_column(Integer, nullable=True)
    primary_education: Mapped[int | None] = mapped_column(Integer, nullable=True)
    secondary_education: Mapped[int | None] = mapped_column(Integer, nullable=True)
    settlement_norm: Mapped[str | None] = mapped_column(String(200), nullable=True)
    settlement_population: Mapped[int | None] = mapped_column(Integer, nullable=True)
    village_city: Mapped[str | None] = mapped_column(String(20), nullable=True)
    municipality_code: Mapped[str] = mapped_column(
        String(10), ForeignKey("municipalities.municipality_code"), nullable=False
    )

    # Relationship
    municipality: Mapped["Municipality"] = relationship(
        "Municipality", back_populates="settlements"
    )


class Chitalishta(Base):
    """Chitalishta model - new schema with UUID and municipality relationships."""

    __tablename__ = "chitalishta"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True)
    address: Mapped[str | None] = mapped_column(String(300), nullable=True)
    ekatte_code: Mapped[str | None] = mapped_column(String(10), nullable=True)
    empl_category: Mapped[str | None] = mapped_column(String(50), nullable=True)
    is_munip_center: Mapped[str | None] = mapped_column(String(10), nullable=True)
    mayorality_code: Mapped[str | None] = mapped_column(String(10), nullable=True)
    name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    national_list: Mapped[str | None] = mapped_column(String(500), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(300), nullable=True)
    reg_n: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    regional_list: Mapped[str | None] = mapped_column(String(500), nullable=True)
    settlement_norm: Mapped[str | None] = mapped_column(String(200), nullable=True)
    slug: Mapped[str | None] = mapped_column(String(255), nullable=True)
    town: Mapped[str | None] = mapped_column(String(200), nullable=True)
    uic: Mapped[str | None] = mapped_column(String(50), nullable=True)
    village_city: Mapped[str | None] = mapped_column(String(20), nullable=True)
    municipality_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("municipalities.id"), nullable=False
    )
    ekatte: Mapped[str | None] = mapped_column(
        String(10), ForeignKey("settlements.ekatte"), nullable=True
    )

    # Relationships
    municipality_rel: Mapped["Municipality"] = relationship("Municipality")
    settlement: Mapped["Settlement | None"] = relationship("Settlement")
    chitalishte_year_data: Mapped[list["ChitalishteYearData"]] = relationship(
        "ChitalishteYearData", back_populates="chitalishta", cascade="all, delete-orphan"
    )


class ChitalishteYearData(Base):
    """Chitalishte year data model - new schema with comprehensive yearly data."""

    __tablename__ = "chitalishte_year_data"

    reg_n: Mapped[str] = mapped_column(String(50), primary_key=True)
    year: Mapped[int] = mapped_column(Integer, primary_key=True)
    absolute_liquidity: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    accumulated_loss: Mapped[float | None] = mapped_column(Numeric(15, 2), nullable=True)
    accumulated_profit: Mapped[float | None] = mapped_column(Numeric(15, 2), nullable=True)
    administrative_positions: Mapped[int | None] = mapped_column(Integer, nullable=True)
    art_clubs: Mapped[int | None] = mapped_column(Integer, nullable=True)
    art_clubs_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    asset_profitability: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    assets_per_staff: Mapped[float | None] = mapped_column(Numeric(15, 2), nullable=True)
    average_annual_staff: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    borrowed_documents: Mapped[int | None] = mapped_column(Integer, nullable=True)
    cash: Mapped[float | None] = mapped_column(Numeric(15, 2), nullable=True)
    chairman: Mapped[str | None] = mapped_column(Text, nullable=True)
    classical_dance_groups: Mapped[int | None] = mapped_column(Integer, nullable=True)
    collaborative_projects: Mapped[int | None] = mapped_column(Integer, nullable=True)
    computerized_workstations: Mapped[int | None] = mapped_column(Integer, nullable=True)
    computerized_workstations_alt: Mapped[int | None] = mapped_column(Integer, nullable=True)
    current_assets: Mapped[float | None] = mapped_column(Numeric(15, 2), nullable=True)
    dance_groups: Mapped[int | None] = mapped_column(Integer, nullable=True)
    debt_to_tangible_assets: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    disability_work: Mapped[str | None] = mapped_column(Text, nullable=True)
    equity: Mapped[float | None] = mapped_column(Numeric(15, 2), nullable=True)
    equity_profitability: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    event_participations: Mapped[int | None] = mapped_column(Integer, nullable=True)
    external_services_spending: Mapped[float | None] = mapped_column(Numeric(15, 2), nullable=True)
    fast_liquidity: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    financial_autonomy: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    financial_debt: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    fixed_assets: Mapped[float | None] = mapped_column(Numeric(15, 2), nullable=True)
    folklore_groups: Mapped[int | None] = mapped_column(Integer, nullable=True)
    home_visits: Mapped[int | None] = mapped_column(Integer, nullable=True)
    immediate_liquidity: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    imposed_sanctions: Mapped[int | None] = mapped_column(Integer, nullable=True)
    income_per_staff: Mapped[float | None] = mapped_column(Numeric(15, 2), nullable=True)
    income_profitability: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    independent_projects: Mapped[int | None] = mapped_column(Integer, nullable=True)
    intangible_assets: Mapped[float | None] = mapped_column(Numeric(15, 2), nullable=True)
    international_projects: Mapped[int | None] = mapped_column(Integer, nullable=True)
    internet_access: Mapped[int | None] = mapped_column(Integer, nullable=True)
    investment: Mapped[float | None] = mapped_column(Numeric(15, 2), nullable=True)
    language_schools: Mapped[int | None] = mapped_column(Integer, nullable=True)
    language_schools_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    liabilities: Mapped[float | None] = mapped_column(Numeric(15, 2), nullable=True)
    liabilities_per_staff: Mapped[float | None] = mapped_column(Numeric(15, 2), nullable=True)
    library_activity: Mapped[str | None] = mapped_column(Text, nullable=True)
    library_staff_higher_edu: Mapped[int | None] = mapped_column(Integer, nullable=True)
    library_staff_secondary_edu: Mapped[int | None] = mapped_column(Integer, nullable=True)
    library_staff_total: Mapped[int | None] = mapped_column(Integer, nullable=True)
    library_staff_training: Mapped[int | None] = mapped_column(Integer, nullable=True)
    library_units: Mapped[int | None] = mapped_column(Integer, nullable=True)
    library_users: Mapped[int | None] = mapped_column(Integer, nullable=True)
    library_users_online: Mapped[int | None] = mapped_column(Integer, nullable=True)
    local_history_clubs: Mapped[int | None] = mapped_column(Integer, nullable=True)
    local_history_clubs_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    long_term_liabilities: Mapped[float | None] = mapped_column(Numeric(15, 2), nullable=True)
    loss: Mapped[float | None] = mapped_column(Numeric(15, 2), nullable=True)
    material_reserves: Mapped[float | None] = mapped_column(Numeric(15, 2), nullable=True)
    membership_applications: Mapped[int | None] = mapped_column(Integer, nullable=True)
    museum_collections: Mapped[int | None] = mapped_column(Integer, nullable=True)
    museum_collections_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    national_projects: Mapped[int | None] = mapped_column(Integer, nullable=True)
    net_income: Mapped[float | None] = mapped_column(Numeric(15, 2), nullable=True)
    new_members: Mapped[int | None] = mapped_column(Integer, nullable=True)
    newly_acquired: Mapped[int | None] = mapped_column(Integer, nullable=True)
    newly_acquired_alt: Mapped[int | None] = mapped_column(Integer, nullable=True)
    operating_income: Mapped[float | None] = mapped_column(Numeric(15, 2), nullable=True)
    other_activities: Mapped[str | None] = mapped_column(Text, nullable=True)
    other_clubs: Mapped[int | None] = mapped_column(Integer, nullable=True)
    phone_registry: Mapped[str | None] = mapped_column(Text, nullable=True)
    profit: Mapped[float | None] = mapped_column(Numeric(15, 2), nullable=True)
    profit_per_staff: Mapped[float | None] = mapped_column(Numeric(15, 2), nullable=True)
    reading_room_visits: Mapped[int | None] = mapped_column(Integer, nullable=True)
    receivables: Mapped[float | None] = mapped_column(Numeric(15, 2), nullable=True)
    regional_projects: Mapped[int | None] = mapped_column(Integer, nullable=True)
    rejected_applications: Mapped[int | None] = mapped_column(Integer, nullable=True)
    secretary: Mapped[str | None] = mapped_column(Text, nullable=True)
    short_term_liabilities: Mapped[float | None] = mapped_column(Numeric(15, 2), nullable=True)
    short_term_liquidity: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    specialized_positions: Mapped[int | None] = mapped_column(Integer, nullable=True)
    staff_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    staff_expenses: Mapped[float | None] = mapped_column(Numeric(15, 2), nullable=True)
    staff_higher_edu: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[str | None] = mapped_column(String(100), nullable=True)
    subsidized_staff_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    support_staff: Mapped[int | None] = mapped_column(Integer, nullable=True)
    theater_groups: Mapped[int | None] = mapped_column(Integer, nullable=True)
    total_assets: Mapped[float | None] = mapped_column(Numeric(15, 2), nullable=True)
    total_expenditure: Mapped[float | None] = mapped_column(Numeric(15, 2), nullable=True)
    total_income: Mapped[float | None] = mapped_column(Numeric(15, 2), nullable=True)
    total_members: Mapped[int | None] = mapped_column(Integer, nullable=True)
    total_staff_registry: Mapped[int | None] = mapped_column(Integer, nullable=True)
    trade_price: Mapped[float | None] = mapped_column(Numeric(15, 2), nullable=True)
    training_participation: Mapped[int | None] = mapped_column(Integer, nullable=True)
    turnover_count: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    turnover_time: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    vocal_groups: Mapped[int | None] = mapped_column(Integer, nullable=True)
    chitalishte_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("chitalishta.id"), nullable=False
    )

    # Relationship
    chitalishta: Mapped["Chitalishta"] = relationship(
        "Chitalishta", back_populates="chitalishte_year_data"
    )


class RagDebugLog(Base):
    """RAG debug log model - stores detailed RAG execution information for debugging."""

    __tablename__ = "rag_debug_logs"

    # Primary key
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Foreign key to chat_logs
    request_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("chat_logs.request_id"), nullable=False, unique=True, index=True
    )  # UUID as string, one debug log per request

    # Conversation tracking
    conversation_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)  # UUID as string

    # Request data
    user_query: Mapped[str] = mapped_column(Text, nullable=False)  # Original user question

    # Retrieved documents (JSONB - array with summaries)
    # Format: [{"content_summary": str (first 500 chars), "full_length": int, "metadata": dict, "source": str}, ...]
    retrieved_documents: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # Context and prompts
    formatted_context: Mapped[str | None] = mapped_column(Text, nullable=True)  # Full formatted context sent to LLM
    prompt_template_used: Mapped[str | None] = mapped_column(Text, nullable=True)  # Prompt template that was used
    llm_prompt_sent: Mapped[str | None] = mapped_column(Text, nullable=True)  # Actual prompt sent to LLM (with context)

    # Retrieval metadata (JSONB)
    retrieval_metadata: Mapped[dict | None] = mapped_column(JSONB, nullable=True)  # Retrieval scores, sources, etc.

    # Document counts
    db_doc_count: Mapped[int | None] = mapped_column(Integer, nullable=True)  # Number of DB documents
    analysis_doc_count: Mapped[int | None] = mapped_column(Integer, nullable=True)  # Number of analysis documents

    # Performance
    retrieval_duration_ms: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)  # Retrieval time

    # LLM response
    llm_response_received: Mapped[str | None] = mapped_column(Text, nullable=True)  # Raw LLM response before post-processing

    # Fallback usage
    fallback_llm_used: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)  # Whether fallback LLM was used

    # Timestamp
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default="now()", index=True
    )
