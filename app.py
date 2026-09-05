from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncGenerator, Union
import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from src.config import APP_NAME, DESCRIPTION, HOST, PORT, TRACK_ID, VERSION
from src.models import HealthResponse, StatusResponse
from src.api import router as api_router
from src.database import init_db

DIST_DIR = Path(__file__).parent / "frontend" / "dist"
INDEX_HTML = DIST_DIR / "index.html"


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

# Mount frontend assets if directory exists
if (DIST_DIR / "assets").exists():
    app.mount("/assets", StaticFiles(directory=str(DIST_DIR / "assets")), name="assets")


@app.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    """Health check endpoint."""
    return HealthResponse(status="healthy", app=APP_NAME, track_id=TRACK_ID)


@app.get("/", response_model=None)
async def root(request: Request):
    """Root endpoint: serves frontend UI for browsers and StatusResponse for automated tests/API callers."""
    accept = request.headers.get("accept", "")
    # Browser requests explicitly ask for text/html; TestClient and JSON API requests send */* or application/json
    if "text/html" in accept and not accept.strip() == "*/*" and INDEX_HTML.exists():
        return FileResponse(str(INDEX_HTML))
    return StatusResponse(
        message="RetailIQ is running",
        status="ok",
        app=APP_NAME,
        track=TRACK_ID,
        version=VERSION,
    )


@app.get("/{full_path:path}")
async def serve_spa(full_path: str):
    """Serve frontend SPA for client-side routing, excluding /api, /health, /docs, /openapi.json."""
    if (
        full_path.startswith("api/")
        or full_path == "health"
        or full_path.startswith("docs")
        or full_path.startswith("openapi")
    ):
        raise HTTPException(status_code=404, detail="Not Found")

    target_file = DIST_DIR / full_path
    if target_file.exists() and target_file.is_file():
        return FileResponse(str(target_file))

    if INDEX_HTML.exists():
        return FileResponse(str(INDEX_HTML))

    raise HTTPException(status_code=404, detail="Frontend build not found.")


if __name__ == "__main__":
    uvicorn.run("app:app", host=HOST, port=PORT, reload=False)
