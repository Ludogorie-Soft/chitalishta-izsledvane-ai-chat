# Chitalishta RAG System

RAG (Retrieval-Augmented Generation) system for Bulgarian Chitalishta research data.

## Tech Stack

- FastAPI
- PostgreSQL (read-first)
- LangChain + Chroma
- Multiple LLMs (OpenAI + TGI)
- Bulgarian-only interface

## Development

### Prerequisites

- Python 3.13
- Poetry

### Setup

1. Install dependencies:
```bash
poetry install
```

2. Start external services (database, etc.) using Docker Compose:
   ```bash
   docker-compose -f docker-compose.dev.yml up -d
   ```
   This will start:
   - Main database on port 5434 (`chitalishta_db`)
   - Test database on port 5435 (`chitalishta_test_db`)
   - Optional: TGI (Text Generation Inference) LLM service on port 8080 (if `LLM_PROVIDER=tgi`)

   **Note**: For local development, the FastAPI app runs directly on your machine (not in Docker).
   For production deployment, use `docker-compose -f docker-compose.prod.yml` (see `DOCKER.md` for details).

3. Initialize database schema:

   **For a fresh database (creates all tables):**
   ```bash
   poetry run python scripts/init_db.py
   ```

   **If you already have data tables (chitalishta, municipalities, etc.) and only need application tables:**
   ```bash
   poetry run python scripts/init_db_additional_tables.py
   ```

4. Configure environment variables:
   - Copy `.env.example` to `.env` (if it doesn't exist)
   - Update `.env` with your configuration:

   See `DEPLOYMENT.md` for detailed environment variable configuration.

5. Run the application (Poetry 2.0+):
```bash
poetry run uvicorn app.main:app --reload
```

Alternatively, activate the virtual environment first:
```bash
poetry env activate
uvicorn app.main:app --reload
```

6. Access the API documentation at: http://localhost:8000/docs

## Testing

Run tests with pytest:
```bash
poetry run pytest
```

Tests use a separate test database (port 5435) that is automatically set up and seeded with test data. See `tests/README.md` for more details.

### Integration and E2E Tests

By default, `pytest` runs only free (mocked) tests. Integration and e2e tests that use real LLMs are opt-in:

```bash
# Integration tests (uses cheaper LLMs like gpt-4o-mini or local TGI)
USE_REAL_LLM=true TEST_LLM_MODEL=gpt-4o-mini poetry run pytest -m integration

# E2E tests (uses production LLMs like gpt-4o - most expensive)
USE_REAL_LLM=true TEST_LLM_MODEL=gpt-4o poetry run pytest -m e2e

# Run all tests (including integration and e2e)
USE_REAL_LLM=true poetry run pytest -m ""
```

**Note**: Integration and e2e tests require proper LLM configuration (API keys, etc.) and will incur costs. See `EVALUATION.md` for detailed information.

See `TESTING_TGI.md` for instructions on testing TGI integration.

## Project Structure

```
├── app/
│   ├── api/          # API endpoints
│   ├── core/         # Core configuration
│   ├── db/           # Database models and connections
│   ├── rag/          # RAG pipeline components
│   ├── services/     # Business logic services
│   └── main.py       # FastAPI application entry point
├── tests/            # Test files
└── IMPLEMENTATION_PLAN.md
```

## Implementation Plan

See `IMPLEMENTATION_PLAN.md` for the detailed step-by-step implementation plan.

## Observability

The application includes comprehensive structured logging and LangChain observability. See `OBSERVABILITY.md` for:
- How to access and analyze logs
- Production observability options (CloudWatch, Loki, ELK)
- Querying LangChain operations
- Performance analysis tools


