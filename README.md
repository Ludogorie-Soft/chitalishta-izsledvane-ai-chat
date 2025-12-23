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
   - Update `.env` with your configuration:

   **Database Configuration:**
   ```
   DATABASE_URL=postgresql://root:root@localhost:5434/chitalishta_db
   ```

   **Embedding Model Configuration:**

   Choose one of the following options:

   **Option 1: OpenAI Embeddings (Recommended for production)**
   ```
   EMBEDDING_PROVIDER=openai
   OPENAI_API_KEY=your_openai_api_key_here
   OPENAI_EMBEDDING_MODEL=text-embedding-3-small
   ```
   - Requires an OpenAI API key (get one at https://platform.openai.com/api-keys)
   - `text-embedding-3-small` is the default model (cost-effective, 1536 dimensions)
   - Alternative models: `text-embedding-3-large` (3072 dimensions, higher quality)

   **Option 2: Hugging Face Embeddings (No API key required)**
   ```
   EMBEDDING_PROVIDER=huggingface
   HUGGINGFACE_MODEL_NAME=intfloat/multilingual-e5-base
   ```
   - No API key required (runs locally)
   - `intfloat/multilingual-e5-base` is optimized for multilingual text including Bulgarian
   - 768 dimensions, good quality for Bulgarian language
   - Alternative models: `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` (faster, smaller)

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


