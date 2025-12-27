# Test Setup

## Test Database

Tests use a separate PostgreSQL database: `chitalishta_test_db`

### Setup Test Database

The test database is automatically set up via docker-compose:

1. Start both databases:
   ```bash
   docker-compose up -d
   ```

2. The test database runs on port **5435** (main DB is on 5434)

3. Set custom test database URL (optional):
   ```bash
   export TEST_DATABASE_URL=postgresql://root:root@localhost:5435/chitalishta_test_db
   ```

The test database is automatically created and seeded with minimal test data by the pytest fixtures.

## Running Tests

```bash
# Run all tests
poetry run pytest

# Run specific test file
poetry run pytest tests/test_ingestion_preview.py

# Run with verbose output
poetry run pytest -v

# Run specific test
poetry run pytest tests/test_ingestion_preview.py::TestIngestionPreviewBasic::test_preview_with_filters
```

## Test Structure

- `conftest.py`: Pytest fixtures for database setup and test data seeding
- `test_ingestion_preview.py`: Integration tests for `/ingest/database` endpoint

## Test Data

The `seeded_test_data` fixture creates:
- 3 Chitalishte records (in Пловдив and София regions)
- 4 InformationCard records (for years 2022 and 2023)

This minimal dataset is sufficient for testing all filter combinations and edge cases.

