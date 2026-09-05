"""Vercel Serverless Function entrypoint for RetailIQ.

Exposes the FastAPI application instance `app` and ensures
the local SQLite database is populated in the serverless environment.
"""

import logging
import sys
from pathlib import Path

# Add project root to sys.path so app and src are directly importable
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.database import init_db
from app import app
from fastapi import Request
from fastapi.responses import JSONResponse

@app.middleware("http")
async def debug_middleware(request: Request, call_next):
    if request.query_params.get("debug") == "1":
        return JSONResponse({
            "url": str(request.url),
            "path": request.url.path,
            "scope_path": request.scope.get("path"),
            "headers": dict(request.headers),
        })
    return await call_next(request)

# Warm up / initialize the database for serverless invocations
try:
    init_db()
except Exception as exc:
    logging.error("Failed to initialize database during cold start: %s", exc)
