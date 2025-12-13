from fastapi import FastAPI

app = FastAPI(title="Chitalishta RAG System", version="0.1.0")


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok"}


