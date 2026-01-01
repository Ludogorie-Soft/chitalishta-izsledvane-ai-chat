# Multi-stage build for Chitalishta RAG System
FROM python:3.13-slim AS builder

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry
RUN pip install --no-cache-dir poetry

# Configure Poetry to install to system Python
ENV POETRY_NO_INTERACTION=1 \
    POETRY_VENV_IN_PROJECT=0 \
    POETRY_CACHE_DIR=/tmp/poetry_cache

# Set working directory
WORKDIR /app

# Copy Poetry files
COPY pyproject.toml poetry.lock* ./

# Install PyTorch CPU-only first (before other packages that depend on it)
# This prevents installing the full PyTorch with CUDA support (~1.5GB savings)
# Only install torch - torchvision/torchaudio will be installed if needed by dependencies
RUN pip install --no-cache-dir --index-url https://download.pytorch.org/whl/cpu torch

# Configure Poetry and install dependencies
RUN poetry config virtualenvs.create false && \
    poetry install --only=main --no-interaction && \
    # Clean up pip cache
    pip cache purge && \
    # Remove Python cache files and .pyc files
    find /usr/local/lib/python3.13/site-packages -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true && \
    find /usr/local/lib/python3.13/site-packages -type f -name "*.pyc" -delete 2>/dev/null || true && \
    find /usr/local/lib/python3.13/site-packages -type f -name "*.pyo" -delete 2>/dev/null || true && \
    # Remove test files and documentation from packages (safe to remove)
    find /usr/local/lib/python3.13/site-packages -type d -name "tests" -exec rm -rf {} + 2>/dev/null || true && \
    find /usr/local/lib/python3.13/site-packages -type d -name "test" -exec rm -rf {} + 2>/dev/null || true && \
    find /usr/local/lib/python3.13/site-packages -type d -name "docs" -exec rm -rf {} + 2>/dev/null || true && \
    find /usr/local/lib/python3.13/site-packages -type d -name "*.egg" -exec rm -rf {} + 2>/dev/null || true && \
    rm -rf $POETRY_CACHE_DIR

# Production stage
FROM python:3.13-slim

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd -m -u 1000 appuser && \
    mkdir -p /app /app/chroma_db /app/documents && \
    chown -R appuser:appuser /app

# Set working directory
WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.13/site-packages /usr/local/lib/python3.13/site-packages

# Copy installed scripts/binaries (like uvicorn) from builder
# Poetry/pip installs scripts to /usr/local/bin when installing to system Python
COPY --from=builder /usr/local/bin/ /usr/local/bin/

# Copy application code
COPY --chown=appuser:appuser . .

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

# Run the application
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

