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

2. Start services using Docker Compose:
   ```bash
   docker-compose up -d
   ```
   This will start:
   - Main database on port 5434 (`chitalishta_db`)
   - Test database on port 5435 (`chitalishta_test_db`)
   - TGI (Text Generation Inference) LLM service on port 8080 (if `LLM_PROVIDER=tgi`)

   **Note**: If using TGI, the first start may take 5-10 minutes to download the model.
   Check TGI health: `curl http://localhost:8080/health`

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

   **LLM Configuration (for Intent Classification and Chat):**

   Choose one of the following options:

   **Option 1: OpenAI LLM (Recommended for production)**
   ```
   LLM_PROVIDER=openai
   OPENAI_API_KEY=your_openai_api_key_here
   OPENAI_CHAT_MODEL=gpt-4o-mini
   ```
   - Requires an OpenAI API key (same key as embeddings)
   - `gpt-4o-mini` is the default model (cost-effective, good quality)
   - Alternative models: `gpt-4o`, `gpt-4-turbo` (higher quality, more expensive)

   **Option 2: Hugging Face LLM (No API key required, runs locally)**
   ```
   LLM_PROVIDER=huggingface
   HUGGINGFACE_LLM_MODEL=HuggingFaceH4/zephyr-7b-beta
   ```
   - No API key required (runs locally in the same process)
   - Default model: `HuggingFaceH4/zephyr-7b-beta` (good multilingual support, no authentication required)
   - **For gated models** (like Llama): You need to authenticate with Hugging Face:
     ```bash
     pip install huggingface_hub
     huggingface-cli login
     ```
     Then set: `HUGGINGFACE_LLM_MODEL=meta-llama/Llama-3.2-3B-Instruct`
   - `transformers` and `langchain-community` are already included in the project dependencies
   - **Optional**: For GPU acceleration, install PyTorch separately:
     ```bash
     pip install torch
     ```
     Note: PyTorch may have Python version compatibility issues with Poetry. Installing it separately with pip usually works better.
     - For CPU-only: `pip install torch --index-url https://download.pytorch.org/whl/cpu`
     - For CUDA: `pip install torch --index-url https://download.pytorch.org/whl/cu121`
   - Alternative models:
     - `mistralai/Mistral-7B-Instruct-v0.2` (larger, better quality)
     - `HuggingFaceH4/zephyr-7b-beta` (good multilingual support)
     - `google/gemma-2b-it` (smaller, faster)
   - **Note**: Hugging Face models require significant RAM/VRAM. Ensure you have enough resources for the selected model.

   **Option 3: TGI (Text Generation Inference) - Docker-based LLM (Recommended for local development)**
   ```
   LLM_PROVIDER=tgi
   TGI_BASE_URL=http://localhost:8080/v1
   TGI_MODEL_NAME=google/gemma-2b-it
   TGI_ENABLED=true
   ```
   - Runs in a separate Docker container (isolated from main app)
   - Uses OpenAI-compatible API (seamless integration with LangChain)
   - Default model: `google/gemma-2b-it` (2B params, lightweight, CPU-friendly)
   - **Setup**:
     1. Start TGI service: `docker-compose up -d tgi`
     2. Wait for model to load (first start may take 3-5 minutes to download model)
     3. Check health: `curl http://localhost:8080/health`
   - **Advantages**:
     - No dependency conflicts (runs in separate container)
     - Faster app restarts (model stays loaded)
     - Better resource isolation
     - Automatic fallback to rule-based classifier if TGI is unavailable
     - Lower memory footprint (good for laptops)
   - **Resource Requirements**:
     - Allocates 6GB RAM for Gemma-2b model
     - CPU-only inference (no GPU required)
     - First download: ~4GB disk space for model cache
     - Faster inference than larger models (good for intent classification)
   - **Alternative Models**:
     - `microsoft/Phi-3-mini-4k-instruct` (3.8B params, better quality but more RAM)
     - `microsoft/Phi-3-mini-128k-instruct` (3.8B params, longer context)
   - **Note**: TGI is optimized for local development. For production, use OpenAI (Option 1).

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

### Testing TGI Integration

To test the TGI LLM integration:

1. Start TGI service:
   ```bash
   docker-compose up -d tgi
   ```

2. Wait for model to load (check logs):
   ```bash
   docker-compose logs -f tgi
   ```

3. Verify TGI is healthy:
   ```bash
   curl http://localhost:8080/health
   ```

4. Set environment variable:
   ```bash
   LLM_PROVIDER=tgi
   ```

5. Run LLM intent classification tests:
   ```bash
   poetry run pytest tests/test_llm_intent_classification.py -v
   ```

**Note**: If TGI is unavailable, the system automatically falls back to the rule-based intent classifier.

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


