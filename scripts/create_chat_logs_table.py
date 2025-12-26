"""Create chat_logs table in the database."""

import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy import text

from app.db.database import engine


def create_chat_logs_table():
    """Create the chat_logs table with all necessary columns and indexes."""
    print("Creating chat_logs table...")

    with engine.connect() as conn:
        # Create table
        conn.execute(
            text(
                """
        CREATE TABLE IF NOT EXISTS chat_logs (
            -- Primary identification
            id BIGSERIAL PRIMARY KEY,
            request_id VARCHAR(36) NOT NULL UNIQUE,
            conversation_id VARCHAR(36) NOT NULL,

            -- Timestamps
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
            request_timestamp TIMESTAMP WITH TIME ZONE NOT NULL,

            -- Request data
            user_message TEXT NOT NULL,
            hallucination_mode VARCHAR(20) NOT NULL,
            output_format VARCHAR(20),

            -- Response data
            answer TEXT,
            intent VARCHAR(20),
            routing_confidence NUMERIC(3,2),

            -- Execution flags
            sql_executed BOOLEAN NOT NULL DEFAULT FALSE,
            rag_executed BOOLEAN NOT NULL DEFAULT FALSE,

            -- SQL query (when executed)
            sql_query TEXT,

            -- Performance metrics
            response_time_ms INTEGER,

            -- Cost tracking (token usage totals)
            total_input_tokens INTEGER,
            total_output_tokens INTEGER,
            total_tokens INTEGER,

            -- LLM operations (stored as JSONB array)
            llm_operations JSONB,

            -- Response metadata (routing_explanation, rag_metadata, etc.)
            response_metadata JSONB,

            -- Structured output (if requested)
            structured_output JSONB,

            -- Error information
            error_occurred BOOLEAN NOT NULL DEFAULT FALSE,
            error_type VARCHAR(100),
            error_message TEXT,
            http_status_code INTEGER,

            -- Client information
            client_ip VARCHAR(45),
            user_agent TEXT
        );
        """
            )
        )

        # Create indexes
        print("Creating indexes...")
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_chat_logs_conversation_id ON chat_logs(conversation_id);",
            "CREATE INDEX IF NOT EXISTS idx_chat_logs_created_at ON chat_logs(created_at DESC);",
            "CREATE INDEX IF NOT EXISTS idx_chat_logs_intent ON chat_logs(intent);",
            "CREATE INDEX IF NOT EXISTS idx_chat_logs_sql_executed ON chat_logs(sql_executed) WHERE sql_executed = TRUE;",
            "CREATE INDEX IF NOT EXISTS idx_chat_logs_error_occurred ON chat_logs(error_occurred) WHERE error_occurred = TRUE;",
            "CREATE INDEX IF NOT EXISTS idx_chat_logs_response_metadata_gin ON chat_logs USING GIN(response_metadata);",
            "CREATE INDEX IF NOT EXISTS idx_chat_logs_llm_operations_gin ON chat_logs USING GIN(llm_operations);",
        ]

        for index_sql in indexes:
            conn.execute(text(index_sql))

        conn.commit()

    print("chat_logs table created successfully!")
    print("\nTable structure:")
    print("  - Primary key: id (BIGSERIAL)")
    print("  - Unique constraint: request_id")
    print("  - Indexes: conversation_id, created_at, intent, sql_executed, error_occurred, response_metadata (GIN), llm_operations (GIN)")
    print("\nYou can now query chat logs using SQLAlchemy models or direct SQL queries.")


if __name__ == "__main__":
    create_chat_logs_table()

