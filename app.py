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

from urllib.parse import parse_qs, urlencode
from starlette.types import ASGIApp, Receive, Scope, Send

DIST_DIR = Path(__file__).parent / "frontend" / "dist"
INDEX_HTML = DIST_DIR / "index.html"


class VercelPathMiddleware:
    """Middleware to normalize request paths under Vercel serverless rewrites."""

    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send):
        if scope.get("type") == "http":
            query_string = scope.get("query_string", b"").decode("latin1")
            params = parse_qs(query_string)
            if "__path__" in params:
                req_path = params.pop("__path__", ["/"])[0]
                if not req_path.startswith("/"):
                    req_path = "/" + req_path
                if len(req_path) > 1 and req_path.endswith("/"):
                    req_path = req_path.rstrip("/")
                scope["path"] = req_path
                scope["raw_path"] = req_path.encode("latin1")
                scope["query_string"] = urlencode(params, doseq=True).encode("latin1")
            else:
                headers = dict(scope.get("headers", []))
                matched = headers.get(b"x-matched-path") or headers.get(b"x-forwarded-uri")
                if matched:
                    path_str = matched.decode("latin1").split("?")[0]
                    scope["path"] = path_str
                    scope["raw_path"] = path_str.encode("latin1")
                else:
                    path = scope.get("path", "")
                    if path.startswith("/api/index.py"):
                        scope["path"] = path[len("/api/index.py"):] or "/"
                    elif path.startswith("/api/index"):
                        scope["path"] = path[len("/api/index"):] or "/"
        await self.app(scope, receive, send)


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

app.add_middleware(VercelPathMiddleware)

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
    if full_path in ("api/index.py", "index.py", "api/index"):
        if INDEX_HTML.exists():
            return FileResponse(str(INDEX_HTML))

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
