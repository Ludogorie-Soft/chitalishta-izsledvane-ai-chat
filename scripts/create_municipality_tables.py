"""Create municipality-related tables in the database."""

import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy import text

from app.db.database import engine


def create_municipality_tables():
    """Create the municipality-related tables with all necessary columns, constraints, and indexes."""
    print("Creating municipality-related tables...")

    with engine.connect() as conn:
        # Create municipalities table
        print("Creating municipalities table...")
        conn.execute(
            text(
                """
        CREATE TABLE IF NOT EXISTS municipalities (
            id UUID NOT NULL,
            district VARCHAR(100) NULL,
            district_code VARCHAR(10) NULL,
            migration_coefficient FLOAT8 NULL,
            mrrb_category VARCHAR(100) NULL,
            municipality VARCHAR(100) NULL,
            municipality_code VARCHAR(10) NOT NULL,
            municipality_norm VARCHAR(100) NULL,
            nuts1 VARCHAR(10) NULL,
            nuts2 VARCHAR(10) NULL,
            nuts3 VARCHAR(10) NULL,
            population_over_65_aggregate INT4 NULL,
            population_under_15_aggregate INT4 NULL,
            share_bulgarian FLOAT8 NULL,
            share_others FLOAT8 NULL,
            share_roma FLOAT8 NULL,
            share_turkish FLOAT8 NULL,
            total_chitalishta INT4 NULL,
            CONSTRAINT municipalities_pkey PRIMARY KEY (id),
            CONSTRAINT uk_94eh03mnpurmukl254shp7mt2 UNIQUE (municipality_code)
        );
        """
            )
        )

        # Create municipality_metrics table
        print("Creating municipality_metrics table...")
        conn.execute(
            text(
                """
        CREATE TABLE IF NOT EXISTS municipality_metrics (
            id UUID NOT NULL,
            additional_positions FLOAT8 NULL,
            average_insurance_income NUMERIC(10, 2) NULL,
            chitalishta_no_training_percent NUMERIC(10, 2) NULL,
            chitalishta_per_10k_residents NUMERIC(10, 1) NULL,
            chitalishta_per_1k_children_under_15 NUMERIC(10, 1) NULL,
            chitalishta_per_1k_elderly NUMERIC(10, 1) NULL,
            chitalishta_per_1k_kindergarten NUMERIC(10, 1) NULL,
            chitalishta_per_1k_students NUMERIC(10, 1) NULL,
            city_chitalishta INT4 NULL,
            expenses_for_salaries_percent NUMERIC(10, 2) NULL,
            expenses_other_percent NUMERIC(10, 2) NULL,
            revenue_from_other_percent NUMERIC(10, 2) NULL,
            revenue_from_rent_percent NUMERIC(10, 2) NULL,
            revenue_from_subsidies_percent NUMERIC(10, 2) NULL,
            secretaries_count FLOAT8 NULL,
            secretaries_higher_education_percent NUMERIC(10, 2) NULL,
            staff_higher_education_percent NUMERIC(10, 2) NULL,
            staff_secondary_education_percent NUMERIC(10, 2) NULL,
            state_subsidy_amount NUMERIC(15, 2) NULL,
            state_subsidy_per_capita NUMERIC(10, 2) NULL,
            total_chitalishta INT4 NULL,
            total_staff FLOAT8 NULL,
            unique_employment_contracts INT4 NULL,
            village_chitalishta INT4 NULL,
            municipality_id UUID NOT NULL,
            CONSTRAINT municipality_metrics_pkey PRIMARY KEY (id),
            CONSTRAINT uk_pllim8m1391nr8ch9vqw4ye1b UNIQUE (municipality_id),
            CONSTRAINT fkqkvhakp2fdtt4p1upg0tnywky FOREIGN KEY (municipality_id) REFERENCES municipalities(id)
        );
        """
            )
        )

        # Create municipality_year_data table
        print("Creating municipality_year_data table...")
        conn.execute(
            text(
                """
        CREATE TABLE IF NOT EXISTS municipality_year_data (
            municipality_code VARCHAR(10) NOT NULL,
            year INT4 NOT NULL,
            additional_positions FLOAT8 NULL,
            average_insurance_income NUMERIC(10, 2) NULL,
            companies_number INT4 NULL,
            companies_per_capita FLOAT8 NULL,
            employment_rate FLOAT8 NULL,
            expenses_salaries_thousands NUMERIC(15, 2) NULL,
            expenses_social_security_thousands NUMERIC(15, 2) NULL,
            gross_value_added_per_person FLOAT8 NULL,
            gross_wage_monthly FLOAT8 NULL,
            hospitals INT4 NULL,
            kids_kindergartens INT4 NULL,
            municipality_population INT4 NULL,
            poor_health FLOAT8 NULL,
            revenue_from_rent_thousands NUMERIC(15, 2) NULL,
            revenue_from_subsidies_thousands NUMERIC(15, 2) NULL,
            secretaries_count FLOAT8 NULL,
            secretaries_higher_education_count FLOAT8 NULL,
            staff_higher_education_count FLOAT8 NULL,
            staff_secondary_education_count FLOAT8 NULL,
            students_number INT4 NULL,
            students_per_1000 FLOAT8 NULL,
            subsidized_positions FLOAT8 NULL,
            total_expenses_thousands NUMERIC(15, 2) NULL,
            total_revenue_thousands NUMERIC(15, 2) NULL,
            total_staff_count FLOAT8 NULL,
            unemployment_rate FLOAT8 NULL,
            unemployment_rate_15_29 FLOAT8 NULL,
            unique_employment_contracts INT4 NULL,
            urban_population_percent FLOAT8 NULL,
            municipality_id UUID NOT NULL,
            CONSTRAINT municipality_year_data_pkey PRIMARY KEY (municipality_code, year),
            CONSTRAINT fk1dxqb8b8nu2ux3jj7ugq6n0d7 FOREIGN KEY (municipality_id) REFERENCES municipalities(id)
        );
        """
            )
        )

        # Create settlements table
        print("Creating settlements table...")
        conn.execute(
            text(
                """
        CREATE TABLE IF NOT EXISTS settlements (
            ekatte VARCHAR(10) NOT NULL,
            elementary_education INT4 NULL,
            higher_education INT4 NULL,
            illiterate INT4 NULL,
            literate INT4 NULL,
            no_education INT4 NULL,
            population_15_64 INT4 NULL,
            population_over_65 INT4 NULL,
            population_under_15 INT4 NULL,
            primary_education INT4 NULL,
            secondary_education INT4 NULL,
            settlement_norm VARCHAR(200) NULL,
            settlement_population INT4 NULL,
            village_city VARCHAR(20) NULL,
            municipality_code VARCHAR(10) NOT NULL,
            CONSTRAINT settlements_pkey PRIMARY KEY (ekatte),
            CONSTRAINT fkjhg5fnvbqxrlkc1hw9ew2lb7s FOREIGN KEY (municipality_code) REFERENCES municipalities(municipality_code)
        );
        """
            )
        )

        # Create indexes
        print("Creating indexes...")
        indexes = [
            # municipalities indexes
            "CREATE INDEX IF NOT EXISTS idx_municipalities_municipality_code ON municipalities(municipality_code);",
            "CREATE INDEX IF NOT EXISTS idx_municipalities_district ON municipalities(district);",
            "CREATE INDEX IF NOT EXISTS idx_municipalities_municipality ON municipalities(municipality);",
            # municipality_metrics indexes
            "CREATE INDEX IF NOT EXISTS idx_municipality_metrics_municipality_id ON municipality_metrics(municipality_id);",
            # municipality_year_data indexes
            "CREATE INDEX IF NOT EXISTS idx_municipality_year_data_municipality_code ON municipality_year_data(municipality_code);",
            "CREATE INDEX IF NOT EXISTS idx_municipality_year_data_year ON municipality_year_data(year);",
            "CREATE INDEX IF NOT EXISTS idx_municipality_year_data_municipality_id ON municipality_year_data(municipality_id);",
            "CREATE INDEX IF NOT EXISTS idx_municipality_year_data_municipality_code_year ON municipality_year_data(municipality_code, year);",
            # settlements indexes
            "CREATE INDEX IF NOT EXISTS idx_settlements_municipality_code ON settlements(municipality_code);",
            "CREATE INDEX IF NOT EXISTS idx_settlements_village_city ON settlements(village_city);",
        ]

        for index_sql in indexes:
            conn.execute(text(index_sql))

        conn.commit()

    print("\nMunicipality-related tables created successfully!")
    print("\nTables created:")
    print("  1. municipalities - Stores municipality information")
    print("  2. municipality_metrics - Stores aggregated metrics for municipalities")
    print("  3. municipality_year_data - Stores yearly data for municipalities")
    print("  4. settlements - Stores settlement information")
    print("\nIndexes created for efficient querying.")
    print("\nYou can now use these tables via SQLAlchemy models.")


if __name__ == "__main__":
    create_municipality_tables()
