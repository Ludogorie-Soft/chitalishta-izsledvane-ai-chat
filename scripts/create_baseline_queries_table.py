"""Create baseline_queries table in the database."""

import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy import text

from app.db.database import engine


def create_baseline_queries_table():
    """Create the baseline_queries table with all necessary columns and indexes."""
    print("Creating baseline_queries table...")

    with engine.connect() as conn:
        # Create table
        conn.execute(
            text(
                """
        CREATE TABLE IF NOT EXISTS baseline_queries (
            -- Primary key
            id BIGSERIAL PRIMARY KEY,

            -- Query information
            query TEXT NOT NULL,

            -- Expected results
            expected_intent VARCHAR(20) NOT NULL,  -- sql/rag/hybrid
            expected_answer TEXT,  -- Expected answer text or pattern
            expected_sql_query TEXT,  -- Optional, if SQL is expected
            expected_rag_executed BOOLEAN NOT NULL DEFAULT FALSE,
            expected_sql_executed BOOLEAN NOT NULL DEFAULT FALSE,

            -- Flexible metadata (JSONB for additional expectations)
            -- Note: Named 'baseline_metadata' to avoid SQLAlchemy reserved 'metadata' attribute
            baseline_metadata JSONB,

            -- Timestamps
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),

            -- Source tracking
            source VARCHAR(50) NOT NULL DEFAULT 'manual_test_query',  -- Source of baseline: 'manual_test_query' (manual test baselines) or 'real_user_query' (from real user queries)

            -- Tracking
            created_by VARCHAR(100),  -- Optional, for tracking who added the baseline

            -- Management
            is_active BOOLEAN NOT NULL DEFAULT TRUE  -- Enable/disable specific baselines
        );
        """
            )
        )

        # Create indexes
        print("Creating indexes...")
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_baseline_queries_is_active ON baseline_queries(is_active) WHERE is_active = TRUE;",
            "CREATE INDEX IF NOT EXISTS idx_baseline_queries_expected_intent ON baseline_queries(expected_intent);",
            "CREATE INDEX IF NOT EXISTS idx_baseline_queries_source ON baseline_queries(source);",
            "CREATE INDEX IF NOT EXISTS idx_baseline_queries_created_at ON baseline_queries(created_at DESC);",
            "CREATE INDEX IF NOT EXISTS idx_baseline_queries_metadata_gin ON baseline_queries USING GIN(baseline_metadata);",
        ]

        for index_sql in indexes:
            conn.execute(text(index_sql))

        conn.commit()

    print("baseline_queries table created successfully!")
    print("\nTable structure:")
    print("  - Primary key: id (BIGSERIAL)")
    print("  - Query: query (TEXT)")
    print("  - Expected results: expected_intent, expected_answer, expected_sql_query, expected_rag_executed, expected_sql_executed")
    print("  - Metadata: baseline_metadata (JSONB)")
    print("  - Timestamps: created_at, updated_at")
    print("  - Source: source (VARCHAR) - 'manual_test_query' (manual test baselines) or 'real_user_query' (from real user queries)")
    print("  - Tracking: created_by")
    print("  - Management: is_active")
    print("  - Indexes: is_active, expected_intent, source, created_at, baseline_metadata (GIN)")
    print("\nYou can now manage baseline queries via SQLAlchemy models or direct SQL queries.")


if __name__ == "__main__":
    create_baseline_queries_table()

