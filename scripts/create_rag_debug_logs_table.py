"""Create rag_debug_logs table in the database."""

import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy import text

from app.db.database import engine


def create_rag_debug_logs_table():
    """Create the rag_debug_logs table with all necessary columns and indexes."""
    print("Creating rag_debug_logs table...")

    with engine.connect() as conn:
        # Create table
        conn.execute(
            text(
                """
        CREATE TABLE IF NOT EXISTS rag_debug_logs (
            -- Primary key
            id BIGSERIAL PRIMARY KEY,

            -- Foreign key to chat_logs
            request_id VARCHAR(36) NOT NULL UNIQUE,
            CONSTRAINT fk_rag_debug_logs_request_id FOREIGN KEY (request_id) REFERENCES chat_logs(request_id) ON DELETE CASCADE,

            -- Conversation tracking
            conversation_id VARCHAR(36) NOT NULL,

            -- Request data
            user_query TEXT NOT NULL,

            -- Retrieved documents (JSONB - array with summaries)
            -- Format: [{"content_summary": str (first 500 chars), "full_length": int, "metadata": dict, "source": str}, ...]
            retrieved_documents JSONB,

            -- Context and prompts
            formatted_context TEXT,  -- Full formatted context sent to LLM
            prompt_template_used TEXT,  -- Prompt template that was used
            llm_prompt_sent TEXT,  -- Actual prompt sent to LLM (with context)

            -- Retrieval metadata (JSONB)
            retrieval_metadata JSONB,  -- Retrieval scores, sources, etc.

            -- Document counts
            db_doc_count INT4,  -- Number of DB documents
            analysis_doc_count INT4,  -- Number of analysis documents

            -- Performance
            retrieval_duration_ms NUMERIC(10, 2),  -- Retrieval time in milliseconds

            -- LLM response
            llm_response_received TEXT,  -- Raw LLM response before post-processing

            -- Fallback usage
            fallback_llm_used BOOLEAN NOT NULL DEFAULT FALSE,  -- Whether fallback LLM was used

            -- Timestamp
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
        );
        """
            )
        )
        conn.commit()

        # Create indexes
        print("Creating indexes...")
        conn.execute(
            text(
                """
        CREATE INDEX IF NOT EXISTS idx_rag_debug_logs_request_id ON rag_debug_logs(request_id);
        CREATE INDEX IF NOT EXISTS idx_rag_debug_logs_conversation_id ON rag_debug_logs(conversation_id);
        CREATE INDEX IF NOT EXISTS idx_rag_debug_logs_created_at ON rag_debug_logs(created_at);
        """
            )
        )
        conn.commit()

        print("✓ Created rag_debug_logs table")
        print("✓ Created indexes for request_id, conversation_id, and created_at")


if __name__ == "__main__":
    create_rag_debug_logs_table()
    print("\nYou can now use RAG debug logging features via the RagDebugLogger service.")
