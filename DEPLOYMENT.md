# Deployment Guide

## AWS EC2 Deployment

This guide covers deploying the Chitalishta AI Chat application to AWS EC2.

### Prerequisites

- Docker and Docker Compose installed on EC2 instance
- Docker Hub account for pulling images
- Environment variables configured

### Document Handling in Production

The application requires access to analysis documents (stored in the `documents/` folder). There are two approaches:

#### Option 1: Documents Baked into Docker Image (Recommended)

This is the default configuration for production. Documents are copied into the Docker image during build time.

**Advantages:**
- No need to manually copy documents to EC2
- Documents are version-controlled with the image
- Simpler deployment process

**Steps:**
1. Ensure `documents/` folder contains required files before building the image
2. Build and push the image:
   ```bash
   docker build -t your-registry/chitalishta_ai_chat_api:latest .
   docker push your-registry/chitalishta_ai_chat_api:latest
   ```

3. On EC2, the `docker-compose.prod.yml` file has the volume mount commented out by default:
   ```yaml
   volumes:
     - chroma_db_data:/app/chroma_db
     # Documents are included in the image - no mount needed
     # - ./documents:/app/documents:ro
   ```

4. Pull and start the container:
   ```bash
   docker-compose -f docker-compose.prod.yml pull
   docker-compose -f docker-compose.prod.yml up -d
   ```

**Note:** If you need to update documents, you must rebuild and redeploy the Docker image.

#### Option 2: Mount Documents from Host (For Frequent Updates)

If you need to frequently update documents without rebuilding the image, use volume mounting.

**Advantages:**
- Can update documents without rebuilding image
- Useful for development or frequent content changes

**Steps:**
1. Copy documents folder to EC2:
   ```bash
   # From your local machine
   scp -r documents/ ec2-user@your-ec2-ip:/home/ec2-user/chitalishta/
   ```

2. On EC2, uncomment the volume mount in `docker-compose.prod.yml`:
   ```yaml
   volumes:
     - chroma_db_data:/app/chroma_db
     - ./documents:/app/documents:ro  # Uncomment this line
   ```

3. Ensure the documents folder exists in the same directory as docker-compose.prod.yml:
   ```bash
   cd /home/ec2-user/chitalishta/
   ls -la documents/  # Verify files exist
   ```

4. Start the container:
   ```bash
   docker-compose -f docker-compose.prod.yml up -d
   ```

### Troubleshooting

#### Error: "Document file not found"

**Symptoms:**
```json
{
  "status": "error",
  "message": "Document file not found: Document not found: /app/documents/...",
}
```

**Cause:** The documents folder is not available in the container.

**Solution:**
1. Check if using Option 1 (baked into image):
   - Verify documents were in the build context when image was built
   - Verify volume mount is commented out in docker-compose.prod.yml
   - Rebuild and redeploy the image

2. Check if using Option 2 (volume mount):
   - Verify documents folder exists on EC2 host
   - Verify volume mount is uncommented in docker-compose.prod.yml
   - Verify correct file permissions (readable by container user)
   - Restart container: `docker-compose -f docker-compose.prod.yml restart app`

#### Verify Documents in Container

Check if documents are accessible inside the container:

```bash
# List files in documents directory
docker exec chitalishta_ai_chat_api ls -la /app/documents/

# Check specific file
docker exec chitalishta_ai_chat_api ls -la "/app/documents/Читалищната мрежа в България – анализ през призмата на данните.docx"
```

### Environment Variables

Create a `.env` file with required variables. Copy `.env.example` to `.env` (if it doesn't exist) and update with your configuration:

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

**Additional Production Configuration:**

For EC2 deployment, you may also need:

```bash
# CORS
CORS_ORIGINS=https://your-frontend-domain.com,http://localhost:5173

# Ports
APP_PORT=8000
POSTGRES_PORT=5432
FRONTEND_PORT=3000
```

### Deployment Steps

1. **Prepare EC2 instance:**
   ```bash
   sudo yum update -y  # Amazon Linux
   sudo yum install -y docker
   sudo service docker start
   sudo usermod -a -G docker ec2-user

   # Install Docker Compose
   sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
   sudo chmod +x /usr/local/bin/docker-compose
   ```

2. **Copy configuration files:**
   ```bash
   # Create project directory
   mkdir -p /home/ec2-user/chitalishta
   cd /home/ec2-user/chitalishta

   # Copy docker-compose.prod.yml and .env
   scp docker-compose.prod.yml ec2-user@your-ec2-ip:/home/ec2-user/chitalishta/
   scp .env ec2-user@your-ec2-ip:/home/ec2-user/chitalishta/

   # If using Option 2 (volume mount), copy documents too
   scp -r documents/ ec2-user@your-ec2-ip:/home/ec2-user/chitalishta/
   ```

3. **Start services:**
   ```bash
   cd /home/ec2-user/chitalishta
   docker-compose -f docker-compose.prod.yml up -d
   ```

4. **Verify deployment:**
   ```bash
   # Check container status
   docker-compose -f docker-compose.prod.yml ps

   # Check logs
   docker-compose -f docker-compose.prod.yml logs -f app

   # Test health endpoint
   curl http://localhost:8000/health
   ```

5. **Initialize database (first time only):**
   ```bash
   # Create users table
   docker exec -it chitalishta_ai_chat_api python scripts/create_users_table.py

   # Create admin user
   docker exec -it chitalishta_ai_chat_api python scripts/create_user.py

   # Create other necessary tables
   docker exec -it chitalishta_ai_chat_api python scripts/init_db_additional_tables.py
   ```

### Updating the Application

```bash
cd /home/ec2-user/chitalishta

# Pull latest image
docker-compose -f docker-compose.prod.yml pull app

# Restart with new image
docker-compose -f docker-compose.prod.yml up -d

# Verify
docker-compose -f docker-compose.prod.yml logs -f app
```

### Security Considerations

1. **Use HTTPS:** Configure a reverse proxy (nginx/Caddy) with SSL certificates
2. **Firewall:** Restrict access to necessary ports only
3. **Environment Variables:** Never commit `.env` files to version control
4. **Database:** Use strong passwords and restrict network access
5. **API Keys:** Rotate regularly and use AWS Secrets Manager for production

### Monitoring

```bash
# View logs
docker-compose -f docker-compose.prod.yml logs -f

# View specific service logs
docker-compose -f docker-compose.prod.yml logs -f app

# Container resource usage
docker stats

# Check disk usage
docker system df
```

### Backup

```bash
# Backup PostgreSQL database
docker exec chitalishta_db_ai_chat pg_dump -U $POSTGRES_USER $POSTGRES_DB > backup_$(date +%Y%m%d).sql

# Backup Chroma vector store
docker cp chitalishta_ai_chat_api:/app/chroma_db ./chroma_backup_$(date +%Y%m%d)
```

