"""Script to add reply_certainty column to chat_logs table."""

import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy import text

from app.db.database import engine


def add_reply_certainty_column():
    """Add reply_certainty column to chat_logs table."""
    with engine.connect() as conn:
        # Add reply_certainty column (Numeric(3, 2) for values like 0.00 to 1.00)
        conn.execute(
            text("""
                ALTER TABLE chat_logs
                ADD COLUMN IF NOT EXISTS reply_certainty NUMERIC(3, 2)
            """)
        )

        # Add index on reply_certainty for analysis queries
        conn.execute(
            text("""
                CREATE INDEX IF NOT EXISTS idx_chat_logs_reply_certainty
                ON chat_logs(reply_certainty)
            """)
        )

        # Add comment to explain the column
        conn.execute(
            text("""
                COMMENT ON COLUMN chat_logs.reply_certainty IS
                'Confidence score (0.0-1.0) indicating how certain the system is that the answer is correct'
            """)
        )

        conn.commit()
        print("✓ Added reply_certainty column to chat_logs table")
        print("✓ Added index for certainty analysis queries")
        print("✓ Added column comment")


if __name__ == "__main__":
    add_reply_certainty_column()

