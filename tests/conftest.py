"""Pytest configuration and fixtures for integration tests."""

import os
import uuid
from datetime import datetime
from typing import Generator

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.db.database import Base, get_db
from app.db.models import Chitalishta, ChitalishteYearData, Municipality


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
    # Create test Municipality records first (required for Chitalishta)
    municipality1_id = str(uuid.uuid4())
    municipality1 = Municipality(
        id=municipality1_id,
        municipality_code="PLV01",
        municipality="Пловдив",
        district="Пловдив",
    )

    municipality2_id = str(uuid.uuid4())
    municipality2 = Municipality(
        id=municipality2_id,
        municipality_code="SOF01",
        municipality="София",
        district="София",
    )

    test_db_session.add_all([municipality1, municipality2])
    test_db_session.flush()

    # Create test Chitalishte records
    chitalishte1_id = str(uuid.uuid4())
    chitalishte1 = Chitalishta(
        id=chitalishte1_id,
        reg_n="100",
        name="Тестово читалище 1",
        town="Пловдив",
        address="ул. Тестова 1",
        municipality_id=municipality1_id,
    )

    chitalishte2_id = str(uuid.uuid4())
    chitalishte2 = Chitalishta(
        id=chitalishte2_id,
        reg_n="200",
        name="Тестово читалище 2",
        town="София",
        address="ул. Тестова 2",
        municipality_id=municipality2_id,
    )

    chitalishte3_id = str(uuid.uuid4())
    chitalishte3 = Chitalishta(
        id=chitalishte3_id,
        reg_n="300",
        name="Тестово читалище 3",
        town="Асеновград",
        address="ул. Тестова 3",
        municipality_id=municipality1_id,
    )

    test_db_session.add_all([chitalishte1, chitalishte2, chitalishte3])
    test_db_session.flush()

    # Create test ChitalishteYearData records
    card1_2023 = ChitalishteYearData(
        reg_n="100",
        year=2023,
        chitalishte_id=chitalishte1_id,
        average_annual_staff=2.0,
        folklore_groups=2,
        dance_groups=1,
        vocal_groups=1,
        internet_access=1,
    )

    card1_2022 = ChitalishteYearData(
        reg_n="100",
        year=2022,
        chitalishte_id=chitalishte1_id,
        average_annual_staff=1.5,
        folklore_groups=1,
        internet_access=0,
    )

    card2_2023 = ChitalishteYearData(
        reg_n="200",
        year=2023,
        chitalishte_id=chitalishte2_id,
        average_annual_staff=3.0,
        dance_groups=2,
        vocal_groups=2,
        internet_access=1,
    )

    card3_2023 = ChitalishteYearData(
        reg_n="300",
        year=2023,
        chitalishte_id=chitalishte3_id,
        average_annual_staff=1.0,
        internet_access=0,
    )

    test_db_session.add_all([card1_2023, card1_2022, card2_2023, card3_2023])
    test_db_session.commit()

    return {
        "chitalishte_ids": [chitalishte1_id, chitalishte2_id, chitalishte3_id],
        "chitalishte_reg_ns": ["100", "200", "300"],
        "years": [2022, 2023],
        "municipalities": ["Пловдив", "София"],
        "municipality_ids": [municipality1_id, municipality2_id],
    }


@pytest.fixture
def test_chroma_vector_store():
    """Create test Chroma vector store with separate persistence directory."""
    from app.rag.vector_store import ChromaVectorStore

    # Use test-specific directory
    vector_store = ChromaVectorStore(
        persist_directory="chroma_db_test",
        collection_name="chitalishta_documents_test",
    )

    # Clear collection before each test
    vector_store.clear_collection()

    yield vector_store

    # Cleanup: clear collection after test
    vector_store.clear_collection()


@pytest.fixture
def test_app(test_db_session: Session):
    """Create test FastAPI app with overridden database dependency."""
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from app.api.ingestion import router as ingestion_router
    from app.core.auth import CurrentUser, require_administrator

    def override_get_db():
        try:
            yield test_db_session
        finally:
            pass  # Session cleanup handled by fixture

    # Mock administrator user for tests
    async def override_require_administrator():
        return CurrentUser(username="test_admin", role="administrator")

    app = FastAPI()
    app.include_router(ingestion_router)
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[require_administrator] = override_require_administrator

    return TestClient(app)


# Note: test_indexing_app fixture is defined in tests/test_indexing.py
# to avoid conflicts and allow proper test isolation
