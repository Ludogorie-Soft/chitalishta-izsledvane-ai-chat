from fastapi import Depends, FastAPI
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.chitalishte import router as chitalishte_router
from app.core.config import settings
from app.db.database import get_db

app = FastAPI(title="Chitalishta RAG System", version="0.1.0")

# Register routers
app.include_router(chitalishte_router)


@app.on_event("startup")
async def startup_event():
    """Verify configuration is loaded on startup."""
    # Configuration is loaded via settings object
    pass


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok"}


@app.get("/db/ping")
async def db_ping(db: Session = Depends(get_db)):
    """Test database connectivity."""
    try:
        # Execute a simple query to test connection
        result = db.execute(text("SELECT 1"))
        result.scalar()
        return {"status": "success", "message": "Database connection successful"}
    except Exception as e:
        return {"status": "error", "message": f"Database connection failed: {str(e)}"}
