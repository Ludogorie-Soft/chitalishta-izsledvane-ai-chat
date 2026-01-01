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

   **LLM Configuration (for Intent Classification and Chat):**

   The system uses an LLM registry that supports task-based model selection. You can configure different models for different tasks:
   - **Classification tasks** (intent classification, routing): Fast, cost-effective models
   - **Generation tasks** (RAG, SQL agent): More powerful models for quality
   - **Synthesis tasks** (combining SQL and RAG results): Balanced models

   **Task-Specific Provider Configuration (Optional):**
   ```
   LLM_PROVIDER=openai                    # Default provider for all tasks
   LLM_PROVIDER_CLASSIFICATION=openai     # Optional: Override for classification
   LLM_PROVIDER_GENERATION=openai         # Optional: Override for generation
   LLM_PROVIDER_SYNTHESIS=openai          # Optional: Override for synthesis
   ```
   If not specified, all tasks use `LLM_PROVIDER`. This allows you to optimize cost/performance per task.

   Choose one of the following provider options:

   **Option 1: OpenAI LLM (Recommended for production)**
   ```
   LLM_PROVIDER=openai
   OPENAI_API_KEY=your_openai_api_key_here
   OPENAI_CHAT_MODEL=gpt-4o-mini
   ```
   - Requires an OpenAI API key (same key as embeddings)
   - `gpt-4o-mini` is the default model (cost-effective, good quality)
   - Alternative models: `gpt-4o`, `gpt-4-turbo` (higher quality, more expensive)

   **Option 2: TGI (Text Generation Inference) - Docker-based LLM (Recommended for local development)**
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

   **RAG Fallback Configuration (Optional - Cost Optimization):**

   The system includes an intelligent fallback mechanism that automatically retries with a more powerful LLM when the initial RAG response indicates "no information" was found. This keeps costs low for basic questions while providing better answers for complex queries.

   **Configuration:**
   ```
   # Enable/disable fallback feature (default: true)
   RAG_ENABLE_FALLBACK=true

   # Fallback LLM provider (empty = use same as LLM_PROVIDER)
   LLM_PROVIDER_FALLBACK=openai

   # Fallback model for OpenAI (more powerful than default)
   OPENAI_CHAT_MODEL_FALLBACK=gpt-4o
   ```

   **How it works:**
   - Initial query uses the default/cheaper LLM (e.g., `gpt-4o-mini`)
   - If the answer contains "Нямам информация за тази заявка" (no information), the system automatically retries with the fallback LLM (e.g., `gpt-4o`)
   - Only uses the expensive model when necessary, keeping costs low
   - Only applies to RAG-only queries (not hybrid queries where SQL might provide answers)

   **Example Cost-Optimized Setup:**
   ```
   # Default: cheap model for most queries
   LLM_PROVIDER=openai
   OPENAI_CHAT_MODEL=gpt-4o-mini

   # Fallback: powerful model only when needed
   LLM_PROVIDER_FALLBACK=openai
   OPENAI_CHAT_MODEL_FALLBACK=gpt-4o
   RAG_ENABLE_FALLBACK=true
   ```

   See `RAG_FALLBACK_FEATURE.md` for detailed documentation.

   **Rate Limiting and Abuse Protection Configuration (Optional):**

   The system includes rate limiting and abuse protection for anonymous users. All limits are configurable via environment variables:

   **Rate Limiting Configuration:**
   ```
   # Enable/disable rate limiting (default: true)
   RATE_LIMIT_ENABLED=true

   # Rate limits for POST /chat and POST /chat/stream endpoints
   RATE_LIMIT_PER_MINUTE=5      # Requests per minute (default: 5)
   RATE_LIMIT_PER_HOUR=40       # Requests per hour (default: 40)
   RATE_LIMIT_PER_DAY=200       # Requests per day (default: 200)

   # Cleanup configuration
   RATE_LIMIT_CLEANUP_INTERVAL_HOURS=24        # Cleanup old records every N hours (default: 24)
   RATE_LIMIT_VIOLATION_RETENTION_DAYS=30      # Keep violation logs for N days (default: 30)
   ```

   **Abuse Protection Configuration:**
   ```
   # Enable/disable abuse protection (default: true)
   ABUSE_PROTECTION_ENABLED=true

   # Abuse detection thresholds
   ABUSE_MAX_QUERY_LENGTH=10000                # Maximum query length in characters (default: 10000)
   ABUSE_MIN_REQUEST_INTERVAL_SECONDS=0.5      # Minimum time between requests in seconds (default: 0.5)
   ABUSE_IP_BLOCK_DURATION_HOURS=1            # Duration of IP block in hours (default: 1)
   ABUSE_MAX_RAPID_REQUESTS=10                 # Max requests in short time window for DoS detection (default: 10)
   ABUSE_RAPID_REQUESTS_WINDOW_SECONDS=5       # Time window for rapid request detection in seconds (default: 5)
   ```

   **How it works:**
   - Rate limiting applies to both IP addresses and session/conversation IDs
   - Limits are enforced per endpoint (currently only `/chat` and `/chat/stream`)
   - When rate limit is exceeded, the API returns HTTP 429 (Too Many Requests) with a `Retry-After` header
   - Abuse violations (DoS, long queries) result in HTTP 403 (Forbidden) and temporary IP blocking
   - All violations are logged to the database for analysis

   **Note**: Rate limiting requires database tables. Run the migration script if needed:
   ```bash
   poetry run python scripts/create_rate_limiting_tables.py
   ```

   **Authentication Configuration:**

   The system uses JWT tokens for Admin API and Setup API endpoints, and API keys for Public API and System API endpoints.

   **Swagger UI Authentication:**
   ```
   SWAGGER_UI_USERNAME=admin
   SWAGGER_UI_PASSWORD=your_secure_password
   ```
   - These credentials protect access to Swagger UI documentation (`/docs` and `/redoc`)
   - The same credentials are used for JWT token generation via `/auth/login` endpoint

   **JWT Authentication Configuration:**
   ```
   # JWT algorithm (RS256 for asymmetric encryption)
   JWT_ALGORITHM=RS256

   # Token expiration times
   JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30      # Access token expires in 30 minutes
   JWT_REFRESH_TOKEN_EXPIRE_DAYS=7         # Refresh token expires in 7 days

   # RSA key pair for JWT signing/verification (PEM format)
   # If not provided, keys will be auto-generated (development only - not recommended for production)
   JWT_RSA_PRIVATE_KEY=-----BEGIN PRIVATE KEY-----
   ...
   -----END PRIVATE KEY-----
   JWT_RSA_PUBLIC_KEY=-----BEGIN PUBLIC KEY-----
   ...
   -----END PUBLIC KEY-----
   ```

   **Generating RSA Keys:**

   For production, you should generate your own RSA key pair. Here are several methods:

   **Method 1: Using OpenSSL (Recommended)**
   ```bash
   # Generate private key (2048-bit RSA)
   openssl genpkey -algorithm RSA -out jwt_private_key.pem -pkeyopt rsa_keygen_bits:2048

   # Extract public key from private key
   openssl rsa -pubout -in jwt_private_key.pem -out jwt_public_key.pem

   # View the keys (copy to .env file)
   cat jwt_private_key.pem
   cat jwt_public_key.pem
   ```

   **Method 2: Using Python (cryptography library)**
   ```python
   from cryptography.hazmat.primitives.asymmetric import rsa
   from cryptography.hazmat.primitives import serialization

   # Generate private key
   private_key = rsa.generate_private_key(
       public_exponent=65537,
       key_size=2048
   )

   # Serialize private key to PEM format
   private_pem = private_key.private_bytes(
       encoding=serialization.Encoding.PEM,
       format=serialization.PrivateFormat.PKCS8,
       encryption_algorithm=serialization.NoEncryption()
   )

   # Serialize public key to PEM format
   public_pem = private_key.public_key().public_bytes(
       encoding=serialization.Encoding.PEM,
       format=serialization.PublicFormat.SubjectPublicKeyInfo
   )

   # Print keys (copy to .env file)
   print("JWT_RSA_PRIVATE_KEY=" + private_pem.decode('utf-8'))
   print("JWT_RSA_PUBLIC_KEY=" + public_pem.decode('utf-8'))
   ```

   **Method 3: Using online tools (for development only)**
   - Visit https://8gwifi.org/rsagen.jsp
   - Generate 2048-bit RSA key pair
   - Copy private and public keys to `.env` file

   **Important Notes:**
   - **Development**: If RSA keys are not provided, the system will auto-generate them (not recommended for production)
   - **Production**: Always generate and securely store your own RSA keys
   - **Security**: Never commit RSA keys to version control. Store them securely (environment variables, secrets manager, etc.)
   - **Format**: Keys must be in PEM format with proper headers/footers:
     - Private key: `-----BEGIN PRIVATE KEY-----` ... `-----END PRIVATE KEY-----`
     - Public key: `-----BEGIN PUBLIC KEY-----` ... `-----END PUBLIC KEY-----`
   - **Multi-line values**: In `.env` files, you can use quotes or escape newlines:
     ```
     JWT_RSA_PRIVATE_KEY="-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----"
     ```

   **API Key Authentication Configuration:**
   ```
   API_KEY=your_api_key_here
   ```
   - This API key is required for Public API endpoints (chat) and System API endpoints (chitalishte data)
   - Generate a secure random string (e.g., using `openssl rand -hex 32`)
   - Share this key only with authorized applications (your React frontend apps)

   **Example complete authentication configuration:**
   ```
   # Swagger UI credentials (also used for JWT login)
   SWAGGER_UI_USERNAME=admin
   SWAGGER_UI_PASSWORD=secure_password_123

   # JWT configuration
   JWT_ALGORITHM=RS256
   JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30
   JWT_REFRESH_TOKEN_EXPIRE_DAYS=7
   JWT_RSA_PRIVATE_KEY="-----BEGIN PRIVATE KEY-----\nMIIEvQIBADANBgkqhkiG9w0BAQEFAASCBKcwggSjAgEAAoIBAQC...\n-----END PRIVATE KEY-----"
   JWT_RSA_PUBLIC_KEY="-----BEGIN PUBLIC KEY-----\nMIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEA...\n-----END PUBLIC KEY-----"

   # API key for Public API and System API
   API_KEY=your_secure_api_key_here
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

## Observability

The application includes comprehensive structured logging and LangChain observability. See `OBSERVABILITY.md` for:
- How to access and analyze logs
- Production observability options (CloudWatch, Loki, ELK)
- Querying LangChain operations
- Performance analysis tools


