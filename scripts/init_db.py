"""Initialize database schema - creates all tables."""

import argparse
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy import inspect

from app.db.database import Base, engine


def init_database(exclude_tables: list[str] | None = None):
    """
    Create database tables, optionally excluding specific tables.

    Args:
        exclude_tables: List of table names to exclude from creation
    """
    if exclude_tables:
        print(f"Creating database tables (excluding: {', '.join(exclude_tables)})...")

        # Get all tables from metadata
        metadata = Base.metadata

        # Filter out excluded tables
        tables_to_create = []
        for table_name, table in metadata.tables.items():
            if table_name not in exclude_tables:
                tables_to_create.append(table)
            else:
                print(f"  Skipping table: {table_name}")

        # Create only the filtered tables
        if tables_to_create:
            metadata.create_all(bind=engine, tables=tables_to_create)
            print(f"Created {len(tables_to_create)} table(s) successfully!")
        else:
            print("No tables to create (all tables excluded).")
    else:
        print("Creating all database tables...")
        Base.metadata.create_all(bind=engine)
        print("Database tables created successfully!")


def list_tables():
    """List all tables defined in the models."""
    metadata = Base.metadata
    tables = sorted(metadata.tables.keys())
    print("Available tables:")
    for table in tables:
        print(f"  - {table}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Initialize database schema - creates database tables"
    )
    parser.add_argument(
        "--exclude",
        type=str,
        help="Comma-separated list of table names to exclude (e.g., 'chitalishta,chitalishte_year_data')",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List all available table names and exit",
    )

    args = parser.parse_args()

    if args.list:
        list_tables()
    else:
        exclude_tables = None
        if args.exclude:
            exclude_tables = [table.strip() for table in args.exclude.split(",")]
        init_database(exclude_tables=exclude_tables)
