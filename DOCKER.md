# Docker Deployment Guide

This guide explains how to build and run the Chitalishta RAG System using Docker.

## Prerequisites

- Docker and Docker Compose installed
- Environment variables configured (see `.env.example` file)

## Two Docker Compose Files

This project uses **two separate docker-compose files** for different use cases:

### 1. `docker-compose.dev.yml` - Local Development
- Contains only **external services** (database, test database, optional TGI)
- FastAPI application runs **directly on your host machine** for development
- Allows hot reload, debugging, and direct access to code
- Use when developing locally

### 2. `docker-compose.prod.yml` - Production/Server
- Contains **all services including the FastAPI application**
- Everything runs in Docker containers
- Use for server deployment and production environments

## Quick Start

### Local Development

1. **Start external services (database, etc.):**
   ```bash
   docker-compose -f docker-compose.dev.yml up -d
   ```

2. **Run FastAPI app locally:**
   ```bash
   poetry run uvicorn app.main:app --reload
   ```

3. **Access the API:**
   - API: http://localhost:8000
   - Swagger UI: http://localhost:8000/docs

### Production/Server Deployment

1. **Set environment variables** (see `.env.example`):
   ```bash
   cp .env.example .env
   # Edit .env with your values
   ```

2. **Pull the latest image and start all services:**
   ```bash
   docker-compose -f docker-compose.prod.yml pull  # Pull latest image
   docker-compose -f docker-compose.prod.yml up -d
   ```

   **Note**: The production setup uses a pre-built image from Docker Hub (`ludogoriesoft/chitalishta_ai_chat_api:latest`).
   No build step is required on the server.

3. **Access the API:**
   - API: http://localhost:8000
   - Swagger UI: http://localhost:8000/docs

2. **Check service status:**
   ```bash
   docker-compose ps
   ```

3. **View application logs:**
   ```bash
   docker-compose logs -f app
   ```

4. **Access the API:**
   - API: http://localhost:8000
   - Swagger UI: http://localhost:8000/docs
   - ReDoc: http://localhost:8000/redoc

## Building and Publishing the Docker Image

The production docker-compose file uses a pre-built image from Docker Hub: `ludogoriesoft/chitalishta_ai_chat_api:latest`

### Build and Push to Docker Hub

**Important**: If building on Apple Silicon (M1/M2/M3 Mac) for deployment on Linux servers (like AWS EC2), you need to build for the `linux/amd64` platform.

#### Option 1: Build for Linux/AMD64 (Recommended for EC2/AWS)

1. **Build the image for linux/amd64 platform:**
   ```bash
   docker build --platform linux/amd64 -t ludogoriesoft/chitalishta_ai_chat_api:latest .
   ```

2. **Tag for specific version (optional):**
   ```bash
   docker tag ludogoriesoft/chitalishta_ai_chat_api:latest ludogoriesoft/chitalishta_ai_chat_api:v1.0.0
   ```

3. **Login to Docker Hub:**
   ```bash
   docker login
   ```

4. **Push to Docker Hub:**
   ```bash
   # Push latest
   docker push ludogoriesoft/chitalishta_ai_chat_api:latest

   # Push versioned tag (optional)
   docker push ludogoriesoft/chitalishta_ai_chat_api:v1.0.0
   ```

#### Option 2: Build Multi-Architecture Image (Supports both ARM64 and AMD64)

1. **Set up Docker Buildx (if not already set up):**
   ```bash
   docker buildx create --use --name multiarch-builder
   docker buildx inspect --bootstrap
   ```

2. **Build and push multi-architecture image:**
   ```bash
   docker buildx build \
     --platform linux/amd64,linux/arm64 \
     -t ludogoriesoft/chitalishta_ai_chat_api:latest \
     -t ludogoriesoft/chitalishta_ai_chat_api:v1.0.0 \
     --push \
     .
   ```

   This will build for both architectures and push them to Docker Hub in a single command.

### Using a Specific Version

To use a specific version in production, update `docker-compose.prod.yml`:

```yaml
services:
  app:
    image: ludogoriesoft/chitalishta_ai_chat_api:v1.0.0  # Use specific version
```

Or set via environment variable:
```bash
export IMAGE_TAG=v1.0.0
docker-compose -f docker-compose.prod.yml up -d
```

Then update the docker-compose file to use `${IMAGE_TAG:-latest}`.

### Building Locally for Testing

If you need to build locally for testing:

**For local development (matches your machine's architecture):**
```bash
docker build -t ludogoriesoft/chitalishta_ai_chat_api:latest .
```

**For testing EC2 compatibility (linux/amd64):**
```bash
docker build --platform linux/amd64 -t ludogoriesoft/chitalishta_ai_chat_api:latest .
```

## Environment Configuration

The application uses environment variables for configuration. Copy `.env.example` to `.env` and fill in your values.

### Database Configuration

For **production** (`docker-compose.prod.yml`), you can configure the database in two ways:

**Option 1: Individual components (recommended)**
```bash
POSTGRES_USER=myuser
POSTGRES_PASSWORD=mypassword
POSTGRES_DB=mydatabase
```
The `DATABASE_URL` will be automatically constructed as:
`postgresql://myuser:mypassword@db:5432/mydatabase`

**Option 2: Full connection string**
```bash
DATABASE_URL=postgresql://myuser:mypassword@db:5432/mydatabase
```

### Required Environment Variables

- **Production**: `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB` (or `DATABASE_URL`)
- `OPENAI_API_KEY`: Required if using OpenAI for embeddings/LLM

### Optional Environment Variables

See `.env.example` and `app/core/config.py` for the complete list of configuration options.

## Docker Compose Services

### `docker-compose.dev.yml` Services

#### `db` - PostgreSQL Database
- Port: 5434 (host, configurable via `POSTGRES_PORT`) → 5432 (container)
- Database: Configurable via `POSTGRES_DB` (default: `chitalishta_db`)
- Credentials: Configurable via `POSTGRES_USER` and `POSTGRES_PASSWORD`

#### `test_db` - Test Database
- Port: 5435 (host, configurable via `TEST_POSTGRES_PORT`) → 5432 (container)
- Database: Configurable via `TEST_POSTGRES_DB` (default: `chitalishta_test_db`)
- Used for running tests

### `docker-compose.prod.yml` Services

#### `app` - FastAPI Application
- Port: 8000 (configurable via `APP_PORT`)
- Depends on: `db`
- Volumes:
  - `chroma_db_data`: Persists Chroma vector store data
  - `./documents`: Mounts documents directory (read-only)
- Environment: All configuration via environment variables

#### `db` - PostgreSQL Database
- Port: 5432 (configurable via `POSTGRES_PORT`, default: 5432)
- Database: Configurable via `POSTGRES_DB`
- Credentials: Configurable via `POSTGRES_USER` and `POSTGRES_PASSWORD`

## Development

### Local Development Workflow

1. **Start external services:**
   ```bash
   docker-compose -f docker-compose.dev.yml up -d
   ```

2. **Run FastAPI app with hot reload:**
   ```bash
   poetry run uvicorn app.main:app --reload
   ```

3. **Run tests:**
   ```bash
   poetry run pytest
   ```

### Running Tests in Production Container

If you need to run tests inside the production container:

```bash
# Run tests
docker-compose -f docker-compose.prod.yml exec app poetry run pytest

# Run specific test file
docker-compose -f docker-compose.prod.yml exec app poetry run pytest tests/test_chat_endpoint.py
```

## Troubleshooting

### Container won't start

1. **Check logs:**
   ```bash
   # Production
   docker-compose -f docker-compose.prod.yml logs app

   # Development (database)
   docker-compose -f docker-compose.dev.yml logs db
   ```

2. **Verify database is healthy:**
   ```bash
   # Production
   docker-compose -f docker-compose.prod.yml ps db

   # Development
   docker-compose -f docker-compose.dev.yml ps db
   ```

3. **Check environment variables:**
   ```bash
   # Production
   docker-compose -f docker-compose.prod.yml exec app env | grep -E "(DATABASE|OPENAI|HUGGING)"
   ```

### Database connection issues

**Production:**
- Ensure the `db` service is healthy: `docker-compose -f docker-compose.prod.yml ps db`
- Check environment variables: `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`
- Verify `DATABASE_URL` is correctly constructed or set directly

**Development:**
- Ensure the `db` service is running: `docker-compose -f docker-compose.dev.yml ps db`
- Check your local `.env` file has correct `DATABASE_URL`:
  ```bash
  DATABASE_URL=postgresql://root:root@localhost:5434/chitalishta_db
  ```

### Chroma DB persistence

Chroma DB data is persisted in the `chroma_db_data` Docker volume. To reset:

```bash
docker-compose down -v  # Removes volumes
docker-compose up -d
```

### Rebuilding after code changes

```bash
docker-compose build app
docker-compose up -d app
```

## Production Considerations

1. **Security:**
   - Change default database credentials
   - Use secrets management for API keys
   - Run as non-root user (already configured)

2. **Performance:**
   - Adjust resource limits in `docker-compose.yml`
   - Use production-grade WSGI server (e.g., Gunicorn with Uvicorn workers)

3. **Monitoring:**
   - Health checks are configured
   - Add logging aggregation
   - Set up metrics collection

4. **Scaling:**
   - Use Docker Swarm or Kubernetes for multi-container deployment
   - Consider separate containers for different services

## Cleanup

```bash
# Stop all services (production)
docker-compose -f docker-compose.prod.yml down

# Stop all services (development)
docker-compose -f docker-compose.dev.yml down

# Stop and remove volumes (⚠️ deletes data)
docker-compose -f docker-compose.prod.yml down -v
docker-compose -f docker-compose.dev.yml down -v

# Remove images
docker-compose -f docker-compose.prod.yml down --rmi all
```

