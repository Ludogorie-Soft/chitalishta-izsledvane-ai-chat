from fastapi import Depends, FastAPI
from fastapi.openapi.utils import get_openapi
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.admin import router as admin_router
from app.api.chat import router as chat_router
from app.api.chitalishte import router as chitalishte_router
from app.api.indexing import router as indexing_router
from app.api.ingestion import router as ingestion_router
from app.api.vector_store import router as vector_store_router
from app.core.config import settings
from app.core.logging_config import configure_logging  # noqa: F401 - Initialize logging
from app.core.metrics import get_metrics
from app.core.middleware import (
    RateLimitingMiddleware,
    RequestIDMiddleware,
    RequestLoggingMiddleware,
    SwaggerUIAuthMiddleware,
)
from app.db.database import get_db

app = FastAPI(title="Chitalishta RAG System", version="0.1.0")

# Add middleware (order matters: RequestIDMiddleware must come first)
app.add_middleware(RequestIDMiddleware)
app.add_middleware(SwaggerUIAuthMiddleware)  # Swagger UI auth before other middleware
app.add_middleware(RateLimitingMiddleware)  # Rate limiting before logging
app.add_middleware(RequestLoggingMiddleware)

# Register routers
app.include_router(chitalishte_router)
app.include_router(ingestion_router)
app.include_router(indexing_router)
app.include_router(vector_store_router)
app.include_router(chat_router)
app.include_router(admin_router)


def custom_openapi():
    """Custom OpenAPI schema with security schemes and organized tags."""
    if app.openapi_schema:
        return app.openapi_schema

    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description="RAG system for Bulgarian Chitalishta research data",
        routes=app.routes,
    )

    # Define security schemes
    # Note: Actual implementation of these schemes will be done in Step 8.3
    openapi_schema["components"]["securitySchemes"] = {
        "ApplicationAuth": {
            "type": "apiKey",
            "name": "X-API-Key",
            "in": "header",
            "description": "API key for application authentication (Public API endpoints)",
        },
        "BearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
            "description": "JWT token authentication (Admin API and Setup API endpoints)",
        },
    }

    # Organize tags with descriptions
    openapi_schema["tags"] = [
        {
            "name": "Public API",
            "description": "Public API endpoints for chat functionality. Requires application authentication (API key). Restricted to authorized React applications only.",
        },
        {
            "name": "Admin API",
            "description": "Administrator endpoints for viewing chat logs and managing conversations. Requires JWT token authentication.",
        },
        {
            "name": "Setup API",
            "description": "Setup and maintenance endpoints for document ingestion, indexing, and vector store management. Requires JWT token authentication.",
        },
        {
            "name": "System API",
            "description": "System endpoints for Chitalishte data access, health checks, and metrics. No authentication required.",
        },
    ]

    # Note: Security requirements per endpoint will be added in Step 8.3
    # For now, we just define the security schemes

    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = custom_openapi


@app.on_event("startup")
async def startup_event():
    """Verify configuration is loaded on startup."""
    # Configuration is loaded via settings object
    pass


@app.get("/health", tags=["System API"])
async def health_check():
    """Health check endpoint."""
    return {"status": "ok"}


@app.get("/db/ping", tags=["System API"])
async def db_ping(db: Session = Depends(get_db)):
    """Test database connectivity."""
    try:
        # Execute a simple query to test connection
        result = db.execute(text("SELECT 1"))
        result.scalar()
        return {"status": "success", "message": "Database connection successful"}
    except Exception as e:
        return {"status": "error", "message": f"Database connection failed: {str(e)}"}


@app.get("/metrics", tags=["System API"])
async def metrics():
    """Prometheus metrics endpoint."""
    from fastapi import Response
    return Response(content=get_metrics(), media_type="text/plain; version=0.0.4")
