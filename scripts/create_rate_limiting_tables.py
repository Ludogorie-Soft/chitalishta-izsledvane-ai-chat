"""Create rate limiting tables in the database."""

import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy import text

from app.db.database import engine


def create_rate_limiting_tables():
    """Create the rate limiting tables with all necessary columns and indexes."""
    print("Creating rate limiting tables...")

    with engine.connect() as conn:
        # Create rate_limit_state table
        print("Creating rate_limit_state table...")
        conn.execute(
            text(
                """
        CREATE TABLE IF NOT EXISTS rate_limit_state (
            -- Primary key
            id BIGSERIAL PRIMARY KEY,

            -- Identification (can be IP address or session/conversation_id)
            identifier VARCHAR(255) NOT NULL,
            identifier_type VARCHAR(20) NOT NULL,  -- 'ip' or 'session'

            -- Rate limit counters (sliding window approach)
            requests_minute INTEGER NOT NULL DEFAULT 0,
            requests_hour INTEGER NOT NULL DEFAULT 0,
            requests_day INTEGER NOT NULL DEFAULT 0,

            -- Timestamps for sliding windows
            first_request_minute TIMESTAMP WITH TIME ZONE,
            first_request_hour TIMESTAMP WITH TIME ZONE,
            first_request_day TIMESTAMP WITH TIME ZONE,

            -- Last request timestamp
            last_request_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),

            -- Timestamps
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
        );
        """
            )
        )

        # Create rate_limit_violations table
        print("Creating rate_limit_violations table...")
        conn.execute(
            text(
                """
        CREATE TABLE IF NOT EXISTS rate_limit_violations (
            -- Primary key
            id BIGSERIAL PRIMARY KEY,

            -- Identification
            identifier VARCHAR(255) NOT NULL,
            identifier_type VARCHAR(20) NOT NULL,  -- 'ip' or 'session'

            -- Violation details
            violation_type VARCHAR(50) NOT NULL,  -- 'rate_limit', 'abuse_dos', 'abuse_long_query', 'abuse_sql_injection', 'abuse_malformed'
            limit_exceeded VARCHAR(20),  -- 'minute', 'hour', 'day' (for rate limit violations)

            -- Request details
            endpoint VARCHAR(255) NOT NULL,
            method VARCHAR(10) NOT NULL,
            user_agent TEXT,
            request_body_preview TEXT,  -- First 500 chars of request body for debugging

            -- Additional context
            violation_details JSONB,

            -- Timestamp
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
        );
        """
            )
        )

        # Create blocked_ips table
        print("Creating blocked_ips table...")
        conn.execute(
            text(
                """
        CREATE TABLE IF NOT EXISTS blocked_ips (
            -- Primary key
            id BIGSERIAL PRIMARY KEY,

            -- IP address
            ip_address VARCHAR(45) NOT NULL UNIQUE,  -- IPv6 max length

            -- Block details
            blocked_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
            blocked_until TIMESTAMP WITH TIME ZONE NOT NULL,
            block_reason VARCHAR(100) NOT NULL,  -- Reason for blocking

            -- Additional context
            violation_count INTEGER NOT NULL DEFAULT 1,
            block_details JSONB,

            -- Timestamp
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
        );
        """
            )
        )

        # Create indexes
        print("Creating indexes...")
        indexes = [
            # rate_limit_state indexes
            "CREATE INDEX IF NOT EXISTS idx_rate_limit_state_identifier ON rate_limit_state(identifier, identifier_type);",
            "CREATE INDEX IF NOT EXISTS idx_rate_limit_state_last_request_at ON rate_limit_state(last_request_at);",
            # rate_limit_violations indexes
            "CREATE INDEX IF NOT EXISTS idx_rate_limit_violations_identifier ON rate_limit_violations(identifier, identifier_type);",
            "CREATE INDEX IF NOT EXISTS idx_rate_limit_violations_created_at ON rate_limit_violations(created_at DESC);",
            "CREATE INDEX IF NOT EXISTS idx_rate_limit_violations_violation_type ON rate_limit_violations(violation_type);",
            "CREATE INDEX IF NOT EXISTS idx_rate_limit_violations_violation_details_gin ON rate_limit_violations USING GIN(violation_details);",
            # blocked_ips indexes
            "CREATE INDEX IF NOT EXISTS idx_blocked_ips_ip_address ON blocked_ips(ip_address);",
            "CREATE INDEX IF NOT EXISTS idx_blocked_ips_blocked_until ON blocked_ips(blocked_until);",
        ]

        for index_sql in indexes:
            conn.execute(text(index_sql))

        conn.commit()

    print("\nRate limiting tables created successfully!")
    print("\nTables created:")
    print("  1. rate_limit_state - Tracks current rate limit counters per IP and session")
    print("  2. rate_limit_violations - Logs all rate limit and abuse violations")
    print("  3. blocked_ips - Tracks temporarily blocked IP addresses")
    print("\nIndexes created for efficient querying.")
    print("\nYou can now use rate limiting features via the RateLimiter service.")


if __name__ == "__main__":
    create_rate_limiting_tables()

