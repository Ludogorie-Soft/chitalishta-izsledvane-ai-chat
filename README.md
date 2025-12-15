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

2. Configure environment variables:
   - Copy `.env.example` to `.env` (if it doesn't exist)
   - Update `.env` with your database configuration:
     ```
     DATABASE_URL=postgresql://root:root@localhost:5434/chitalishta_db
     ```
   - Make sure your PostgreSQL database is running (see docker-compose.yml)

3. Run the application (Poetry 2.0+):
```bash
poetry run uvicorn app.main:app --reload
```

Alternatively, activate the virtual environment first:
```bash
poetry env activate
uvicorn app.main:app --reload
```

3. Access the API documentation at: http://localhost:8000/docs

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


