"""Initialize additional database tables - excludes data tables that are already created.

This script creates all application tables EXCEPT:
- chitalishta
- chitalishte_year_data
- municipalities
- municipality_metrics
- municipality_year_data
- settlements

Use this when you already have the data tables created and only need the application tables.
"""

import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from scripts.init_db import init_database

# Tables that are already created and should be excluded
EXCLUDED_TABLES = [
    "chitalishta",
    "chitalishte_year_data",
    "municipalities",
    "municipality_metrics",
    "municipality_year_data",
    "settlements",
]


def main():
    """Create additional database tables."""
    print("=" * 60)
    print("Creating additional database tables")
    print("=" * 60)
    print(f"Excluding {len(EXCLUDED_TABLES)} already-created tables:")
    for table in EXCLUDED_TABLES:
        print(f"  - {table}")
    print()

    init_database(exclude_tables=EXCLUDED_TABLES)

    print()
    print("=" * 60)
    print("Additional tables created successfully!")
    print("=" * 60)
    print()
    print("Created tables:")
    print("  - chat_logs")
    print("  - baseline_queries")
    print("  - users")
    print("  - rate_limit_state")
    print("  - rate_limit_violations")
    print("  - blocked_ips")


if __name__ == "__main__":
    main()
