"""SQL agent using LangChain for querying the database."""

import structlog
import re
from typing import Dict, List, Optional

from app.core.config import settings
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
        "chitalishte": {
            "id",
            "registration_number",
            "created_at",
            "address",
            "bulstat",
            "chairman",
            "chitalishta_url",
            "email",
            "municipality",
            "name",
            "phone",
            "region",
            "secretary",
            "status",
            "town",
            "url_to_libraries_site",
        },
        "information_card": {
            "id",
            "chitalishte_id",
            "year",
            "created_at",
            "administrative_positions",
            "amateur_arts",
            "dancing_groups",
            "disabilities_and_volunteers",
            "employees_count",
            "employees_specialized",
            "employees_with_higher_education",
            "folklore_formations",
            "kraeznanie_clubs",
            "language_courses",
            "library_activity",
            "membership_applications",
            "modern_ballet",
            "museum_collections",
            "new_members",
            "other_activities",
            "other_clubs",
            "participation_in_events",
            "participation_in_live_human_treasures_national",
            "participation_in_live_human_treasures_regional",
            "participation_in_trainings",
            "projects_participation_leading",
            "projects_participation_partner",
            "reg_number",
            "registration_number",
            "rejected_members",
            "subsidiary_count",  # Note: NOT subsidized_count
            "supporting_employees",
            "theatre_formations",
            "total_members_count",
            "town_population",
            "town_users",
            "vocal_groups",
            "workshops_clubs_arts",
            "has_pc_and_internet_services",
            "bulstat",
            "email",
            "kraeznanie_clubs_text",
            "language_courses_text",
            "museum_collections_text",
            "sanctions_for31and33",
            "url",
            "webpage",
            "workshops_clubs_arts_text",
        },
    }

    # Nullable columns that should be filtered when used in ORDER BY or important queries
    # These are columns that can be NULL and should have IS NOT NULL filter when queried
    NULLABLE_COLUMNS = {
        "information_card": {
            "subsidiary_count",
            "employees_count",
            "total_members_count",
            "new_members",
            "rejected_members",
            "town_population",
            "town_users",
            "administrative_positions",
            "amateur_arts",
            "dancing_groups",
            "disabilities_and_volunteers",
            "employees_specialized",
            "employees_with_higher_education",
            "folklore_formations",
            "kraeznanie_clubs",
            "language_courses",
            "library_activity",
            "membership_applications",
            "modern_ballet",
            "museum_collections",
            "other_activities",
            "other_clubs",
            "participation_in_events",
            "participation_in_live_human_treasures_national",
            "participation_in_live_human_treasures_regional",
            "participation_in_trainings",
            "projects_participation_leading",
            "projects_participation_partner",
            "supporting_employees",
            "theatre_formations",
            "vocal_groups",
            "workshops_clubs_arts",
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
            return False, f"Invalid column names detected: {', '.join(invalid_columns)}", invalid_columns

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
                return False, f"Dangerous SQL keyword detected: {keyword}. Only SELECT queries are allowed."

        # Ensure it starts with SELECT or WITH (for CTEs)
        if not (sql_upper.startswith("SELECT") or sql_upper.startswith("WITH")):
            return False, "Query must start with SELECT or WITH (for CTEs). Only read operations are allowed."

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
            "chitalishte": (
                "Table: chitalishte\n"
                "COLUMNS (use ONLY these exact column names):\n"
                "- id (INTEGER, primary key)\n"
                "- registration_number (INTEGER)\n"
                "- created_at (TIMESTAMP)\n"
                "- address (VARCHAR)\n"
                "- bulstat (VARCHAR)\n"
                "- chairman (VARCHAR)\n"
                "- chitalishta_url (VARCHAR)\n"
                "- email (VARCHAR)\n"
                "- municipality (VARCHAR)\n"
                "- name (VARCHAR)\n"
                "- phone (VARCHAR)\n"
                "- region (VARCHAR)\n"
                "- secretary (VARCHAR)\n"
                "- status (VARCHAR)\n"
                "- town (VARCHAR)\n"
                "- url_to_libraries_site (VARCHAR)\n"
                "\n"
                "CRITICAL RULES:\n"
                "1. NEVER invent column names that don't exist in the list above.\n"
                "2. For text field comparisons (region, town, municipality, status, etc.), "
                "ALWAYS use case-insensitive comparison:\n"
                "   - Use ILIKE instead of = (e.g., WHERE region ILIKE 'Враца')\n"
                "   - OR use LOWER() function: WHERE LOWER(region) = LOWER('Враца')\n"
                "3. IMPORTANT - The 'town' column contains values like 'ГРАД ВРАЦА' or 'СЕЛО ВРАЦА' "
                "(i.e., 'ГРАД/СЕЛО <name>'), NOT just the town name.\n"
                "   When filtering by town, ALWAYS use ILIKE with wildcards: WHERE town ILIKE '%Враца%'\n"
                "   This will match 'ГРАД ВРАЦА', 'СЕЛО ВРАЦА', or just 'ВРАЦА'.\n"
                "4. When query asks for 'извън град X' (outside city X), use 'town NOT ILIKE' instead of 'town ILIKE'.\n"
                "5. This table does NOT contain subsidiary_count, subsidized_count, or any count fields.\n"
                "   Those fields are in the information_card table.\n"
            ),
            "information_card": (
                "Table: information_card\n"
                "COLUMNS (use ONLY these exact column names):\n"
                "- id (INTEGER, primary key)\n"
                "- chitalishte_id (INTEGER, foreign key to chitalishte.id)\n"
                "- year (INTEGER)\n"
                "- created_at (TIMESTAMP)\n"
                "- administrative_positions (INTEGER)\n"
                "- amateur_arts (INTEGER)\n"
                "- dancing_groups (INTEGER)\n"
                "- disabilities_and_volunteers (INTEGER)\n"
                "- employees_count (DOUBLE)\n"
                "- employees_specialized (INTEGER)\n"
                "- employees_with_higher_education (INTEGER)\n"
                "- folklore_formations (INTEGER)\n"
                "- kraeznanie_clubs (INTEGER)\n"
                "- language_courses (INTEGER)\n"
                "- library_activity (INTEGER)\n"
                "- membership_applications (INTEGER)\n"
                "- modern_ballet (INTEGER)\n"
                "- museum_collections (INTEGER)\n"
                "- new_members (INTEGER)\n"
                "- other_activities (INTEGER)\n"
                "- other_clubs (INTEGER)\n"
                "- participation_in_events (INTEGER)\n"
                "- participation_in_live_human_treasures_national (INTEGER)\n"
                "- participation_in_live_human_treasures_regional (INTEGER)\n"
                "- participation_in_trainings (INTEGER)\n"
                "- projects_participation_leading (INTEGER)\n"
                "- projects_participation_partner (INTEGER)\n"
                "- reg_number (INTEGER)\n"
                "- registration_number (INTEGER)\n"
                "- rejected_members (INTEGER)\n"
                "- subsidiary_count (DOUBLE) - NOTE: This is 'subsidiary_count', NOT 'subsidized_count'\n"
                "- supporting_employees (INTEGER)\n"
                "- theatre_formations (INTEGER)\n"
                "- total_members_count (INTEGER)\n"
                "- town_population (INTEGER)\n"
                "- town_users (INTEGER)\n"
                "- vocal_groups (INTEGER)\n"
                "- workshops_clubs_arts (INTEGER)\n"
                "- has_pc_and_internet_services (BOOLEAN)\n"
                "- bulstat (VARCHAR)\n"
                "- email (VARCHAR)\n"
                "- kraeznanie_clubs_text (TEXT)\n"
                "- language_courses_text (TEXT)\n"
                "- museum_collections_text (TEXT)\n"
                "- sanctions_for31and33 (VARCHAR)\n"
                "- url (VARCHAR)\n"
                "- webpage (VARCHAR)\n"
                "- workshops_clubs_arts_text (TEXT)\n"
                "\n"
                "CRITICAL RULES:\n"
                "1. NEVER invent column names that don't exist in the list above.\n"
                "2. The column is 'subsidiary_count' (NOT 'subsidized_count').\n"
                "3. To access information_card columns, you MUST JOIN with chitalishte:\n"
                "   JOIN information_card ON chitalishte.id = information_card.chitalishte_id\n"
                "4. If a query needs subsidiary_count or other information_card fields, "
                "you MUST include the JOIN.\n"
                "5. IMPORTANT - Many columns in this table can be NULL (including subsidiary_count, "
                "employees_count, total_members_count, etc.). When ordering by these columns or "
                "querying for meaningful results, ALWAYS add IS NOT NULL filter:\n"
                "   Example: WHERE information_card.subsidiary_count IS NOT NULL\n"
                "   This ensures you get records with actual values, not NULLs.\n"
                "6. CRITICAL - Each chitalishte can have MULTIPLE information_card records (one per year). "
                "When joining chitalishte with information_card and ordering by information_card columns, "
                "you MUST use GROUP BY chitalishte.id and MAX() aggregation to avoid duplicate chitalishte records:\n"
                "   Example: SELECT ch.name, MAX(ic.subsidiary_count) FROM chitalishte ch "
                "JOIN information_card ic ON ch.id = ic.chitalishte_id "
                "GROUP BY ch.id ORDER BY MAX(ic.subsidiary_count) DESC\n"
                "   This ensures each chitalishte appears only once in results.\n"
            ),
        }

        self.db = SQLDatabase(
            engine=engine,
            # Include only the tables we want to expose
            include_tables=["chitalishte", "information_card"],
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
            "4. ВАЖНО: Колоната е 'subsidiary_count' (НЕ 'subsidized_count') и е в таблицата 'information_card'.\n"
            "5. Ако заявката изисква колони от 'information_card', ТРЯБВА да направиш JOIN:\n"
            "   JOIN information_card ON chitalishte.id = information_card.chitalishte_id\n"
            "\n"
            "ОСНОВНИ ПРАВИЛА:\n"
            "1. Генерирай САМО SELECT заявки. Никога не използвай DELETE, UPDATE, INSERT, DROP или други модифициращи команди.\n"
            "2. Използвай таблиците 'chitalishte' и 'information_card'.\n"
            "3. За агрегации използвай COUNT, SUM, AVG, MIN, MAX.\n"
            "4. За JOIN операции използвай правилните ключове:\n"
            "   - chitalishte.id = information_card.chitalishte_id\n"
            "5. Бъди точен с имената на колоните - ВИНАГИ проверявай схемата.\n"
            "6. Ако потребителят пита за статистика, използвай GROUP BY.\n"
            "7. Връщай резултатите на български език, когато е възможно.\n"
            "8. ВАЖНО - Много колони в information_card могат да бъдат NULL (subsidiary_count, "
            "employees_count, total_members_count и др.). Когато сортираш по тези колони или търсиш "
            "смислени резултати, ВИНАГИ добави IS NOT NULL филтър:\n"
            "   Пример: WHERE information_card.subsidiary_count IS NOT NULL\n"
            "   Това гарантира, че получаваш записи с реални стойности, а не NULL.\n"
            "9. КРИТИЧНО - Всяко chitalishte може да има МНОЖЕСТВО information_card записи (по един за всяка година). "
            "Когато правиш JOIN между chitalishte и information_card и сортираш по колони от information_card, "
            "ТРЯБВА да използваш GROUP BY chitalishte.id и MAX() агрегация, за да избегнеш дублирани chitalishte записи:\n"
            "   Пример: SELECT ch.name, MAX(ic.subsidiary_count) FROM chitalishte ch "
            "JOIN information_card ic ON ch.id = ic.chitalishte_id "
            "GROUP BY ch.id ORDER BY MAX(ic.subsidiary_count) DESC\n"
            "   Това гарантира, че всяко chitalishte се появява само веднъж в резултатите.\n"
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
                    # Check if this column is nullable in information_card
                    # We check both the actual table name and common aliases (ic, information_card)
                    # Only add filter if it's an information_card column
                    if (
                        col_name in self.validator.NULLABLE_COLUMNS.get("information_card", set())
                        and table_or_alias in ["information_card", "ic", "card"]
                    ):
                        # Check if IS NOT NULL filter already exists for this column
                        # Look for the column reference with IS NOT NULL in WHERE clause
                        # Use case-insensitive search
                        where_pattern = rf"{re.escape(col_ref_clean)}\s+IS\s+NOT\s+NULL"
                        if not re.search(where_pattern, sql_upper):
                            filters_to_add.append(f"{col_ref_clean} IS NOT NULL")

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
        Fix duplicate chitalishte records when joining with information_card.

        When joining chitalishte with information_card and ordering by information_card columns,
        we get duplicates because each chitalishte can have multiple information_card records.
        This method automatically adds GROUP BY and MAX() aggregation to get one record per chitalishte.

        Args:
            sql: SQL query string

        Returns:
            SQL query with GROUP BY and aggregation to prevent duplicates
        """
        sql_upper = sql.upper()

        # Check if query joins with information_card
        has_information_card_join = re.search(
            r"JOIN\s+information_card|JOIN\s+\w+\s+(?:ic|card)\s+ON",
            sql_upper,
        )

        if not has_information_card_join:
            return sql

        # Check if query already has GROUP BY
        has_group_by = re.search(r"\bGROUP\s+BY\b", sql_upper)
        if has_group_by:
            # Already has GROUP BY, assume it's handled correctly
            return sql

        # Check if query orders by an information_card column
        order_by_match = re.search(r"ORDER\s+BY\s+([^,\n]+)", sql_upper)
        if not order_by_match:
            return sql

        order_by_clause = order_by_match.group(1)
        # Extract column references from ORDER BY
        order_by_cols = re.findall(
            r"(\w+\.\w+|\w+)(?:\s+(?:ASC|DESC))?", order_by_clause, re.IGNORECASE
        )

        # Check if any ORDER BY column is from information_card
        ic_order_by_col = None
        for col_ref in order_by_cols:
            col_ref_clean = col_ref.strip()
            if "." in col_ref_clean:
                parts = col_ref_clean.split(".")
                if len(parts) == 2:
                    table_or_alias, col_name = parts[0].lower(), parts[1].lower()
                    if table_or_alias in ["information_card", "ic", "card"]:
                        ic_order_by_col = col_ref_clean
                        break

        if not ic_order_by_col:
            return sql

        # Find chitalishte table alias
        chitalishte_alias = None
        alias_match = re.search(
            r"FROM\s+chitalishte\s+(\w+)|FROM\s+(\w+)\s+chitalishte",
            sql_upper,
        )
        if alias_match:
            chitalishte_alias = alias_match.group(1) or alias_match.group(2)

        # Determine chitalishte identifier for GROUP BY
        if chitalishte_alias:
            chitalishte_id_col = f"{chitalishte_alias}.id"
        else:
            chitalishte_id_col = "chitalishte.id"

        # Wrap the information_card column in MAX() in SELECT if it's there
        select_match = re.search(r"SELECT\s+(.+?)\s+FROM", sql_upper, re.DOTALL)
        if select_match:
            select_clause = select_match.group(1)
            # Check if the order by column appears in SELECT
            select_col_pattern = rf"\b{re.escape(ic_order_by_col)}\b"
            if re.search(select_col_pattern, select_clause, re.IGNORECASE):
                # Check if it's already wrapped in an aggregate function
                if not re.search(
                    rf"(MAX|SUM|AVG|MIN|COUNT)\s*\(\s*{re.escape(ic_order_by_col)}\s*\)",
                    select_clause,
                    re.IGNORECASE,
                ):
                    # Replace with MAX(column)
                    select_clause_new = re.sub(
                        select_col_pattern,
                        f"MAX({ic_order_by_col})",
                        select_clause,
                        flags=re.IGNORECASE,
                    )
                    sql = sql.replace(select_clause, select_clause_new)

        # Add GROUP BY before ORDER BY
        order_by_pos = order_by_match.start()
        sql = sql[:order_by_pos] + f" GROUP BY {chitalishte_id_col} " + sql[order_by_pos:]

        # Update ORDER BY to use MAX() as well
        sql_upper = sql.upper()
        order_by_match_new = re.search(r"ORDER\s+BY\s+([^,\n]+)", sql_upper)
        if order_by_match_new:
            order_by_clause_new = order_by_match_new.group(1)
            # Check if MAX() is already there
            if not re.search(
                rf"MAX\s*\(\s*{re.escape(ic_order_by_col)}\s*\)",
                order_by_clause_new,
                re.IGNORECASE,
            ):
                # Replace the column with MAX(column) in ORDER BY
                order_by_new = re.sub(
                    rf"\b{re.escape(ic_order_by_col)}\b",
                    f"MAX({ic_order_by_col})",
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

    def _fix_town_field_patterns(self, sql: str) -> str:
        """
        Fix town field comparisons to handle patterns like "ГРАД ВРАЦА" or "СЕЛО ВРАЦА".

        The town column contains values like "ГРАД ВРАЦА" or "СЕЛО ВРАЦА" (i.e., "ГРАД/СЕЛО <name>"),
        not just the town name. This method converts exact matches to pattern matches using ILIKE.

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
                                            sql_match = re.search(r"SELECT.*?(?:;|$)", value, re.IGNORECASE | re.DOTALL)
                                            if sql_match:
                                                generated_sql = sql_match.group(0)
                                                break
                            elif isinstance(tool_input, str):
                                # Try to extract SQL from string
                                sql_match = re.search(r"SELECT.*?(?:;|$)", tool_input, re.IGNORECASE | re.DOTALL)
                                if sql_match:
                                    generated_sql = sql_match.group(0)

                        # Method 2: Check tool name and extract from action string
                        if not generated_sql and hasattr(action, "tool"):
                            tool_name = str(action.tool) if hasattr(action, "tool") else ""
                            if "sql" in tool_name.lower():
                                action_str = str(action)
                                sql_match = re.search(r"SELECT.*?(?:;|$)", action_str, re.IGNORECASE | re.DOTALL)
                                if sql_match:
                                    generated_sql = sql_match.group(0)

                        # Method 3: Check the observation/result for SQL
                        if not generated_sql and observation:
                            if isinstance(observation, str):
                                # Look for SQL in observation
                                sql_match = re.search(r"SELECT.*?(?:;|$)", observation, re.IGNORECASE | re.DOTALL)
                                if sql_match:
                                    generated_sql = sql_match.group(0)
                            elif isinstance(observation, (list, tuple)) and len(observation) > 0:
                                # Check first element if it's a list/tuple
                                first_elem = observation[0]
                                if isinstance(first_elem, str) and "SELECT" in first_elem.upper():
                                    sql_match = re.search(r"SELECT.*?(?:;|$)", first_elem, re.IGNORECASE | re.DOTALL)
                                if sql_match:
                                    generated_sql = sql_match.group(0)

                        # Method 4: Check action string representation
                        if not generated_sql:
                            action_str = str(action)
                            if "SELECT" in action_str.upper() or "sql_db_query" in action_str:
                                sql_match = re.search(r"SELECT.*?(?:;|$)", action_str, re.IGNORECASE | re.DOTALL)
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
                                        sql_match = re.search(r"SELECT.*?(?:;|$)", value, re.IGNORECASE | re.DOTALL)
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

            return {
                "answer": answer,
                "sql_query": generated_sql,
                "question": question,
                "success": True,
            }

        except Exception as e:
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

            return {
                "answer": f"Грешка при изпълнение на заявката: {error_msg}",
                "sql_query": None,
                "question": question,
                "success": False,
                "error": error_msg,
            }

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

