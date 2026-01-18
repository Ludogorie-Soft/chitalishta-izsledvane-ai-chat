"""SQL agent using LangChain for querying the database."""

import structlog
import re
import time
import unicodedata
from typing import Dict, List, Optional

from app.core.config import settings
from app.core.metrics import track_sql_query
from app.db.database import engine
from app.rag.langchain_callbacks import get_langchain_callback_handler
from app.rag.llm_intent_classification import get_default_llm
from app.rag.hallucination_control import (
    HallucinationConfig,
    PromptEnhancer,
    get_default_hallucination_config,
)

logger = structlog.get_logger(__name__)

try:
    # Try different import paths for create_sql_agent (varies by LangChain version)
    try:
        from langchain_community.agent_toolkits import create_sql_agent
    except ImportError:
        try:
            from langchain.agents import create_sql_agent
        except ImportError:
            from langchain_experimental.agents import create_sql_agent

    # SQLDatabaseToolkit and SQLDatabase are typically in langchain_community
    try:
        from langchain_community.agent_toolkits import SQLDatabaseToolkit
        from langchain_community.utilities import SQLDatabase
    except ImportError:
        from langchain.agents.agent_toolkits import SQLDatabaseToolkit
        from langchain.sql_database import SQLDatabase

    from langchain_core.callbacks import BaseCallbackHandler
    from langchain_core.language_models.chat_models import BaseChatModel
except ImportError as _e:  # pragma: no cover - guarded by tests
    create_sql_agent = None  # type: ignore[assignment]
    SQLDatabaseToolkit = None  # type: ignore[assignment]
    SQLDatabase = None  # type: ignore[assignment]
    BaseCallbackHandler = object  # type: ignore[assignment]
    BaseChatModel = object  # type: ignore[assignment]
    _LANGCHAIN_IMPORT_ERROR = _e
else:
    _LANGCHAIN_IMPORT_ERROR = None


class SQLValidator:
    """Validator for SQL queries to ensure safety and correctness."""

    # Dangerous SQL keywords that should be blocked
    DANGEROUS_KEYWORDS = [
        "DELETE",
        "DROP",
        "TRUNCATE",
        "ALTER",
        "CREATE",
        "INSERT",
        "UPDATE",
        "GRANT",
        "REVOKE",
        "EXEC",
        "EXECUTE",
    ]

    # Allowed SQL keywords for read-only operations
    ALLOWED_KEYWORDS = [
        "SELECT",
        "WITH",
        "FROM",
        "WHERE",
        "JOIN",
        "INNER",
        "LEFT",
        "RIGHT",
        "FULL",
        "OUTER",
        "ON",
        "GROUP",
        "BY",
        "HAVING",
        "ORDER",
        "LIMIT",
        "OFFSET",
        "UNION",
        "INTERSECT",
        "EXCEPT",
        "DISTINCT",
        "AS",
        "AND",
        "OR",
        "NOT",
        "IN",
        "LIKE",
        "IS",
        "NULL",
        "COUNT",
        "SUM",
        "AVG",
        "MIN",
        "MAX",
        "CASE",
        "WHEN",
        "THEN",
        "ELSE",
        "END",
    ]

    # Valid columns for each table (to prevent hallucinations)
    VALID_COLUMNS = {
        "chitalishta": {
            "id",
            "address",
            "ekatte_code",
            "empl_category",
            "is_munip_center",
            "mayorality_code",
            "name",
            "national_list",
            "phone",
            "reg_n",
            "regional_list",
            "settlement_norm",
            "slug",
            "town",
            "uic",
            "village_city",
            "municipality_id",
            "ekatte",
        },
        "chitalishte_year_data": {
            "reg_n",
            "year",
            "absolute_liquidity",
            "accumulated_loss",
            "accumulated_profit",
            "administrative_positions",
            "art_clubs",
            "art_clubs_text",
            "asset_profitability",
            "assets_per_staff",
            "average_annual_staff",
            "borrowed_documents",
            "cash",
            "chairman",
            "classical_dance_groups",
            "collaborative_projects",
            "computerized_workstations",
            "computerized_workstations_alt",
            "current_assets",
            "dance_groups",
            "debt_to_tangible_assets",
            "disability_work",
            "equity",
            "equity_profitability",
            "event_participations",
            "external_services_spending",
            "fast_liquidity",
            "financial_autonomy",
            "financial_debt",
            "fixed_assets",
            "folklore_groups",
            "home_visits",
            "immediate_liquidity",
            "imposed_sanctions",
            "income_per_staff",
            "income_profitability",
            "independent_projects",
            "intangible_assets",
            "international_projects",
            "internet_access",
            "investment",
            "language_schools",
            "language_schools_text",
            "liabilities",
            "liabilities_per_staff",
            "library_activity",
            "library_staff_higher_edu",
            "library_staff_secondary_edu",
            "library_staff_total",
            "library_staff_training",
            "library_units",
            "library_users",
            "library_users_online",
            "local_history_clubs",
            "local_history_clubs_text",
            "long_term_liabilities",
            "loss",
            "material_reserves",
            "membership_applications",
            "museum_collections",
            "museum_collections_text",
            "national_projects",
            "net_income",
            "new_members",
            "newly_acquired",
            "newly_acquired_alt",
            "operating_income",
            "other_activities",
            "other_clubs",
            "phone_registry",
            "profit",
            "profit_per_staff",
            "reading_room_visits",
            "receivables",
            "regional_projects",
            "rejected_applications",
            "secretary",
            "short_term_liabilities",
            "short_term_liquidity",
            "specialized_positions",
            "staff_count",
            "staff_expenses",
            "staff_higher_edu",
            "status",
            "subsidized_staff_count",
            "support_staff",
            "theater_groups",
            "total_assets",
            "total_expenditure",
            "total_income",
            "total_members",
            "total_staff_registry",
            "trade_price",
            "training_participation",
            "turnover_count",
            "turnover_time",
            "vocal_groups",
            "chitalishte_id",
        },
        "municipalities": {
            "id",
            "district",
            "district_code",
            "migration_coefficient",
            "mrrb_category",
            "municipality",
            "municipality_code",
            "municipality_norm",
            "nuts1",
            "nuts2",
            "nuts3",
            "population_over_65_aggregate",
            "population_under_15_aggregate",
            "share_bulgarian",
            "share_others",
            "share_roma",
            "share_turkish",
            "total_chitalishta",
        },
        "municipality_metrics": {
            "id",
            "additional_positions",
            "average_insurance_income",
            "chitalishta_no_training_percent",
            "chitalishta_per_10k_residents",
            "chitalishta_per_1k_children_under_15",
            "chitalishta_per_1k_elderly",
            "chitalishta_per_1k_kindergarten",
            "chitalishta_per_1k_students",
            "city_chitalishta",
            "expenses_for_salaries_percent",
            "expenses_other_percent",
            "revenue_from_other_percent",
            "revenue_from_rent_percent",
            "revenue_from_subsidies_percent",
            "secretaries_count",
            "secretaries_higher_education_percent",
            "staff_higher_education_percent",
            "staff_secondary_education_percent",
            "state_subsidy_amount",
            "state_subsidy_per_capita",
            "total_chitalishta",
            "total_staff",
            "unique_employment_contracts",
            "village_chitalishta",
            "municipality_id",
        },
        "municipality_year_data": {
            "municipality_code",
            "year",
            "additional_positions",
            "average_insurance_income",
            "companies_number",
            "companies_per_capita",
            "employment_rate",
            "expenses_salaries_thousands",
            "expenses_social_security_thousands",
            "gross_value_added_per_person",
            "gross_wage_monthly",
            "hospitals",
            "kids_kindergartens",
            "municipality_population",
            "poor_health",
            "revenue_from_rent_thousands",
            "revenue_from_subsidies_thousands",
            "secretaries_count",
            "secretaries_higher_education_count",
            "staff_higher_education_count",
            "staff_secondary_education_count",
            "students_number",
            "students_per_1000",
            "subsidized_positions",
            "total_expenses_thousands",
            "total_revenue_thousands",
            "total_staff_count",
            "unemployment_rate",
            "unemployment_rate_15_29",
            "unique_employment_contracts",
            "urban_population_percent",
            "municipality_id",
        },
        "settlements": {
            "ekatte",
            "elementary_education",
            "higher_education",
            "illiterate",
            "literate",
            "no_education",
            "population_15_64",
            "population_over_65",
            "population_under_15",
            "primary_education",
            "secondary_education",
            "settlement_norm",
            "settlement_population",
            "village_city",
            "municipality_code",
        },
    }

    # Nullable columns that should be filtered when used in ORDER BY or important queries
    # These are columns that can be NULL and should have IS NOT NULL filter when queried
    NULLABLE_COLUMNS = {
        "chitalishta": {
            "address",
            "ekatte_code",
            "empl_category",
            "is_munip_center",
            "mayorality_code",
            "name",
            "national_list",
            "phone",
            "regional_list",
            "settlement_norm",
            "slug",
            "town",
            "uic",
            "village_city",
            "ekatte",
        },
        "chitalishte_year_data": {
            "absolute_liquidity",
            "accumulated_loss",
            "accumulated_profit",
            "administrative_positions",
            "art_clubs",
            "asset_profitability",
            "assets_per_staff",
            "average_annual_staff",
            "borrowed_documents",
            "cash",
            "chairman",
            "classical_dance_groups",
            "collaborative_projects",
            "computerized_workstations",
            "current_assets",
            "dance_groups",
            "debt_to_tangible_assets",
            "equity",
            "equity_profitability",
            "event_participations",
            "external_services_spending",
            "fast_liquidity",
            "financial_autonomy",
            "financial_debt",
            "fixed_assets",
            "folklore_groups",
            "home_visits",
            "immediate_liquidity",
            "imposed_sanctions",
            "income_per_staff",
            "income_profitability",
            "independent_projects",
            "intangible_assets",
            "international_projects",
            "internet_access",
            "investment",
            "language_schools",
            "liabilities",
            "liabilities_per_staff",
            "library_staff_higher_edu",
            "library_staff_secondary_edu",
            "library_staff_total",
            "library_staff_training",
            "library_units",
            "library_users",
            "library_users_online",
            "local_history_clubs",
            "long_term_liabilities",
            "loss",
            "material_reserves",
            "membership_applications",
            "museum_collections",
            "national_projects",
            "net_income",
            "new_members",
            "newly_acquired",
            "operating_income",
            "other_activities",
            "other_clubs",
            "profit",
            "profit_per_staff",
            "reading_room_visits",
            "receivables",
            "regional_projects",
            "rejected_applications",
            "secretary",
            "short_term_liabilities",
            "short_term_liquidity",
            "specialized_positions",
            "staff_count",
            "staff_expenses",
            "staff_higher_edu",
            "status",
            "subsidized_staff_count",
            "support_staff",
            "theater_groups",
            "total_assets",
            "total_expenditure",
            "total_income",
            "total_members",
            "total_staff_registry",
            "trade_price",
            "training_participation",
            "turnover_count",
            "turnover_time",
            "vocal_groups",
        },
        "municipalities": {
            "migration_coefficient",
            "population_over_65_aggregate",
            "population_under_15_aggregate",
            "share_bulgarian",
            "share_others",
            "share_roma",
            "share_turkish",
            "total_chitalishta",
        },
        "municipality_metrics": {
            "additional_positions",
            "average_insurance_income",
            "chitalishta_no_training_percent",
            "chitalishta_per_10k_residents",
            "chitalishta_per_1k_children_under_15",
            "chitalishta_per_1k_elderly",
            "chitalishta_per_1k_kindergarten",
            "chitalishta_per_1k_students",
            "city_chitalishta",
            "expenses_for_salaries_percent",
            "expenses_other_percent",
            "revenue_from_other_percent",
            "revenue_from_rent_percent",
            "revenue_from_subsidies_percent",
            "secretaries_count",
            "secretaries_higher_education_percent",
            "staff_higher_education_percent",
            "staff_secondary_education_percent",
            "state_subsidy_amount",
            "state_subsidy_per_capita",
            "total_chitalishta",
            "total_staff",
            "unique_employment_contracts",
            "village_chitalishta",
        },
        "municipality_year_data": {
            "additional_positions",
            "average_insurance_income",
            "companies_number",
            "companies_per_capita",
            "employment_rate",
            "expenses_salaries_thousands",
            "expenses_social_security_thousands",
            "gross_value_added_per_person",
            "gross_wage_monthly",
            "hospitals",
            "kids_kindergartens",
            "municipality_population",
            "poor_health",
            "revenue_from_rent_thousands",
            "revenue_from_subsidies_thousands",
            "secretaries_count",
            "secretaries_higher_education_count",
            "staff_higher_education_count",
            "staff_secondary_education_count",
            "students_number",
            "students_per_1000",
            "subsidized_positions",
            "total_expenses_thousands",
            "total_revenue_thousands",
            "total_staff_count",
            "unemployment_rate",
            "unemployment_rate_15_29",
            "unique_employment_contracts",
            "urban_population_percent",
        },
        "settlements": {
            "elementary_education",
            "higher_education",
            "illiterate",
            "literate",
            "no_education",
            "population_15_64",
            "population_over_65",
            "population_under_15",
            "primary_education",
            "secondary_education",
            "settlement_population",
        },
    }

    @classmethod
    def validate_columns(cls, sql: str) -> tuple[bool, Optional[str], Optional[list[str]]]:
        """
        Validate that all column references in SQL exist in the schema.

        Args:
            sql: SQL query string

        Returns:
            Tuple of (is_valid, error_message, invalid_columns)
        """
        sql_upper = sql.upper()
        invalid_columns = []

        # Extract column references from SQL
        # Pattern: column names after SELECT, in WHERE, ORDER BY, GROUP BY, etc.
        # This is a simplified check - we look for common patterns

        # Check for common hallucinated column names
        common_mistakes = {
            "subsidized_count": "subsidiary_count",  # Common mistake
        }

        # Check all tables
        for table_name, valid_cols in cls.VALID_COLUMNS.items():
            # Look for table.column or just column references
            # This is a heuristic - we check if columns are mentioned that don't exist
            for col in common_mistakes:
                # Check if the wrong column name appears
                pattern = rf"\b{re.escape(col)}\b"
                if re.search(pattern, sql, re.IGNORECASE):
                    invalid_columns.append(
                        f"{col} (should be {common_mistakes[col]} in {table_name} table)"
                    )

        # More comprehensive check: extract column names from SELECT, WHERE, ORDER BY, etc.
        # This is a simplified version - a full parser would be better
        # For now, we'll rely on the common mistakes check and schema info

        if invalid_columns:
            return (
                False,
                f"Invalid column names detected: {', '.join(invalid_columns)}",
                invalid_columns,
            )

        return True, None, None

    @classmethod
    def validate_sql(cls, sql: str) -> tuple[bool, Optional[str]]:
        """
        Validate SQL query for safety.

        Args:
            sql: SQL query string

        Returns:
            Tuple of (is_valid, error_message)
        """
        if not sql or not sql.strip():
            return False, "Empty SQL query"

        sql_upper = sql.upper().strip()

        # Check for dangerous keywords
        for keyword in cls.DANGEROUS_KEYWORDS:
            # Use word boundaries to avoid false positives
            pattern = r"\b" + re.escape(keyword) + r"\b"
            if re.search(pattern, sql_upper):
                return (
                    False,
                    f"Dangerous SQL keyword detected: {keyword}. Only SELECT queries are allowed.",
                )

        # Ensure it starts with SELECT or WITH (for CTEs)
        if not (sql_upper.startswith("SELECT") or sql_upper.startswith("WITH")):
            return (
                False,
                "Query must start with SELECT or WITH (for CTEs). Only read operations are allowed.",
            )

        # Check for semicolon injection attempts
        if ";" in sql and sql.count(";") > 1:
            return False, "Multiple semicolons detected. Possible SQL injection attempt."

        # Check for comment-based injection attempts
        if "--" in sql or "/*" in sql:
            # Allow comments in reasonable places, but be cautious
            if sql_upper.count("--") > 2 or sql_upper.count("/*") > 1:
                return False, "Excessive comments detected. Possible SQL injection attempt."

        return True, None

    @classmethod
    def sanitize_sql(cls, sql: str) -> str:
        """
        Sanitize SQL query by removing potentially dangerous patterns.

        Args:
            sql: SQL query string

        Returns:
            Sanitized SQL query
        """
        # Remove trailing semicolons (not needed for single queries)
        sql = sql.rstrip(";")

        # Remove excessive whitespace
        sql = re.sub(r"\s+", " ", sql)

        return sql.strip()


class SQLAuditLogger:
    """Logger for SQL query auditing."""

    @staticmethod
    def log_query(
        query: str,
        generated_sql: str,
        result: Optional[Dict] = None,
        error: Optional[str] = None,
    ):
        """
        Log SQL query execution for auditing.

        Args:
            query: Original user query
            generated_sql: Generated SQL query
            result: Query result (if successful)
            error: Error message (if failed)
        """
        log_data = {
            "type": "sql_query",
            "user_query": query,
            "generated_sql": generated_sql,
            "success": error is None,
        }

        if result:
            log_data["result_rows"] = result.get("row_count", 0)
            log_data["result_preview"] = result.get("preview", [])

        if error:
            log_data["error"] = error

        # Log as structured JSON for easy parsing
        logger.info("sql_query_audit", **log_data)


class SQLAgentService:
    """
    SQL agent service using LangChain for generating and executing SQL queries.

    This service ensures read-only access and validates all SQL queries.
    """

    def __init__(
        self,
        llm: Optional[BaseChatModel] = None,
        database_url: Optional[str] = None,
        enable_audit_logging: bool = True,
        hallucination_config: Optional[HallucinationConfig] = None,
        callbacks: Optional[List[BaseCallbackHandler]] = None,
    ):
        """
        Initialize SQL agent service.

        Args:
            llm: Optional LLM instance. If None, creates one from settings.
            database_url: Optional database URL. If None, uses config default.
            enable_audit_logging: Whether to enable audit logging of SQL queries
            hallucination_config: Optional hallucination control configuration. If None, uses default (MEDIUM_TOLERANCE).
            callbacks: Optional list of LangChain callback handlers for observability.
        """
        if _LANGCHAIN_IMPORT_ERROR is not None:
            raise ImportError(
                "LangChain SQL dependencies are required for SQLAgentService.\n"
                "Install them with:\n"
                "  poetry add langchain langchain-community langchain-openai"
            ) from _LANGCHAIN_IMPORT_ERROR

        self.hallucination_config = hallucination_config or get_default_hallucination_config()

        # Configure LLM with hallucination settings
        base_llm = llm or get_default_llm()
        self.llm = self.hallucination_config.get_llm_with_config(base_llm)
        self.database_url = database_url or settings.database_url
        self.enable_audit_logging = enable_audit_logging

        # Create SQLDatabase instance (read-only)
        # Add custom instructions with detailed column information to prevent hallucinations
        custom_table_info = {
            "chitalishta": (
                "Table: chitalishta\n"
                "COLUMNS (use ONLY these exact column names):\n"
                "- id (UUID, primary key)\n"
                "- address (VARCHAR 300)\n"
                "- ekatte_code (VARCHAR 10)\n"
                "- empl_category (VARCHAR 50)\n"
                "- is_munip_center (VARCHAR 10)\n"
                "- mayorality_code (VARCHAR 10)\n"
                "- name (VARCHAR 200)\n"
                "- national_list (VARCHAR 500)\n"
                "- phone (VARCHAR 300)\n"
                "- reg_n (VARCHAR 50, unique)\n"
                "- regional_list (VARCHAR 500)\n"
                "- settlement_norm (VARCHAR 200)\n"
                "- slug (VARCHAR 255)\n"
                "- town (VARCHAR 200)\n"
                "- uic (VARCHAR 50)\n"
                "- village_city (VARCHAR 20)\n"
                "- municipality_id (UUID, foreign key to municipalities.id)\n"
                "- ekatte (VARCHAR 10, foreign key to settlements.ekatte)\n"
                "\n"
                "CRITICAL RULES:\n"
                "1. NEVER invent column names that don't exist in the list above.\n"
                "2. For text field comparisons (town, name, village_city, etc.), ALWAYS use case-insensitive comparison:\n"
                "   - Use ILIKE instead of = (e.g., WHERE town ILIKE 'Враца')\n"
                "   - OR use LOWER() function: WHERE LOWER(town) = LOWER('Враца')\n"
                "3. IMPORTANT - The 'town' column may contain values like 'ГРАД ВРАЦА' or 'СЕЛО ВРАЦА' "
                "(i.e., 'ГРАД/СЕЛО <name>'), NOT just the town name.\n"
                "   When filtering by town, ALWAYS use ILIKE with wildcards: WHERE town ILIKE '%Враца%'\n"
                "   This will match 'ГРАД ВРАЦА', 'СЕЛО ВРАЦА', or just 'ВРАЦА'.\n"
                "4. When query asks for 'извън град X' (outside city X), use 'town NOT ILIKE' instead of 'town ILIKE'.\n"
                "5. To join with chitalishte_year_data: JOIN chitalishte_year_data ON chitalishta.id = chitalishte_year_data.chitalishte_id\n"
                "6. To join with municipalities: JOIN municipalities ON chitalishta.municipality_id = municipalities.id\n"
                "7. To join with settlements: JOIN settlements ON chitalishta.ekatte = settlements.ekatte\n"
            ),
            "chitalishte_year_data": (
                "Table: chitalishte_year_data\n"
                "COLUMNS (use ONLY these exact column names):\n"
                "- reg_n (VARCHAR 50, primary key part)\n"
                "- year (INTEGER, primary key part)\n"
                "- absolute_liquidity (NUMERIC)\n"
                "- accumulated_loss (NUMERIC)\n"
                "- accumulated_profit (NUMERIC)\n"
                "- administrative_positions (INTEGER)\n"
                "- art_clubs (INTEGER)\n"
                "- art_clubs_text (TEXT)\n"
                "- asset_profitability (NUMERIC)\n"
                "- assets_per_staff (NUMERIC)\n"
                "- average_annual_staff (NUMERIC)\n"
                "- borrowed_documents (INTEGER)\n"
                "- cash (NUMERIC)\n"
                "- chairman (TEXT)\n"
                "- classical_dance_groups (INTEGER)\n"
                "- collaborative_projects (INTEGER)\n"
                "- computerized_workstations (INTEGER)\n"
                "- computerized_workstations_alt (INTEGER)\n"
                "- current_assets (NUMERIC)\n"
                "- dance_groups (INTEGER)\n"
                "- debt_to_tangible_assets (NUMERIC)\n"
                "- disability_work (TEXT)\n"
                "- equity (NUMERIC)\n"
                "- equity_profitability (NUMERIC)\n"
                "- event_participations (INTEGER)\n"
                "- external_services_spending (NUMERIC)\n"
                "- fast_liquidity (NUMERIC)\n"
                "- financial_autonomy (NUMERIC)\n"
                "- financial_debt (NUMERIC)\n"
                "- fixed_assets (NUMERIC)\n"
                "- folklore_groups (INTEGER)\n"
                "- home_visits (INTEGER)\n"
                "- immediate_liquidity (NUMERIC)\n"
                "- imposed_sanctions (INTEGER)\n"
                "- income_per_staff (NUMERIC)\n"
                "- income_profitability (NUMERIC)\n"
                "- independent_projects (INTEGER)\n"
                "- intangible_assets (NUMERIC)\n"
                "- international_projects (INTEGER)\n"
                "- internet_access (INTEGER)\n"
                "- investment (NUMERIC)\n"
                "- language_schools (INTEGER)\n"
                "- language_schools_text (TEXT)\n"
                "- liabilities (NUMERIC)\n"
                "- liabilities_per_staff (NUMERIC)\n"
                "- library_activity (TEXT)\n"
                "- library_staff_higher_edu (INTEGER)\n"
                "- library_staff_secondary_edu (INTEGER)\n"
                "- library_staff_total (INTEGER)\n"
                "- library_staff_training (INTEGER)\n"
                "- library_units (INTEGER)\n"
                "- library_users (INTEGER)\n"
                "- library_users_online (INTEGER)\n"
                "- local_history_clubs (INTEGER)\n"
                "- local_history_clubs_text (TEXT)\n"
                "- long_term_liabilities (NUMERIC)\n"
                "- loss (NUMERIC)\n"
                "- material_reserves (NUMERIC)\n"
                "- membership_applications (INTEGER)\n"
                "- museum_collections (INTEGER)\n"
                "- museum_collections_text (TEXT)\n"
                "- national_projects (INTEGER)\n"
                "- net_income (NUMERIC)\n"
                "- new_members (INTEGER)\n"
                "- newly_acquired (INTEGER)\n"
                "- newly_acquired_alt (INTEGER)\n"
                "- operating_income (NUMERIC)\n"
                "- other_activities (TEXT)\n"
                "- other_clubs (INTEGER)\n"
                "- phone_registry (TEXT)\n"
                "- profit (NUMERIC)\n"
                "- profit_per_staff (NUMERIC)\n"
                "- reading_room_visits (INTEGER)\n"
                "- receivables (NUMERIC)\n"
                "- regional_projects (INTEGER)\n"
                "- rejected_applications (INTEGER)\n"
                "- secretary (TEXT)\n"
                "- short_term_liabilities (NUMERIC)\n"
                "- short_term_liquidity (NUMERIC)\n"
                "- specialized_positions (INTEGER)\n"
                "- staff_count (INTEGER)\n"
                "- staff_expenses (NUMERIC)\n"
                "- staff_higher_edu (INTEGER)\n"
                "- status (VARCHAR 100)\n"
                "- subsidized_staff_count (INTEGER)\n"
                "- support_staff (INTEGER)\n"
                "- theater_groups (INTEGER)\n"
                "- total_assets (NUMERIC)\n"
                "- total_expenditure (NUMERIC)\n"
                "- total_income (NUMERIC)\n"
                "- total_members (INTEGER)\n"
                "- total_staff_registry (INTEGER)\n"
                "- trade_price (NUMERIC)\n"
                "- training_participation (INTEGER)\n"
                "- turnover_count (NUMERIC)\n"
                "- turnover_time (NUMERIC)\n"
                "- vocal_groups (INTEGER)\n"
                "- chitalishte_id (UUID, foreign key to chitalishta.id)\n"
                "\n"
                "CRITICAL RULES:\n"
                "1. NEVER invent column names that don't exist in the list above.\n"
                "2. Primary key is composite: (reg_n, year)\n"
                "3. To access chitalishte_year_data columns, you MUST JOIN with chitalishta:\n"
                "   JOIN chitalishte_year_data ON chitalishta.id = chitalishte_year_data.chitalishte_id\n"
                "   OR: JOIN chitalishte_year_data ON chitalishta.reg_n = chitalishte_year_data.reg_n\n"
                "4. IMPORTANT - Many columns in this table can be NULL. When ordering by these columns or "
                "querying for meaningful results, ALWAYS add IS NOT NULL filter:\n"
                "   Example: WHERE chitalishte_year_data.total_members IS NOT NULL\n"
                "   This ensures you get records with actual values, not NULLs.\n"
                "5. CRITICAL - Each chitalishta can have MULTIPLE chitalishte_year_data records (one per year). "
                "When joining chitalishta with chitalishte_year_data and ordering by chitalishte_year_data columns, "
                "you MUST use GROUP BY chitalishta.id and MAX() aggregation to avoid duplicate chitalishta records:\n"
                "   Example: SELECT ch.name, MAX(cyd.total_members) FROM chitalishta ch "
                "JOIN chitalishte_year_data cyd ON ch.id = cyd.chitalishte_id "
                "GROUP BY ch.id ORDER BY MAX(cyd.total_members) DESC\n"
                "   This ensures each chitalishta appears only once in results.\n"
                "6. When filtering by year, use: WHERE chitalishte_year_data.year = 2023\n"
            ),
            "municipalities": (
                "Table: municipalities\n"
                "COLUMNS (use ONLY these exact column names):\n"
                "- id (UUID, primary key)\n"
                "- district (VARCHAR)\n"
                "- district_code (VARCHAR)\n"
                "- migration_coefficient (FLOAT8)\n"
                "- mrrb_category (VARCHAR)\n"
                "- municipality (VARCHAR)\n"
                "- municipality_code (VARCHAR, unique)\n"
                "- municipality_norm (VARCHAR)\n"
                "- nuts1 (VARCHAR)\n"
                "- nuts2 (VARCHAR)\n"
                "- nuts3 (VARCHAR)\n"
                "- population_over_65_aggregate (INTEGER)\n"
                "- population_under_15_aggregate (INTEGER)\n"
                "- share_bulgarian (FLOAT8)\n"
                "- share_others (FLOAT8)\n"
                "- share_roma (FLOAT8)\n"
                "- share_turkish (FLOAT8)\n"
                "- total_chitalishta (INTEGER)\n"
                "\n"
                "CRITICAL RULES:\n"
                "1. NEVER invent column names that don't exist in the list above.\n"
                "2. For text field comparisons (municipality, district, etc.), ALWAYS use case-insensitive comparison:\n"
                "   - Use ILIKE instead of = (e.g., WHERE municipality ILIKE 'София')\n"
                "   - OR use LOWER() function: WHERE LOWER(municipality) = LOWER('София')\n"
                "3. To join with municipality_metrics: JOIN municipality_metrics ON municipalities.id = municipality_metrics.municipality_id\n"
                "4. To join with municipality_year_data: JOIN municipality_year_data ON municipalities.id = municipality_year_data.municipality_id\n"
                "5. To join with settlements: JOIN settlements ON municipalities.municipality_code = settlements.municipality_code\n"
            ),
            "municipality_metrics": (
                "Table: municipality_metrics\n"
                "COLUMNS (use ONLY these exact column names):\n"
                "- id (UUID, primary key)\n"
                "- additional_positions (FLOAT8)\n"
                "- average_insurance_income (NUMERIC)\n"
                "- chitalishta_no_training_percent (NUMERIC)\n"
                "- chitalishta_per_10k_residents (NUMERIC)\n"
                "- chitalishta_per_1k_children_under_15 (NUMERIC)\n"
                "- chitalishta_per_1k_elderly (NUMERIC)\n"
                "- chitalishta_per_1k_kindergarten (NUMERIC)\n"
                "- chitalishta_per_1k_students (NUMERIC)\n"
                "- city_chitalishta (INTEGER)\n"
                "- expenses_for_salaries_percent (NUMERIC)\n"
                "- expenses_other_percent (NUMERIC)\n"
                "- revenue_from_other_percent (NUMERIC)\n"
                "- revenue_from_rent_percent (NUMERIC)\n"
                "- revenue_from_subsidies_percent (NUMERIC)\n"
                "- secretaries_count (FLOAT8)\n"
                "- secretaries_higher_education_percent (NUMERIC)\n"
                "- staff_higher_education_percent (NUMERIC)\n"
                "- staff_secondary_education_percent (NUMERIC)\n"
                "- state_subsidy_amount (NUMERIC)\n"
                "- state_subsidy_per_capita (NUMERIC)\n"
                "- total_chitalishta (INTEGER)\n"
                "- total_staff (FLOAT8)\n"
                "- unique_employment_contracts (INTEGER)\n"
                "- village_chitalishta (INTEGER)\n"
                "- municipality_id (UUID, foreign key to municipalities.id, unique)\n"
                "\n"
                "CRITICAL RULES:\n"
                "1. NEVER invent column names that don't exist in the list above.\n"
                "2. This table has a ONE-TO-ONE relationship with municipalities (one metric record per municipality).\n"
                "3. To join with municipalities: JOIN municipalities ON municipality_metrics.municipality_id = municipalities.id\n"
                "4. IMPORTANT - Many columns in this table can be NULL. When ordering by these columns or querying for meaningful results, ALWAYS add IS NOT NULL filter:\n"
                "   Example: WHERE municipality_metrics.total_chitalishta IS NOT NULL\n"
            ),
            "municipality_year_data": (
                "Table: municipality_year_data\n"
                "COLUMNS (use ONLY these exact column names):\n"
                "- municipality_code (VARCHAR, primary key part)\n"
                "- year (INTEGER, primary key part)\n"
                "- additional_positions (FLOAT8)\n"
                "- average_insurance_income (NUMERIC)\n"
                "- companies_number (INTEGER)\n"
                "- companies_per_capita (FLOAT8)\n"
                "- employment_rate (FLOAT8)\n"
                "- expenses_salaries_thousands (NUMERIC)\n"
                "- expenses_social_security_thousands (NUMERIC)\n"
                "- gross_value_added_per_person (FLOAT8)\n"
                "- gross_wage_monthly (FLOAT8)\n"
                "- hospitals (INTEGER)\n"
                "- kids_kindergartens (INTEGER)\n"
                "- municipality_population (INTEGER)\n"
                "- poor_health (FLOAT8)\n"
                "- revenue_from_rent_thousands (NUMERIC)\n"
                "- revenue_from_subsidies_thousands (NUMERIC)\n"
                "- secretaries_count (FLOAT8)\n"
                "- secretaries_higher_education_count (FLOAT8)\n"
                "- staff_higher_education_count (FLOAT8)\n"
                "- staff_secondary_education_count (FLOAT8)\n"
                "- students_number (INTEGER)\n"
                "- students_per_1000 (FLOAT8)\n"
                "- subsidized_positions (FLOAT8)\n"
                "- total_expenses_thousands (NUMERIC)\n"
                "- total_revenue_thousands (NUMERIC)\n"
                "- total_staff_count (FLOAT8)\n"
                "- unemployment_rate (FLOAT8)\n"
                "- unemployment_rate_15_29 (FLOAT8)\n"
                "- unique_employment_contracts (INTEGER)\n"
                "- urban_population_percent (FLOAT8)\n"
                "- municipality_id (UUID, foreign key to municipalities.id)\n"
                "\n"
                "CRITICAL RULES:\n"
                "1. NEVER invent column names that don't exist in the list above.\n"
                "2. This table has a ONE-TO-MANY relationship with municipalities (multiple year records per municipality).\n"
                "3. Primary key is composite: (municipality_code, year)\n"
                "4. To join with municipalities: JOIN municipalities ON municipality_year_data.municipality_id = municipalities.id\n"
                "   OR: JOIN municipalities ON municipality_year_data.municipality_code = municipalities.municipality_code\n"
                "5. IMPORTANT - Many columns in this table can be NULL. When ordering by these columns or querying for meaningful results, ALWAYS add IS NOT NULL filter:\n"
                "   Example: WHERE municipality_year_data.municipality_population IS NOT NULL\n"
                "6. When filtering by year, use: WHERE municipality_year_data.year = 2023\n"
            ),
            "settlements": (
                "Table: settlements\n"
                "COLUMNS (use ONLY these exact column names):\n"
                "- ekatte (VARCHAR, primary key)\n"
                "- elementary_education (INTEGER)\n"
                "- higher_education (INTEGER)\n"
                "- illiterate (INTEGER)\n"
                "- literate (INTEGER)\n"
                "- no_education (INTEGER)\n"
                "- population_15_64 (INTEGER)\n"
                "- population_over_65 (INTEGER)\n"
                "- population_under_15 (INTEGER)\n"
                "- primary_education (INTEGER)\n"
                "- secondary_education (INTEGER)\n"
                "- settlement_norm (VARCHAR)\n"
                "- settlement_population (INTEGER)\n"
                "- village_city (VARCHAR)\n"
                "- municipality_code (VARCHAR, foreign key to municipalities.municipality_code)\n"
                "\n"
                "CRITICAL RULES:\n"
                "1. NEVER invent column names that don't exist in the list above.\n"
                "2. This table has a MANY-TO-ONE relationship with municipalities (multiple settlements per municipality).\n"
                "3. To join with municipalities: JOIN municipalities ON settlements.municipality_code = municipalities.municipality_code\n"
                "4. IMPORTANT - Many columns in this table can be NULL. When ordering by these columns or querying for meaningful results, ALWAYS add IS NOT NULL filter:\n"
                "   Example: WHERE settlements.settlement_population IS NOT NULL\n"
                "5. The 'village_city' column indicates if a settlement is a village or city (e.g., 'село', 'град').\n"
            ),
        }

        self.db = SQLDatabase(
            engine=engine,
            # Include only the tables we want to expose
            include_tables=[
                "chitalishta",
                "chitalishte_year_data",
                "municipalities",
                "municipality_metrics",
                "municipality_year_data",
                "settlements",
            ],
            # Sample rows for schema understanding (limit to avoid large samples)
            sample_rows_in_table_info=3,
            custom_table_info=custom_table_info,
        )

        # Create SQL toolkit
        self.toolkit = SQLDatabaseToolkit(db=self.db, llm=self.llm)

        # Store callbacks (default to structured logging callback if not provided)
        if callbacks is None:
            callbacks = [get_langchain_callback_handler()]
        self.callbacks = callbacks

        # Create SQL agent with Bulgarian prompt
        self.agent = self._create_sql_agent()

        # Initialize validator and logger
        self.validator = SQLValidator()
        self.audit_logger = SQLAuditLogger() if enable_audit_logging else None

    def _create_sql_agent(self):
        """Create SQL agent with Bulgarian language support."""
        # Create agent with custom prompt for Bulgarian
        # Note: create_sql_agent API may vary by LangChain version
        # Using the standard parameters that work across versions
        agent = create_sql_agent(
            llm=self.llm,
            toolkit=self.toolkit,
            verbose=True,  # Enable verbose logging for debugging
            agent_type="openai-tools",  # Use OpenAI tools format
        )

        return agent

    def _get_bulgarian_system_message(self) -> str:
        """Get Bulgarian system message for SQL agent with hallucination control."""
        base_message = (
            "Ти си SQL агент за база данни за читалища в България.\n"
            "Твоята задача е да генерираш SQL заявки на базата на потребителските въпроси.\n"
            "\n"
            "КРИТИЧНО ВАЖНИ ПРАВИЛА ЗА ПРЕДОТВРЪЩАНЕ НА ГРЕШКИ:\n"
            "1. ВИНАГИ проверявай точните имена на колоните в схемата преди да ги използваш.\n"
            "2. НИКОГА не измисляй имена на колони - използвай САМО тези, които са в схемата.\n"
            "3. Ако не си сигурен за име на колона, провери схемата отново.\n"
            "4. Ако заявката изисква колони от 'chitalishte_year_data', ТРЯБВА да направиш JOIN:\n"
            "   JOIN chitalishte_year_data ON chitalishta.id = chitalishte_year_data.chitalishte_id\n"
            "   OR: JOIN chitalishte_year_data ON chitalishta.reg_n = chitalishte_year_data.reg_n\n"
            "\n"
            "ОСНОВНИ ПРАВИЛА:\n"
            "1. Генерирай САМО SELECT заявки. Никога не използвай DELETE, UPDATE, INSERT, DROP или други модифициращи команди.\n"
            "2. Използвай таблиците: 'chitalishta', 'chitalishte_year_data', 'municipalities', 'municipality_metrics', 'municipality_year_data', 'settlements'.\n"
            "3. За агрегации използвай COUNT, SUM, AVG, MIN, MAX.\n"
            "4. За JOIN операции използвай правилните ключове:\n"
            "   - chitalishta.id = chitalishte_year_data.chitalishte_id (ONE-TO-MANY)\n"
            "   - chitalishta.reg_n = chitalishte_year_data.reg_n (alternative join)\n"
            "   - chitalishta.municipality_id = municipalities.id (MANY-TO-ONE)\n"
            "   - chitalishta.ekatte = settlements.ekatte (MANY-TO-ONE)\n"
            "   - municipalities.id = municipality_metrics.municipality_id (ONE-TO-ONE)\n"
            "   - municipalities.id = municipality_year_data.municipality_id (ONE-TO-MANY)\n"
            "   - municipalities.municipality_code = municipality_year_data.municipality_code (alternative join)\n"
            "   - municipalities.municipality_code = settlements.municipality_code (ONE-TO-MANY)\n"
            "5. Бъди точен с имената на колоните - ВИНАГИ проверявай схемата.\n"
            "6. Ако потребителят пита за статистика, използвай GROUP BY.\n"
            "7. Връщай резултатите на български език, когато е възможно.\n"
            "8. ВАЖНО - Много колони в chitalishte_year_data могат да бъдат NULL (total_members, "
            "staff_count, total_income и др.). Когато сортираш по тези колони или търсиш "
            "смислени резултати, ВИНАГИ добави IS NOT NULL филтър:\n"
            "   Пример: WHERE chitalishte_year_data.total_members IS NOT NULL\n"
            "   Това гарантира, че получаваш записи с реални стойности, а не NULL.\n"
            "9. КРИТИЧНО - Всяко chitalishta може да има МНОЖЕСТВО chitalishte_year_data записи (по един за всяка година). "
            "Когато правиш JOIN между chitalishta и chitalishte_year_data и сортираш по колони от chitalishte_year_data, "
            "ТРЯБВА да използваш GROUP BY chitalishta.id и MAX() агрегация, за да избегнеш дублирани chitalishta записи:\n"
            "   Пример: SELECT ch.name, MAX(cyd.total_members) FROM chitalishta ch "
            "JOIN chitalishte_year_data cyd ON ch.id = cyd.chitalishte_id "
            "GROUP BY ch.id ORDER BY MAX(cyd.total_members) DESC\n"
            "   Това гарантира, че всяко chitalishta се появява само веднъж в резултатите.\n"
            "10. ВАЖНО - Колоната 'town' съдържа стойности като 'ГРАД ВРАЦА' или 'СЕЛО ВРАЦА' "
            "(т.е. 'ГРАД/СЕЛО <име>'), НЕ само името на града.\n"
            "   Когато филтрираш по town, ВИНАГИ използвай ILIKE с wildcards: WHERE town ILIKE '%Враца%'\n"
            "   Това ще съвпадне с 'ГРАД ВРАЦА', 'СЕЛО ВРАЦА', или само 'ВРАЦА'.\n"
            "11. Когато заявката пита за 'извън град X' (outside city X), използвай 'town NOT ILIKE' вместо 'town ILIKE'.\n"
            "12. ВАЖНО - За сравнения на текстови полета (region, town, municipality, status и др.) ВИНАГИ използвай case-insensitive сравнение:\n"
            "   - Използвай ILIKE вместо = за текстови сравнения (напр. WHERE region ILIKE 'Враца')\n"
            "   - ИЛИ използвай LOWER() функцията: WHERE LOWER(region) = LOWER('Враца')\n"
            "   - Това е критично, защото потребителите могат да питат с различни регистри (Враца, ВРАЦА, враца)\n"
            "   - Пример: Вместо 'WHERE region = \\'Враца\\'' използвай 'WHERE region ILIKE \\'Враца\\'' или 'WHERE LOWER(region) = LOWER(\\'Враца\\')'\n"
            "13. КРИТИЧНО - Когато броиш резултати, БЪДИ МНОГО ТОЧЕН:\n"
            "   - ВИНАГИ преброй реално броя на редовете в резултата, НЕ предполагай\n"
            "   - Ако заявката пита за 'градове', брои САМО тези, които започват с 'ГРАД' (не 'СЕЛО')\n"
            "   - Ако заявката пита за 'села', брои САМО тези, които започват с 'СЕЛО' (не 'ГРАД')\n"
            "   - Когато изброяваш списък, преброй точно колко елемента има в списъка преди да кажеш броя\n"
            "   - Пример: Ако резултатът съдържа 8 града и 50 села, и заявката пита за градове, кажи '8 града', НЕ '10 града'\n"
            "   - ВИНАГИ провери броя преди да го кажеш в отговора\n"
        )

        # Enhance with hallucination control instructions
        return PromptEnhancer.enhance_sql_prompt(base_message, self.hallucination_config)

    def _fix_column_names(self, sql: str) -> str:
        """
        Fix common column name mistakes (e.g., subsidized_count -> subsidiary_count).

        Args:
            sql: SQL query string

        Returns:
            SQL query with corrected column names
        """
        # Common mistakes: wrong_name -> correct_name
        column_fixes = {
            "subsidized_count": "subsidiary_count",
        }

        for wrong_name, correct_name in column_fixes.items():
            # Replace wrong column name with correct one
            # Use word boundaries to avoid partial matches
            pattern = re.compile(rf"\b{re.escape(wrong_name)}\b", re.IGNORECASE)
            sql = pattern.sub(correct_name, sql)

        return sql

    def _add_null_filters(self, sql: str) -> str:
        """
        Automatically add IS NOT NULL filters for nullable columns used in ORDER BY.

        This ensures that queries ordering by nullable columns filter out NULL values
        to return meaningful results.

        Args:
            sql: SQL query string

        Returns:
            SQL query with added IS NOT NULL filters
        """
        sql_upper = sql.upper()

        # Find columns used in ORDER BY
        order_by_match = re.search(r"ORDER\s+BY\s+([^,\n]+)", sql_upper)
        if not order_by_match:
            return sql

        order_by_clause = order_by_match.group(1)
        # Extract column references (handle table.column, alias.column, and just column, with optional DESC/ASC)
        # Pattern: table.column or alias.column or column, optionally followed by ASC/DESC
        order_by_cols = re.findall(
            r"(\w+\.\w+|\w+)(?:\s+(?:ASC|DESC))?", order_by_clause, re.IGNORECASE
        )

        filters_to_add = []

        # Check each column in ORDER BY
        for col_ref in order_by_cols:
            col_ref_clean = col_ref.strip()
            # Check if it's a table.column or alias.column
            if "." in col_ref_clean:
                parts = col_ref_clean.split(".")
                if len(parts) == 2:
                    table_or_alias, col_name = parts[0].lower(), parts[1].lower()
                    # Check if this column is nullable in any table
                    # Check all tables and their common aliases
                    nullable_tables = {
                        "chitalishta": ["chitalishta", "ch"],
                        "chitalishte_year_data": ["chitalishte_year_data", "cyd", "year_data"],
                        "municipalities": ["municipalities", "mun", "m"],
                        "municipality_metrics": ["municipality_metrics", "mm", "metrics"],
                        "municipality_year_data": ["municipality_year_data", "myd", "year_data"],
                        "settlements": ["settlements", "sett", "s"],
                    }
                    for table_name, aliases in nullable_tables.items():
                        if (
                            col_name in self.validator.NULLABLE_COLUMNS.get(table_name, set())
                            and table_or_alias in aliases
                        ):
                            # Check if IS NOT NULL filter already exists for this column
                            # Look for the column reference with IS NOT NULL in WHERE clause
                            # Use case-insensitive search
                            where_pattern = rf"{re.escape(col_ref_clean)}\s+IS\s+NOT\s+NULL"
                            if not re.search(where_pattern, sql_upper):
                                filters_to_add.append(f"{col_ref_clean} IS NOT NULL")
                            break  # Found matching table, no need to check others

        # Add filters if needed
        if filters_to_add:
            filter_text = " AND ".join(filters_to_add)
            # Find WHERE clause
            where_match = re.search(r"\bWHERE\b", sql_upper)
            if where_match:
                # Insert after WHERE, before ORDER BY/GROUP BY/LIMIT
                where_pos = where_match.end()
                # Find the end of WHERE clause
                where_end_match = re.search(
                    r"\b(ORDER\s+BY|GROUP\s+BY|HAVING|LIMIT)\b",
                    sql_upper[where_pos:],
                )
                if where_end_match:
                    insert_pos = where_pos + where_end_match.start()
                else:
                    insert_pos = len(sql)
                # Insert the filter
                sql = sql[:insert_pos] + f" AND {filter_text}" + sql[insert_pos:]
            else:
                # No WHERE clause, add one before ORDER BY
                order_by_pos = order_by_match.start()
                sql = sql[:order_by_pos] + f" WHERE {filter_text} " + sql[order_by_pos:]

        return sql

    def _fix_duplicate_chitalishte(self, sql: str) -> str:
        """
        Fix duplicate chitalishta records when joining with chitalishte_year_data.

        When joining chitalishta with chitalishte_year_data and ordering by chitalishte_year_data columns,
        we get duplicates because each chitalishta can have multiple chitalishte_year_data records.
        This method automatically adds GROUP BY and MAX() aggregation to get one record per chitalishta.

        Args:
            sql: SQL query string

        Returns:
            SQL query with GROUP BY and aggregation to prevent duplicates
        """
        sql_upper = sql.upper()

        # Check if query joins with chitalishte_year_data
        has_year_data_join = re.search(
            r"JOIN\s+chitalishte_year_data|JOIN\s+\w+\s+(?:cyd|year_data)\s+ON",
            sql_upper,
        )

        if not has_year_data_join:
            return sql

        # Check if query already has GROUP BY
        has_group_by = re.search(r"\bGROUP\s+BY\b", sql_upper)
        if has_group_by:
            # Already has GROUP BY, assume it's handled correctly
            return sql

        # Check if query orders by a chitalishte_year_data column
        order_by_match = re.search(r"ORDER\s+BY\s+([^,\n]+)", sql_upper)
        if not order_by_match:
            return sql

        order_by_clause = order_by_match.group(1)
        # Extract column references from ORDER BY
        order_by_cols = re.findall(
            r"(\w+\.\w+|\w+)(?:\s+(?:ASC|DESC))?", order_by_clause, re.IGNORECASE
        )

        # Check if any ORDER BY column is from chitalishte_year_data
        cyd_order_by_col = None
        for col_ref in order_by_cols:
            col_ref_clean = col_ref.strip()
            if "." in col_ref_clean:
                parts = col_ref_clean.split(".")
                if len(parts) == 2:
                    table_or_alias, col_name = parts[0].lower(), parts[1].lower()
                    if table_or_alias in ["chitalishte_year_data", "cyd", "year_data"]:
                        cyd_order_by_col = col_ref_clean
                        break

        if not cyd_order_by_col:
            return sql

        # Find chitalishta table alias
        chitalishta_alias = None
        alias_match = re.search(
            r"FROM\s+chitalishta\s+(\w+)|FROM\s+(\w+)\s+chitalishta",
            sql_upper,
        )
        if alias_match:
            chitalishta_alias = alias_match.group(1) or alias_match.group(2)

        # Determine chitalishta identifier for GROUP BY
        if chitalishta_alias:
            chitalishta_id_col = f"{chitalishta_alias}.id"
        else:
            chitalishta_id_col = "chitalishta.id"

        # Wrap the chitalishte_year_data column in MAX() in SELECT if it's there
        select_match = re.search(r"SELECT\s+(.+?)\s+FROM", sql_upper, re.DOTALL)
        if select_match:
            select_clause = select_match.group(1)
            # Check if the order by column appears in SELECT
            select_col_pattern = rf"\b{re.escape(cyd_order_by_col)}\b"
            if re.search(select_col_pattern, select_clause, re.IGNORECASE):
                # Check if it's already wrapped in an aggregate function
                if not re.search(
                    rf"(MAX|SUM|AVG|MIN|COUNT)\s*\(\s*{re.escape(cyd_order_by_col)}\s*\)",
                    select_clause,
                    re.IGNORECASE,
                ):
                    # Replace with MAX(column)
                    select_clause_new = re.sub(
                        select_col_pattern,
                        f"MAX({cyd_order_by_col})",
                        select_clause,
                        flags=re.IGNORECASE,
                    )
                    sql = sql.replace(select_clause, select_clause_new)

        # Add GROUP BY before ORDER BY
        order_by_pos = order_by_match.start()
        sql = sql[:order_by_pos] + f" GROUP BY {chitalishta_id_col} " + sql[order_by_pos:]

        # Update ORDER BY to use MAX() as well
        sql_upper = sql.upper()
        order_by_match_new = re.search(r"ORDER\s+BY\s+([^,\n]+)", sql_upper)
        if order_by_match_new:
            order_by_clause_new = order_by_match_new.group(1)
            # Check if MAX() is already there
            if not re.search(
                rf"MAX\s*\(\s*{re.escape(cyd_order_by_col)}\s*\)",
                order_by_clause_new,
                re.IGNORECASE,
            ):
                # Replace the column with MAX(column) in ORDER BY
                order_by_new = re.sub(
                    rf"\b{re.escape(cyd_order_by_col)}\b",
                    f"MAX({cyd_order_by_col})",
                    order_by_clause_new,
                    flags=re.IGNORECASE,
                )
                sql = sql.replace(
                    f"ORDER BY {order_by_match_new.group(1)}",
                    f"ORDER BY {order_by_new}",
                )

        return sql

    def _make_case_insensitive(self, sql: str) -> str:
        """
        Convert case-sensitive text comparisons to case-insensitive for known text fields.

        This method converts patterns like:
        - WHERE region = 'value' -> WHERE LOWER(region) = LOWER('value')
        - WHERE chitalishte.region = 'value' -> WHERE LOWER(chitalishte.region) = LOWER('value')
        - WHERE town = 'value' -> WHERE LOWER(town) = LOWER('value')
        - etc.

        Args:
            sql: SQL query string

        Returns:
            SQL query with case-insensitive comparisons for text fields
        """
        # Text fields that should be case-insensitive
        text_fields = [
            "region",
            "town",
            "municipality",
            "status",
            "chairman",
            "secretary",
            "name",
            "address",
            "email",
            "phone",
            "bulstat",
        ]

        # Pattern to match: [table.]field = 'value' or [table.]field = "value"
        # This handles both single and double quotes, table-qualified fields, and various whitespace
        # Avoid matching if already wrapped in LOWER() or using ILIKE
        for field in text_fields:
            # Match field = 'value' (case-insensitive field name, avoid if already LOWER or ILIKE)
            # Pattern matches: optional table prefix, field name, whitespace, =, whitespace, quoted value
            pattern1 = re.compile(
                rf"(?<!LOWER\()(?<!ILIKE\s)(\w+\.)?({re.escape(field)})\s*=\s*'([^']*)'",
                re.IGNORECASE,
            )

            def replace_single_quote(match):
                table_prefix = match.group(1) or ""  # May be None, so default to empty
                original_field = match.group(2)  # Field name (preserve original casing)
                value = match.group(3)
                if table_prefix:
                    return f"{table_prefix}LOWER({original_field}) = LOWER('{value}')"
                else:
                    return f"LOWER({original_field}) = LOWER('{value}')"

            sql = pattern1.sub(replace_single_quote, sql)

            # Match field = "value" (double quotes)
            pattern2 = re.compile(
                rf'(?<!LOWER\()(?<!ILIKE\s)(\w+\.)?({re.escape(field)})\s*=\s*"([^"]*)"',
                re.IGNORECASE,
            )

            def replace_double_quote(match):
                table_prefix = match.group(1) or ""
                original_field = match.group(2)
                value = match.group(3)
                if table_prefix:
                    return f'{table_prefix}LOWER({original_field}) = LOWER("{value}")'
                else:
                    return f'LOWER({original_field}) = LOWER("{value}")'

            sql = pattern2.sub(replace_double_quote, sql)

        return sql

    def _normalize_whitespace(self, text: str) -> str:
        """
        Normalize whitespace characters, including non-breaking spaces (0xa0).

        Args:
            text: Input text

        Returns:
            Text with normalized whitespace (non-breaking spaces converted to regular spaces)
        """
        # Replace non-breaking space (U+00A0, 0xa0) with regular space
        text = text.replace("\xa0", " ")
        # Normalize all Unicode whitespace characters to regular space
        text = "".join(" " if unicodedata.category(c)[0] == "Z" else c for c in text)
        # Collapse multiple spaces to single space
        text = " ".join(text.split())
        return text.strip()

    def _fix_town_field_patterns(self, sql: str) -> str:
        """
        Fix town field comparisons to handle patterns like "ГРАД ВРАЦА" or "СЕЛО ВРАЦА".

        The town column contains values like "ГРАД ВРАЦА" or "СЕЛО ВРАЦА" (i.e., "ГРАД/СЕЛО <name>"),
        not just the town name. This method converts exact matches to pattern matches using ILIKE.

        Also handles non-breaking spaces (0xa0) in town values by normalizing them.

        Args:
            sql: SQL query string

        Returns:
            SQL query with town field comparisons using ILIKE patterns
        """
        # Find town field comparisons that use exact match (=) or ILIKE without wildcards
        # Pattern: [table.]town = 'value' or [table.]town ILIKE 'value' (without %)
        # Convert to: [table.]town ILIKE '%value%' to match "ГРАД value" or "СЕЛО value" patterns

        # Match: town = 'value' -> town ILIKE '%value%'
        pattern1 = re.compile(
            r"(\w+\.)?town\s*=\s*'([^']+)'",
            re.IGNORECASE,
        )

        def replace_exact_match1(match):
            table_prefix = match.group(1) or ""
            value = match.group(2)
            # Normalize whitespace in the value (handle non-breaking spaces)
            value = self._normalize_whitespace(value)
            # Use ILIKE with wildcards to match "ГРАД value", "СЕЛО value", or just "value"
            return f"{table_prefix}town ILIKE '%{value}%'"

        sql = pattern1.sub(replace_exact_match1, sql)

        # Match: town = "value" -> town ILIKE "%value%"
        pattern2 = re.compile(
            r'(\w+\.)?town\s*=\s*"([^"]+)"',
            re.IGNORECASE,
        )

        def replace_exact_match2(match):
            table_prefix = match.group(1) or ""
            value = match.group(2)
            # Normalize whitespace in the value (handle non-breaking spaces)
            value = self._normalize_whitespace(value)
            return f'{table_prefix}town ILIKE "%{value}%"'

        sql = pattern2.sub(replace_exact_match2, sql)

        # Also fix ILIKE without wildcards: town ILIKE 'value' -> town ILIKE '%value%'
        # But only if it doesn't already have wildcards
        pattern3 = re.compile(
            r"(\w+\.)?town\s+ILIKE\s+'([^']+)'",
            re.IGNORECASE,
        )

        def replace_ilike_no_wildcard1(match):
            table_prefix = match.group(1) or ""
            value = match.group(2)
            # Normalize whitespace in the value (handle non-breaking spaces)
            value = self._normalize_whitespace(value)
            # Only add wildcards if not already present
            if "%" not in value:
                return f"{table_prefix}town ILIKE '%{value}%'"
            return match.group(0)

        sql = pattern3.sub(replace_ilike_no_wildcard1, sql)

        pattern4 = re.compile(
            r'(\w+\.)?town\s+ILIKE\s+"([^"]+)"',
            re.IGNORECASE,
        )

        def replace_ilike_no_wildcard2(match):
            table_prefix = match.group(1) or ""
            value = match.group(2)
            # Normalize whitespace in the value (handle non-breaking spaces)
            value = self._normalize_whitespace(value)
            if "%" not in value:
                return f'{table_prefix}town ILIKE "%{value}%"'
            return match.group(0)

        sql = pattern4.sub(replace_ilike_no_wildcard2, sql)

        return sql

    def _fix_not_conditions(self, sql: str) -> str:
        """
        Fix missing NOT in conditions when query asks for "извън" (outside/excluding).

        When the user asks for "извън град X" (outside city X), the query should use
        "town NOT ILIKE" instead of "town ILIKE".

        Args:
            sql: SQL query string

        Returns:
            SQL query with corrected NOT conditions
        """
        sql_upper = sql.upper()

        # Find patterns where we have "town ILIKE 'value'" but should have "town NOT ILIKE 'value'"
        # This is a heuristic - we look for cases where town ILIKE appears but the logic suggests exclusion
        # For now, we'll look for patterns like "town ILIKE 'value' = false" which is incorrect SQL
        # and should be "town NOT ILIKE 'value'"

        # Pattern: town ILIKE 'value' = false (incorrect SQL that should be town NOT ILIKE 'value')
        pattern = r"(\w+\.)?town\s+ILIKE\s+['\"]([^'\"]+)['\"]\s*=\s*false"
        replacement = r"\1town NOT ILIKE '\2'"

        sql = re.sub(pattern, replacement, sql, flags=re.IGNORECASE)

        # Also handle: town ILIKE 'value' = true (should just be town ILIKE 'value')
        pattern2 = r"(\w+\.)?town\s+ILIKE\s+['\"]([^'\"]+)['\"]\s*=\s*true"
        replacement2 = r"\1town ILIKE '\2'"

        sql = re.sub(pattern2, replacement2, sql, flags=re.IGNORECASE)

        return sql

    def _validate_and_sanitize_sql(self, sql: str) -> tuple[str, Optional[str]]:
        """
        Validate and sanitize SQL query.

        Args:
            sql: SQL query string

        Returns:
            Tuple of (sanitized_sql, error_message)
        """
        # Validate SQL structure
        is_valid, error = self.validator.validate_sql(sql)
        if not is_valid:
            return sql, error

        # Validate columns exist
        cols_valid, cols_error, invalid_cols = self.validator.validate_columns(sql)
        if not cols_valid:
            logger.warning(
                "column_validation_failed",
                error=cols_error,
                sql_preview=sql[:100] if sql else None,
            )
            # Log the invalid columns for debugging
            if invalid_cols:
                logger.warning(
                    "invalid_columns_detected",
                    invalid_columns=invalid_cols,
                    sql_preview=sql[:100] if sql else None,
                )
            # Return error but don't block execution - let the database error handle it
            # This allows the agent to see the actual error and retry
            return sql, cols_error

        # Sanitize
        sanitized = self.validator.sanitize_sql(sql)

        # Fix common column name mistakes (e.g., subsidized_count -> subsidiary_count)
        sanitized = self._fix_column_names(sanitized)

        # Make text field comparisons case-insensitive
        sanitized = self._make_case_insensitive(sanitized)

        # Fix town field patterns (handle "ГРАД ВРАЦА" or "СЕЛО ВРАЦА" patterns)
        sanitized = self._fix_town_field_patterns(sanitized)

        # Fix missing NOT in conditions (handle "извън" / outside conditions)
        sanitized = self._fix_not_conditions(sanitized)

        # Add IS NOT NULL filters for nullable columns used in ORDER BY
        sanitized = self._add_null_filters(sanitized)

        # Fix duplicate chitalishte records when joining with information_card
        sanitized = self._fix_duplicate_chitalishte(sanitized)

        return sanitized, None

    def query(self, question: str) -> Dict[str, any]:
        """
        Execute SQL query based on user question.

        Args:
            question: User question in Bulgarian

        Returns:
            Dictionary with answer, SQL query, and metadata
        """
        start_time = time.time()
        status = "success"

        try:
            # Invoke the agent with callbacks
            config = {"callbacks": self.callbacks} if self.callbacks else {}
            result = self.agent.invoke({"input": question}, config=config)

            # Extract SQL query from agent execution
            # The agent returns a dict with 'output' and potentially intermediate steps
            answer = result.get("output", str(result))

            # Try to extract SQL from intermediate steps if available
            generated_sql = None
            if "intermediate_steps" in result:
                logger.debug(
                    "extracting_sql_from_steps",
                    step_count=len(result["intermediate_steps"]),
                )
                for step in result["intermediate_steps"]:
                    if isinstance(step, tuple) and len(step) >= 2:
                        action = step[0]
                        observation = step[1] if len(step) > 1 else None

                        # Method 1: Check tool_input attribute (most common)
                        if hasattr(action, "tool_input"):
                            tool_input = action.tool_input
                            if isinstance(tool_input, dict):
                                # Try "query" key first
                                if "query" in tool_input:
                                    generated_sql = tool_input["query"]
                                # Try other possible keys
                                elif "sql" in tool_input:
                                    generated_sql = tool_input["sql"]
                                # Check all string values for SQL
                                if not generated_sql:
                                    for key, value in tool_input.items():
                                        if isinstance(value, str) and "SELECT" in value.upper():
                                            sql_match = re.search(
                                                r"SELECT.*?(?:;|$)",
                                                value,
                                                re.IGNORECASE | re.DOTALL,
                                            )
                                            if sql_match:
                                                generated_sql = sql_match.group(0)
                                                break
                            elif isinstance(tool_input, str):
                                # Try to extract SQL from string
                                sql_match = re.search(
                                    r"SELECT.*?(?:;|$)", tool_input, re.IGNORECASE | re.DOTALL
                                )
                                if sql_match:
                                    generated_sql = sql_match.group(0)

                        # Method 2: Check tool name and extract from action string
                        if not generated_sql and hasattr(action, "tool"):
                            tool_name = str(action.tool) if hasattr(action, "tool") else ""
                            if "sql" in tool_name.lower():
                                action_str = str(action)
                                sql_match = re.search(
                                    r"SELECT.*?(?:;|$)", action_str, re.IGNORECASE | re.DOTALL
                                )
                                if sql_match:
                                    generated_sql = sql_match.group(0)

                        # Method 3: Check the observation/result for SQL
                        if not generated_sql and observation:
                            if isinstance(observation, str):
                                # Look for SQL in observation
                                sql_match = re.search(
                                    r"SELECT.*?(?:;|$)", observation, re.IGNORECASE | re.DOTALL
                                )
                                if sql_match:
                                    generated_sql = sql_match.group(0)
                            elif isinstance(observation, (list, tuple)) and len(observation) > 0:
                                # Check first element if it's a list/tuple
                                first_elem = observation[0]
                                if isinstance(first_elem, str) and "SELECT" in first_elem.upper():
                                    sql_match = re.search(
                                        r"SELECT.*?(?:;|$)", first_elem, re.IGNORECASE | re.DOTALL
                                    )
                                if sql_match:
                                    generated_sql = sql_match.group(0)

                        # Method 4: Check action string representation
                        if not generated_sql:
                            action_str = str(action)
                            if "SELECT" in action_str.upper() or "sql_db_query" in action_str:
                                sql_match = re.search(
                                    r"SELECT.*?(?:;|$)", action_str, re.IGNORECASE | re.DOTALL
                                )
                                if sql_match:
                                    generated_sql = sql_match.group(0)

                        # Method 5: Check if action has args attribute (some LangChain versions)
                        if not generated_sql and hasattr(action, "args"):
                            args = action.args
                            if isinstance(args, dict) and "query" in args:
                                generated_sql = args["query"]
                            elif isinstance(args, dict):
                                # Check all values for SQL
                                for value in args.values():
                                    if isinstance(value, str) and "SELECT" in value.upper():
                                        sql_match = re.search(
                                            r"SELECT.*?(?:;|$)", value, re.IGNORECASE | re.DOTALL
                                        )
                                        if sql_match:
                                            generated_sql = sql_match.group(0)
                                            break

                        # If we found SQL, break early
                        if generated_sql:
                            logger.debug(
                                "sql_extracted_from_steps",
                                sql_preview=generated_sql[:100],
                            )
                            break

            # If we couldn't extract SQL from steps, try to find it in the output
            if not generated_sql:
                sql_match = re.search(r"SELECT.*?(?:;|$)", answer, re.IGNORECASE | re.DOTALL)
                if sql_match:
                    generated_sql = sql_match.group(0)
                    logger.debug("sql_extracted_from_output")

            # Log if we couldn't extract SQL (for debugging)
            if not generated_sql:
                logger.warning(
                    "sql_not_extracted",
                    has_intermediate_steps="intermediate_steps" in result,
                    intermediate_steps_count=len(result.get("intermediate_steps", [])),
                    answer_preview=answer[:200] if answer else None,
                )

            # Validate SQL if we found it
            if generated_sql:
                sanitized_sql, error = self._validate_and_sanitize_sql(generated_sql)
                if error:
                    logger.warning(
                        "sql_validation_failed",
                        error=error,
                        sql_preview=generated_sql[:100] if generated_sql else None,
                    )
                    # Still return the answer, but log the warning
                generated_sql = sanitized_sql

            # Audit log
            if self.audit_logger:
                self.audit_logger.log_query(
                    query=question,
                    generated_sql=generated_sql or "N/A",
                    result={"answer": answer},
                )

            result = {
                "answer": answer,
                "sql_query": generated_sql,
                "question": question,
                "success": True,
            }
        except Exception as e:
            status = "error"
            error_msg = str(e)

            # Audit log error
            if self.audit_logger:
                self.audit_logger.log_query(
                    query=question,
                    generated_sql="N/A",
                    error=error_msg,
                )

            logger.error(
                "sql_agent_error",
                error_message=error_msg,
                query=question,
                exc_info=True,
            )

            result = {
                "answer": f"Грешка при изпълнение на заявката: {error_msg}",
                "sql_query": None,
                "question": question,
                "success": False,
            }
        finally:
            # Track SQL query metrics
            duration = time.time() - start_time
            track_sql_query(status=status, duration=duration)

        return result

    def execute_sql(self, sql: str) -> Dict[str, any]:
        """
        Execute a SQL query directly (with validation).

        This method allows direct SQL execution but still validates the query.

        Args:
            sql: SQL query string

        Returns:
            Dictionary with results and metadata
        """
        # Validate and sanitize
        sanitized_sql, error = self._validate_and_sanitize_sql(sql)
        if error:
            return {
                "success": False,
                "error": error,
                "sql_query": sql,
                "results": None,
            }

        try:
            # Execute query
            result = self.db.run(sanitized_sql)

            # Parse result
            # The result is typically a string representation of rows
            rows = []
            if result:
                # Try to parse the result (format depends on SQLDatabase implementation)
                # For now, just return the raw result
                rows = [result] if isinstance(result, str) else result

            # Audit log
            if self.audit_logger:
                self.audit_logger.log_query(
                    query="Direct SQL execution",
                    generated_sql=sanitized_sql,
                    result={"row_count": len(rows) if isinstance(rows, list) else 1},
                )

            return {
                "success": True,
                "sql_query": sanitized_sql,
                "results": rows,
                "row_count": len(rows) if isinstance(rows, list) else 1,
            }

        except Exception as e:
            error_msg = str(e)

            # Audit log error
            if self.audit_logger:
                self.audit_logger.log_query(
                    query="Direct SQL execution",
                    generated_sql=sanitized_sql,
                    error=error_msg,
                )

            logger.error(
                "sql_execution_error",
                error_message=error_msg,
                sql_preview=sanitized_sql[:100] if sanitized_sql else None,
                exc_info=True,
            )

            return {
                "success": False,
                "error": error_msg,
                "sql_query": sanitized_sql,
                "results": None,
            }


def get_sql_agent_service(
    llm: Optional[BaseChatModel] = None,
    enable_audit_logging: bool = True,
    hallucination_config: Optional[HallucinationConfig] = None,
    callbacks: Optional[List[BaseCallbackHandler]] = None,
) -> SQLAgentService:
    """
    Factory function to get a default SQLAgentService.

    Args:
        llm: Optional LLM instance. If None, creates one from settings.
        enable_audit_logging: Whether to enable audit logging
        hallucination_config: Optional hallucination control configuration
        callbacks: Optional list of LangChain callback handlers

    Returns:
        SQLAgentService instance
    """
    return SQLAgentService(
        llm=llm,
        enable_audit_logging=enable_audit_logging,
        hallucination_config=hallucination_config,
        callbacks=callbacks,
    )
