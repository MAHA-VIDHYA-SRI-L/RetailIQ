"""RetailIQ — Evidence-First Sales & Inventory Copilot FastAPI application."""

from contextlib import asynccontextmanager
from typing import AsyncGenerator
import uvicorn
from fastapi import FastAPI
from src.config import APP_NAME, DESCRIPTION, HOST, PORT, TRACK_ID, VERSION
from src.models import HealthResponse, StatusResponse
from src.api import router as api_router
from src.database import init_db


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Lifecycle manager: ensure database is initialized on application startup."""
    init_db()
    yield


app = FastAPI(
    title=f"{APP_NAME} — {DESCRIPTION}",
    description="Evidence-First AI Copilot for retail sales analytics and inventory intelligence.",
    version=VERSION,
    lifespan=lifespan,
)

# Include modular API router
app.include_router(api_router)


@app.get("/", response_model=StatusResponse)
async def root() -> StatusResponse:
    """Root endpoint confirming that RetailIQ is running."""
    return StatusResponse(
        message="RetailIQ is running",
        status="ok",
        app=APP_NAME,
        track=TRACK_ID,
        version=VERSION,
    )


@app.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    """Health check endpoint."""
    return HealthResponse(status="healthy")


if __name__ == "__main__":
    uvicorn.run("app:app", host=HOST, port=PORT, reload=False)
