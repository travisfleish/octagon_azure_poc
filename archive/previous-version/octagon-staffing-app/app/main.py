from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import Any, Callable

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddlOkeware
from dotenv import load_dotenv

from .config import get_settings
from .api.health import router as health_router
from .api.sow_processing import router as sow_router
from .api.debug import router as debug_router
from .utils.azure_auth import configure_structured_logging

# .env file is now loaded automatically by Pydantic BaseSettings


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware that logs basic request/response info in structured JSON."""

    async def dispatch(self, request: Request, call_next: Callable[[Request], Any]) -> Response:
        start_time = time.time()
        response: Response = None
        try:
            response = await call_next(request)
        except Exception as e:
            # Log the exception
            process_time_ms = int((time.time() - start_time) * 1000)
            log = {
                "message": "http_request_error",
                "method": request.method,
                "path": request.url.path,
                "status_code": 500,
                "duration_ms": process_time_ms,
                "error": str(e)
            }
            logging.getLogger("app").error(json.dumps(log))
            raise
        finally:
            # Only log if we have a response
            if response is not None:
                process_time_ms = int((time.time() - start_time) * 1000)
                log = {
                    "message": "http_request",
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": getattr(response, "status_code", 0),
                    "duration_ms": process_time_ms,
                }
                logging.getLogger("app").info(json.dumps(log))
        return response


def create_app() -> FastAPI:
    settings = get_settings()
    configure_structured_logging(settings.log_level)

    app = FastAPI(title="Octagon Staffing Plan Generator", version="0.1.0")

    # CORS
    allowed = [o.strip() for o in settings.cors_allow_origins.split(",") if o.strip()]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed or ["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Logging middleware
    app.add_middleware(RequestLoggingMiddleware)

    # Routers
    app.include_router(health_router)
    app.include_router(sow_router)
    app.include_router(debug_router)

    return app


app = create_app()



