from fastapi import FastAPI

from app.core.config import settings

app = FastAPI(title="Chitalishta RAG System", version="0.1.0")


@app.on_event("startup")
async def startup_event():
    """Verify configuration is loaded on startup."""
    # Configuration is loaded via settings object
    # DATABASE_URL will be used in Step 1.3
    pass


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok"}


