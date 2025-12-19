# Chitalishta RAG System

RAG (Retrieval-Augmented Generation) system for Bulgarian Chitalishta research data.

## Tech Stack

- FastAPI
- PostgreSQL (read-first)
- LangChain + Chroma
- Multiple LLMs (OpenAI + Hugging Face)
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

2. Start PostgreSQL databases using Docker Compose:
   ```bash
   docker-compose up -d
   ```
   This will start:
   - Main database on port 5434 (`chitalishta_db`)
   - Test database on port 5435 (`chitalishta_test_db`)

3. Initialize database schema (if using a fresh database):
   ```bash
   poetry run python scripts/init_db.py
   ```
   Note: If you're reusing an existing database with data, skip this step.

4. Configure environment variables:
   - Copy `.env.example` to `.env` (if it doesn't exist)
   - Update `.env` with your database configuration:
     ```
     DATABASE_URL=postgresql://root:root@localhost:5434/chitalishta_db
     ```

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


