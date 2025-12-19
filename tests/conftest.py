"""Pytest configuration and fixtures for integration tests."""
import os
from datetime import datetime
from typing import Generator

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.db.database import Base, get_db
from app.db.models import Chitalishte, InformationCard


@pytest.fixture(scope="session")
def test_database_url() -> str:
    """
    Get test database URL from environment or use default.

    Default: postgresql://root:root@localhost:5435/chitalishta_test_db
    Note: Test database uses port 5435 to avoid conflict with main DB (5434)
    """
    return os.getenv(
        "TEST_DATABASE_URL",
        "postgresql://root:root@localhost:5435/chitalishta_test_db",
    )


@pytest.fixture(scope="session")
def test_engine(test_database_url: str):
    """Create test database engine."""
    engine = create_engine(test_database_url, pool_pre_ping=True)
    return engine


@pytest.fixture(scope="session", autouse=True)
def setup_test_database(test_engine):
    """Create test database tables."""
    # Create all tables
    Base.metadata.create_all(bind=test_engine)
    yield
    # Cleanup: drop all tables
    Base.metadata.drop_all(bind=test_engine)


@pytest.fixture
def test_db_session(test_engine) -> Generator[Session, None, None]:
    """Create a test database session with transaction rollback."""
    connection = test_engine.connect()
    transaction = connection.begin()
    session = sessionmaker(bind=connection)()

    yield session

    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture
def seeded_test_data(test_db_session: Session):
    """Seed test database with minimal test data."""
    # Create test Chitalishte records
    chitalishte1 = Chitalishte(
        id=1,
        registration_number=100,
        created_at=datetime.now(),
        name="Тестово читалище 1",
        region="Пловдив",
        municipality="Пловдив",
        town="Пловдив",
        status="Действащо",
        address="ул. Тестова 1",
        email="test1@example.com",
    )

    chitalishte2 = Chitalishte(
        id=2,
        registration_number=200,
        created_at=datetime.now(),
        name="Тестово читалище 2",
        region="София",
        municipality="София",
        town="София",
        status="Действащо",
        address="ул. Тестова 2",
    )

    chitalishte3 = Chitalishte(
        id=3,
        registration_number=300,
        created_at=datetime.now(),
        name="Тестово читалище 3",
        region="Пловдив",
        municipality="Пловдив",
        town="Асеновград",
        status="Закрито",
        address="ул. Тестова 3",
    )

    test_db_session.add_all([chitalishte1, chitalishte2, chitalishte3])
    test_db_session.flush()

    # Create test InformationCard records
    card1_2023 = InformationCard(
        id=1,
        chitalishte_id=1,
        year=2023,
        created_at=datetime.now(),
        total_members_count=50,
        employees_count=2.0,
        subsidiary_count=1.5,
        folklore_formations=2,
        theatre_formations=1,
        vocal_groups=1,
        has_pc_and_internet_services=True,
    )

    card1_2022 = InformationCard(
        id=2,
        chitalishte_id=1,
        year=2022,
        created_at=datetime.now(),
        total_members_count=45,
        employees_count=1.5,
        subsidiary_count=1.0,
        folklore_formations=1,
        has_pc_and_internet_services=False,
    )

    card2_2023 = InformationCard(
        id=3,
        chitalishte_id=2,
        year=2023,
        created_at=datetime.now(),
        total_members_count=100,
        employees_count=3.0,
        subsidiary_count=2.0,
        theatre_formations=2,
        vocal_groups=2,
        has_pc_and_internet_services=True,
    )

    card3_2023 = InformationCard(
        id=4,
        chitalishte_id=3,
        year=2023,
        created_at=datetime.now(),
        total_members_count=30,
        employees_count=1.0,
        subsidiary_count=0.5,
        has_pc_and_internet_services=False,
    )

    test_db_session.add_all([card1_2023, card1_2022, card2_2023, card3_2023])
    test_db_session.commit()

    return {
        "chitalishte_ids": [1, 2, 3],
        "years": [2022, 2023],
        "regions": ["Пловдив", "София"],
        "statuses": ["Действащо", "Закрито"],
    }


@pytest.fixture
def test_app(test_db_session: Session):
    """Create test FastAPI app with overridden database dependency."""
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from app.api.ingestion import router as ingestion_router

    def override_get_db():
        try:
            yield test_db_session
        finally:
            pass  # Session cleanup handled by fixture

    app = FastAPI()
    app.include_router(ingestion_router)
    app.dependency_overrides[get_db] = override_get_db

    return TestClient(app)

