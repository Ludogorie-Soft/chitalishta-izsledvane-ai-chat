"""Script to add cost_usd and llm_model columns to chat_logs table."""

import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy import text

from app.db.database import engine


def add_cost_columns():
    """Add cost_usd and llm_model columns to chat_logs table."""
    with engine.connect() as conn:
        # Add cost_usd column (Numeric(10, 6) for up to $9999.999999)
        conn.execute(
            text("""
                ALTER TABLE chat_logs
                ADD COLUMN IF NOT EXISTS cost_usd NUMERIC(10, 6)
            """)
        )

        # Add llm_model column (VARCHAR(100) for model name)
        conn.execute(
            text("""
                ALTER TABLE chat_logs
                ADD COLUMN IF NOT EXISTS llm_model VARCHAR(100)
            """)
        )

        # Add index on llm_model for cost analysis queries
        conn.execute(
            text("""
                CREATE INDEX IF NOT EXISTS idx_chat_logs_llm_model
                ON chat_logs(llm_model)
            """)
        )

        # Add index on cost_usd for cost analysis queries
        conn.execute(
            text("""
                CREATE INDEX IF NOT EXISTS idx_chat_logs_cost_usd
                ON chat_logs(cost_usd)
            """)
        )

        conn.commit()
        print("✓ Added cost_usd and llm_model columns to chat_logs table")
        print("✓ Added indexes for cost analysis queries")


if __name__ == "__main__":
    add_cost_columns()

