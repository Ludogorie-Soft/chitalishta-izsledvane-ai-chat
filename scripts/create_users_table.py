"""Create users table in the database."""

import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy import text

from app.db.database import engine


def create_users_table():
    """Create the users table with all necessary columns and indexes."""
    print("Creating users table...")

    with engine.connect() as conn:
        # Create table
        conn.execute(
            text(
                """
        CREATE TABLE IF NOT EXISTS users (
            -- Primary key
            id BIGSERIAL PRIMARY KEY,

            -- Authentication fields
            username VARCHAR(100) NOT NULL UNIQUE,
            email VARCHAR(255) UNIQUE,
            password_hash VARCHAR(255) NOT NULL,

            -- Role-based access control
            role VARCHAR(50) NOT NULL DEFAULT 'administrator',  -- Initially only 'administrator', but extensible for future roles (e.g., 'moderator', 'viewer')

            -- User status
            is_active BOOLEAN NOT NULL DEFAULT TRUE,  -- Enable/disable users

            -- Timestamps
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
            last_login TIMESTAMP WITH TIME ZONE  -- Optional timestamp for last login
        );
        """
            )
        )

        # Create indexes
        print("Creating indexes...")
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);",
            "CREATE INDEX IF NOT EXISTS idx_users_email ON users(email) WHERE email IS NOT NULL;",
            "CREATE INDEX IF NOT EXISTS idx_users_role ON users(role);",
            "CREATE INDEX IF NOT EXISTS idx_users_is_active ON users(is_active) WHERE is_active = TRUE;",
        ]

        for index_sql in indexes:
            conn.execute(text(index_sql))

        conn.commit()

    print("users table created successfully!")
    print("\nTable structure:")
    print("  - Primary key: id (BIGSERIAL)")
    print("  - Authentication: username (VARCHAR(100), unique), email (VARCHAR(255), unique), password_hash (VARCHAR(255))")
    print("  - Role: role (VARCHAR(50), default: 'administrator')")
    print("  - Status: is_active (BOOLEAN, default: TRUE)")
    print("  - Timestamps: created_at, updated_at, last_login")
    print("  - Indexes: username, email, role, is_active")
    print("\nYou can now manage users via SQLAlchemy models or direct SQL queries.")


if __name__ == "__main__":
    create_users_table()

