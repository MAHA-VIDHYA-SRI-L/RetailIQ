"""Vercel Serverless Function entrypoint for RetailIQ.

Exposes the FastAPI application instance `app` and ensures
the local SQLite database is populated and ASGI routing works correctly
behind Vercel serverless rewrites.
"""

import logging
import sys
from pathlib import Path

# Add project root to sys.path so app and src are directly importable
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.database import init_db
from app import app as fastapi_app

# Warm up / initialize the database for serverless invocations
try:
    init_db()
except Exception as exc:
    logging.error("Failed to initialize database during cold start: %s", exc)


from urllib.parse import parse_qs, urlencode


class VercelPathCorrectionMiddleware:
    """Corrects ASGI scope path when running behind Vercel serverless rewrites."""

    def __init__(self, asgi_app):
        self.asgi_app = asgi_app

    def __getattr__(self, name):
        return getattr(self.asgi_app, name)

    async def __call__(self, scope, receive, send):
        if scope.get("type") == "http":
            query_string = scope.get("query_string", b"").decode("latin1")
            params = parse_qs(query_string)

            if "__path__" in params:
                req_path = params.pop("__path__", ["/"])[0]
                if not req_path.startswith("/"):
                    req_path = "/" + req_path
                # Clean up any trailing / or duplicate slashes while preserving root /
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
                    if path in ("/api/index.py", "/api/index", "/api"):
                        scope["path"] = "/"
                    elif path.startswith("/api/index.py/"):
                        scope["path"] = path[len("/api/index.py"):]
                    elif path.startswith("/api/index/"):
                        scope["path"] = path[len("/api/index"):]

        await self.asgi_app(scope, receive, send)


app = VercelPathCorrectionMiddleware(fastapi_app)
