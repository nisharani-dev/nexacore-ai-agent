"""
logging_middleware.py
---------------------
FastAPI middleware for request/response logging with tracing.

Tracks:
- Request ID (correlation ID for distributed tracing)
- Session ID (for user session tracking)
- User info (email, role)
- Request/response times and status
- Error details

Usage in server.py:
    from backend.logging_middleware import LoggingMiddleware
    
    app = FastAPI()
    app.add_middleware(LoggingMiddleware)
"""

import time
import uuid
from typing import Callable

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from backend.logging_config import get_logger

logger = get_logger(__name__)


class LoggingMiddleware(BaseHTTPMiddleware):
    """Middleware to log all HTTP requests/responses with context."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Log request/response with correlation ID."""
        # Generate or get correlation ID
        correlation_id = request.headers.get("X-Correlation-ID", str(uuid.uuid4()))
        
        # Try to extract session ID from query params or headers
        session_id = request.query_params.get("session_id") or request.headers.get(
            "X-Session-ID"
        )
        
        # Try to extract user from auth context (if available)
        user_id = None
        if hasattr(request.state, "user_id"):
            user_id = request.state.user_id

        # Record start time
        start_time = time.time()

        # Store context in request state for endpoint handlers
        request.state.correlation_id = correlation_id
        request.state.session_id = session_id
        request.state.user_id = user_id

        # Log request
        logger.info(
            f"{request.method} {request.url.path}",
            extra={
                "request_id": correlation_id,
                "session_id": session_id,
                "user_id": user_id,
                "method": request.method,
                "path": request.url.path,
                "client": request.client.host if request.client else None,
                "event": "request.start",
            },
        )

        try:
            # Call next middleware/endpoint
            response = await call_next(request)
        except Exception as e:
            # Log error and re-raise
            duration_ms = (time.time() - start_time) * 1000
            logger.error(
                f"Request failed: {request.method} {request.url.path}",
                extra={
                    "request_id": correlation_id,
                    "session_id": session_id,
                    "user_id": user_id,
                    "method": request.method,
                    "path": request.url.path,
                    "duration_ms": duration_ms,
                    "error": str(e),
                    "event": "request.error",
                },
                exc_info=True,
            )
            raise

        # Log response
        duration_ms = (time.time() - start_time) * 1000
        log_level = "warning" if response.status_code >= 400 else "info"
        log_method = getattr(logger, log_level)

        log_method(
            f"{request.method} {request.url.path} → {response.status_code}",
            extra={
                "request_id": correlation_id,
                "session_id": session_id,
                "user_id": user_id,
                "method": request.method,
                "path": request.url.path,
                "status": response.status_code,
                "duration_ms": duration_ms,
                "event": "request.complete",
            },
        )

        # Add correlation ID to response headers
        response.headers["X-Correlation-ID"] = correlation_id

        return response
