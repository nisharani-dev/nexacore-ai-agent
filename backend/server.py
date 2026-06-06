"""
server.py
──────────
FastAPI application — HTTP boundary of the Ramp backend.

Endpoints:
  POST /chat    → main onboarding query
  GET  /health  → liveness probe
"""

import logging
import json
import uuid
import os
import asyncio
from pathlib import Path
from contextlib import asynccontextmanager
from time import perf_counter
from datetime import datetime, timezone

import jwt

from fastapi import Depends, FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import PlainTextResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from backend.logging_middleware import LoggingMiddleware
from backend.websocket_manager import WebSocketManager, WebSocketMessage

from backend.interfaces import AgentResponse, ConsentRequest, OidcCallbackRequest, OnboardingRequest, SessionRequest
from backend.agent.agent import get_agent
from backend.auth import authenticate_request, create_session
from backend.auth_oidc import OIDCFactory
from backend.context.context_builder import ContextBuilder
from backend.db import AppDatabase
from backend.interfaces import UserProfile
from backend.memory.retriever import apply_demo_mode, fetch_person1_demo_memories
from backend.memory.hindsight_client import HindsightClient
from backend.memory.seed_data import ensure_demo_data
from backend.memory.seed_employees import ensure_employee_data
from backend.memory.ensure_ingestion import ensure_ingestion_data
from backend.analytics import get_analytics_instance
from backend.analytics_summary import build_analytics_summary
from backend.cache import cache
from backend.compliance import ComplianceManager
from backend.db_migrate import run_migrations
from backend.interfaces import FeedbackRequest
from backend.rbac import Permission, get_rbac
from backend.rbac_deps import require_permission
from backend.settings import integrations_mode, ticket_backend
from backend.observability import metrics
from backend.settings import allowed_origins, app_env
from backend.runtime_paths import reminder_store_path, ticket_store_path

logger = logging.getLogger(__name__)
REMINDER_LOG = reminder_store_path()
TICKET_LOG = ticket_store_path()

_db: AppDatabase | None = None


def get_db() -> AppDatabase:
    """Lazy DB singleton — must not init at import time (gunicorn worker race)."""
    global _db
    if _db is None:
        _db = AppDatabase.get()
    return _db


MEMORY_CACHE_TTL = int(os.getenv("MEMORY_CACHE_TTL", "120"))
SESSION_CACHE_TTL = int(os.getenv("SESSION_CACHE_TTL", "300"))


def _invalidate_memory_cache() -> None:
    cache.invalidate_pattern("memories:*")


def _cached_session(session_id: str) -> dict | None:
    key = f"session:{session_id}"
    cached = cache.get(key)
    if cached is not None:
        return cached
    session = get_db().get_session(session_id)
    if session is not None:
        cache.set(key, session, SESSION_CACHE_TTL)
    return session


# Rate limiting
limiter = Limiter(key_func=get_remote_address)

# WebSocket manager
ws_manager = WebSocketManager()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Ramp backend starting up...")
    run_migrations()
    get_db()  # init pool after migrations (never at import time)
    logger.info("Cache backend: %s", cache.backend_name())
    ensure_demo_data()
    ensure_employee_data()
    ingestion = ensure_ingestion_data()
    logger.info("Ingestion startup complete: %s", ingestion)
    get_agent()  # warm up singleton, validates GROQ_API_KEY early
    logger.info("Agent ready")
    yield
    logger.info("Ramp backend shutting down")


app = FastAPI(
    title="Ramp — Onboarding Agent API",
    description="""
AI-powered onboarding assistant with integrated memory system and LLM backend.

## Features
- **Conversational Agent**: Groq-backed LLM for natural onboarding guidance
- **Memory Retrieval**: Context-aware recommendations from 270+ seed memories
- **Session Management**: Track onboarding progress per employee
- **Ticket & Reminders**: Create action items and schedule follow-ups
- **Audit Trail**: Full event logging for compliance
- **Real-time Updates**: WebSocket support for live session updates

## Authentication
- **API Key**: Set `APP_API_KEY` environment variable
- **Public Endpoints**: `/health`, `/ready`, `/metrics` (no auth required)
- **Protected Endpoints**: All data/action endpoints require `Authorization: Bearer {token}` if `AUTH_REQUIRED=true`

## Getting Started
1. Create a session: `POST /sessions`
2. Send a message: `POST /chat`
3. Query memories: `GET /memories`
4. Connect WebSocket: `WS /ws?session_id=...`
5. Create tickets: Agent can call internally via LangChain tools
""",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    openapi_tags=[
        {"name": "health", "description": "Service health and readiness"},
        {"name": "metrics", "description": "Prometheus metrics and statistics"},
        {"name": "authentication", "description": "OIDC/SSO authentication endpoints"},
        {"name": "sessions", "description": "Session lifecycle management"},
        {"name": "chat", "description": "Conversational agent endpoint"},
        {"name": "data", "description": "Query operational data (tickets, reminders, audit)"},
        {"name": "memory", "description": "Query memory and knowledge base"},
        {"name": "websocket", "description": "Real-time WebSocket connections"},
    ],
)

# Add rate limiter to app
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, lambda request, exc: (
    PlainTextResponse("Rate limit exceeded", status_code=429)
))

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins() if app_env() != "development" else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add structured logging middleware
app.add_middleware(LoggingMiddleware)


@app.middleware("http")
async def request_context_middleware(request: Request, call_next):
    request_id = request.headers.get("x-request-id", str(uuid.uuid4()))
    request.state.request_id = request_id
    request.state.auth = authenticate_request(request)
    start = perf_counter()
    metrics.inc("http_requests_started_total", method=request.method, path=request.url.path)
    try:
        response = await call_next(request)
    except Exception:
        metrics.inc("http_requests_failed_total", method=request.method, path=request.url.path)
        logger.exception("Unhandled request failure | request_id=%s | path=%s", request_id, request.url.path)
        raise
    duration_ms = round((perf_counter() - start) * 1000, 2)
    response.headers["x-request-id"] = request_id
    metrics.inc(
        "http_requests_total",
        method=request.method,
        path=request.url.path,
        status=str(response.status_code),
    )
    metrics.inc(
        "http_request_duration_ms_total",
        amount=duration_ms,
        method=request.method,
        path=request.url.path,
    )
    # Record latency histogram
    metrics.observe(
        "http_request_duration_ms",
        duration_ms,
        method=request.method,
        path=request.url.path,
    )
    # Update active request gauges
    metrics.gauge("http_requests_in_flight", max(0, metrics._counters.get("http_requests_started_total", 0) - metrics._counters.get("http_requests_total", 0)))
    logger.info(
        "request complete | request_id=%s | method=%s | path=%s | status=%s | duration_ms=%s",
        request_id,
        request.method,
        request.url.path,
        response.status_code,
        duration_ms,
    )
    return response


@app.get("/openapi.json", include_in_schema=False)
async def openapi():
    """
    OpenAPI schema endpoint.
    
    Returns the OpenAPI 3.0 specification for this API.
    Used by:
    - `/docs` (Swagger UI)
    - `/redoc` (ReDoc documentation)
    - Code generation tools
    - API clients (Postman, etc.)
    """
    return app.openapi()


@app.get("/docs", include_in_schema=False)
async def swagger_docs():
    """
    Swagger UI documentation.
    
    Interactive API explorer with live test capability.
    Visit this endpoint in a browser to explore the API.
    """
    from fastapi.openapi.docs import get_swagger_ui_html
    return get_swagger_ui_html(openapi_url="/openapi.json", title="Ramp API")


@app.get("/redoc", include_in_schema=False)
async def redoc_docs():
    """
    ReDoc documentation.
    
    Clean, static API documentation.
    Visit this endpoint in a browser for formatted docs.
    """
    from fastapi.openapi.docs import get_redoc_html
    return get_redoc_html(openapi_url="/openapi.json", title="Ramp API")


@app.get("/health", tags=["health"])
@limiter.limit("100/minute")
async def health(request: Request):
    """
    Liveness probe for Kubernetes/orchestration.
    
    Returns 200 OK if service is running. Use this for health checks and alerting.
    Does not check dependencies (see `/ready` for full dependency check).
    """
    return {"status": "ok", "service": "ramp-agent", "seeded": True}


@app.get("/ready", tags=["health"])
@limiter.limit("100/minute")
async def ready(request: Request):
    """
    Readiness probe for Kubernetes/orchestration.
    
    Returns 200 OK only if all dependencies are available:
    - GROQ_API_KEY configured
    - Database accessible
    - Memory backend reachable
    
    Returns 503 if any dependency is unavailable.
    """
    groq_key_present = bool(os.getenv("GROQ_API_KEY", "").strip())
    db_health = get_db().healthcheck()
    memory_backend = HindsightClient().backend_summary()
    store_paths = {
        "ticket_store": str(TICKET_LOG),
        "reminder_store": str(REMINDER_LOG),
    }
    return {
        "status": "ready",
        "service": "ramp-agent",
        "groq_api_key_configured": groq_key_present,
        "database": db_health,
        "memory_backend": memory_backend,
        "stores": store_paths,
    }


@app.get("/metrics", response_class=PlainTextResponse, tags=["metrics"])
@limiter.limit("100/minute")
async def metrics_endpoint(request: Request):
    """
    Prometheus metrics endpoint (text format).
    
    Returns metrics in Prometheus text exposition format.
    Metrics include:
    - HTTP request counts and latencies
    - Session creation rates
    - Agent response times
    - Database query metrics
    
    Scrape interval: 15s recommended
    """
    return metrics.render_prometheus()


@app.get("/stats", response_class=PlainTextResponse, tags=["metrics"])
async def stats_endpoint():
    """
    Metrics summary in JSON format.
    
    Returns aggregated statistics including:
    - Histogram percentiles (p50, p95, p99)
    - Counter totals
    - Gauge values
    """
    import json
    return json.dumps(metrics.get_summary(), indent=2)


@app.get("/db-stats", tags=["metrics"])
async def db_stats_endpoint():
    """
    Detailed database statistics.
    
    Returns operational metrics:
    - Row counts per table
    - Status distributions
    - Time-based metrics (sessions created today, events logged)
    """
    return get_db().get_database_stats()


@app.get("/health-detailed", tags=["health"])
async def health_detailed():
    """
    Comprehensive health check with full diagnostics.
    
    Returns detailed status including:
    - All dependencies (Groq, database, memory backend)
    - Database statistics
    - Metrics summary
    
    Use for manual debugging. Returns 200 even if degraded; check `status` field.
    """
    groq_key_present = bool(os.getenv("GROQ_API_KEY", "").strip())
    db_health = get_db().healthcheck()
    memory_backend = HindsightClient().backend_summary()
    db_stats = get_db().get_database_stats()
    
    return {
        "status": "ok",
        "service": "ramp-agent",
        "groq_api_key_configured": groq_key_present,
        "database": db_health,
        "memory_backend": memory_backend,
        "database_stats": db_stats,
        "metrics_summary": metrics.get_summary(),
    }


@app.post("/sessions", tags=["sessions"])
@limiter.limit("30/minute")
async def create_session_endpoint(request: Request, payload: SessionRequest):
    """
    Create a new onboarding session.
    
    Creates a session for a new employee with their context:
    - Name, team, role, employment type
    - Optional metadata (start date, manager, etc.)
    
    Returns: `session_id` to use in subsequent requests
    
    **Example:**
    ```json
    {
        "name": "Alice Johnson",
        "team": "platform",
        "role": "SDE-1",
        "employee_type": "fte"
    }
    ```
    """
    session = create_session(
        user_name=payload.name,
        team_name=payload.team,
        role_title=payload.role,
        employment_type=payload.employee_type,
        metadata=payload.metadata,
    )
    get_db().insert_audit_event(
        event_type="session.created",
        actor=request.state.auth.subject,
        session_id=session["session_id"],
        request_id=request.state.request_id,
        payload=payload.model_dump(),
    )
    metrics.inc("sessions_created_total", employment_type=payload.employee_type, team=payload.team)
    return session


@app.get("/sessions/{session_id}", tags=["sessions"])
@limiter.limit("60/minute")
async def get_session_endpoint(request: Request, session_id: str):
    """
    Retrieve session details.
    
    Returns the full session object including user profile, team context, and metadata.
    """
    session = _cached_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


@app.get("/sessions", tags=["sessions"], dependencies=[Depends(require_permission(Permission.VIEW_AUDIT_LOG))])
async def list_sessions_endpoint():
    """
    List recent sessions.
    
    Returns the 100 most recent sessions ordered by creation time (newest first).
    Useful for monitoring active onboarding sessions.
    """
    return {"sessions": get_db().list_sessions()}


@app.get("/memories", tags=["memory"])
@limiter.limit("60/minute")
async def memories(request: Request, team: str, employee_type: str = "fte", role: str = "", demo_mode: str = "person10"):
    """
    Query contextual memories for an employee profile.
    
    Returns relevant guidance memories based on:
    - Team context
    - Employment type (fte/contractor/intern)
    - Role/level
    - Demo mode (person1 = realistic, person10 = AI persona)
    
    Memories are ranked by relevance to the employee's profile.
    """
    cache_key = f"memories:{team}:{employee_type}:{role}:{demo_mode}"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached
    try:
        builder = ContextBuilder()
        user = UserProfile(
            name="Demo User",
            team_name=team,
            employment_type=employee_type.lower(),
            role_title=role or None,
        )
        ctx = builder.build(user)
        if demo_mode == "person1":
            filtered = fetch_person1_demo_memories()
        else:
            filtered = apply_demo_mode(ctx.memories, demo_mode)
        payload = {"memories": [_ui_memory_shape(memory) for memory in filtered]}
        cache.set(cache_key, payload, MEMORY_CACHE_TTL)
        return payload
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@app.get("/memory/summary", tags=["memory"])
async def memory_summary():
    """
    Get memory system summary.
    
    Returns statistics about the knowledge base:
    - Total records
    - Backend type (local/http)
    - Namespace counts
    """
    summary = HindsightClient().backend_summary()
    metrics.gauge("memory_records_total", summary.get("metadata", {}).get("total", 0))
    return summary


@app.get("/reminders", tags=["data"], dependencies=[Depends(require_permission(Permission.VIEW_REMINDER))])
async def reminders():
    """
    List all pending reminders.
    
    Returns reminders scheduled for employees, useful for:
    - Day-N follow-ups
    - Onboarding milestone checks
    - Access request verifications
    """
    reminders_list = get_db().list_reminders()
    metrics.gauge("reminders_total", len(reminders_list))
    metrics.inc("api_reminders_fetched")
    return {"reminders": reminders_list}


@app.get("/tickets", tags=["data"], dependencies=[Depends(require_permission(Permission.VIEW_TICKET))])
async def tickets():
    """
    List all IT tickets created during onboarding.
    
    Returns tickets for:
    - Access requests (AWS, GitHub, etc.)
    - Equipment provisioning
    - Account setup
    """
    tickets_list = get_db().list_tickets()
    metrics.gauge("tickets_total", len(tickets_list))
    metrics.inc("api_tickets_fetched")
    return {"tickets": tickets_list}


@app.get("/audit", tags=["data"], dependencies=[Depends(require_permission(Permission.VIEW_AUDIT_LOG))])
async def audit():
    """
    Audit event log for compliance and debugging.
    
    Returns chronological event log including:
    - Session creation
    - Chat requests/completions
    - Ticket/reminder operations
    - Configuration changes
    
    Useful for compliance, debugging, and user activity tracking.
    """
    events = get_db().list_audit_events()
    metrics.inc("api_audit_fetched")
    return {"events": events}


@app.post("/demo/reset", tags=["demo"], dependencies=[Depends(require_permission(Permission.SYSTEM_ADMIN))])
async def demo_reset():
    """
    Reset demo data to seed state.
    
    Re-loads seed memories, employee corpus, and doc ingestion.
    Useful for resetting demo environments between presentations.
    """
    from backend.memory.seed_data import seed_demo_data
    from backend.memory.seed_employees import seed_employees

    seed_demo_data(reset=True)
    seed_employees(reset=False)
    ingestion = ensure_ingestion_data()
    _invalidate_memory_cache()
    cache.clear()
    get_db().insert_audit_event(event_type="demo.reset", payload={"reset": True, "ingestion": ingestion})
    return {
        "status": "reset",
        "memories_seeded": True,
        "ingestion": ingestion,
        "integrations_mode": integrations_mode(),
    }


@app.get("/integrations/status", tags=["data"])
async def integrations_status():
    """Return whether Jira/email integrations are in demo or live mode."""
    mode = integrations_mode()
    backend = ticket_backend()
    return {
        "mode": mode,
        "ticket_backend": backend,
        "jira_configured": bool(os.getenv("JIRA_API_TOKEN")),
        "servicenow_configured": bool(
            os.getenv("SERVICENOW_INSTANCE_URL")
            and os.getenv("SERVICENOW_USERNAME")
            and os.getenv("SERVICENOW_PASSWORD")
        ),
        "email_configured": bool(os.getenv("SMTP_HOST") or os.getenv("SENDGRID_API_KEY")),
        "label": "live integrations" if mode == "live" else "mock integrations (demo)",
    }


@app.get("/analytics/summary", tags=["metrics"], dependencies=[Depends(require_permission(Permission.VIEW_METRICS))])
async def analytics_summary():
    """Operational analytics aggregated from audit trail and DB stats."""
    return build_analytics_summary()


@app.get("/compliance/export/{user_name}", tags=["data"], dependencies=[Depends(require_permission(Permission.VIEW_AUDIT_LOG))])
async def compliance_export(user_name: str):
    """GDPR-style data export for a user by name."""
    manager = ComplianceManager()
    export = manager.export_user_data(user_name)
    return export.model_dump()


@app.delete("/compliance/users/{user_name}", tags=["data"], dependencies=[Depends(require_permission(Permission.SYSTEM_ADMIN))])
async def compliance_delete_user(user_name: str):
    """GDPR right-to-erasure for a user."""
    manager = ComplianceManager()
    deleted = manager.delete_user_data(user_name)
    return {"deleted": deleted, "user_name": user_name}


@app.post("/compliance/consent", tags=["data"])
async def compliance_set_consent(request: Request, payload: ConsentRequest):
    """Record user consent for analytics/marketing/cookies."""
    manager = ComplianceManager()
    record = manager.set_consent(
        user_id=payload.user_id or request.state.auth.subject,
        category=payload.category,
        granted=payload.granted,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    return record.model_dump()


@app.get("/compliance/report", tags=["data"], dependencies=[Depends(require_permission(Permission.VIEW_AUDIT_LOG))])
async def compliance_report():
    """Compliance and data-protection summary."""
    manager = ComplianceManager()
    return manager.get_compliance_report()


@app.get("/sessions/{session_id}/messages", tags=["sessions"])
async def session_messages(session_id: str):
    """Chat history for a session."""
    if not _cached_session(session_id):
        raise HTTPException(status_code=404, detail="Session not found")
    return {"session_id": session_id, "messages": get_db().list_chat_messages(session_id)}


@app.post("/feedback", tags=["chat"])
@limiter.limit("30/minute")
async def submit_feedback(request: Request, payload: FeedbackRequest):
    """Record user feedback and optionally write a refined memory."""
    from backend.interfaces import MemoryItem
    from backend.memory.hindsight_client import HindsightClient

    record = get_db().insert_feedback(
        session_id=payload.session_id or "",
        helpful=payload.helpful,
        comment=payload.comment,
        team_name=payload.team,
        query_text=payload.query,
    )
    if payload.helpful and payload.team and payload.query:
        _invalidate_memory_cache()
        HindsightClient().write(
            MemoryItem(
                content=f"Verified answer for '{payload.query}': {payload.comment or 'marked helpful'}",
                tags=[f"team:{payload.team}", "type:access", "source:feedback"],
                level="team",
                source="feedback",
                relevance_score=0.95,
            )
        )
    get_db().insert_audit_event(
        event_type="feedback.submitted",
        session_id=payload.session_id or "",
        payload={"helpful": payload.helpful, "team": payload.team},
    )
    return record


@app.get("/reminders/{reminder_id}/ics", tags=["data"])
async def reminder_ics(reminder_id: str):
    """Download a calendar invite for a scheduled reminder."""
    reminder = get_db().get_reminder(reminder_id)
    if not reminder:
        raise HTTPException(status_code=404, detail="Reminder not found")
    ics = (
        "BEGIN:VCALENDAR\nVERSION:2.0\nBEGIN:VEVENT\n"
        f"SUMMARY:Onboarding reminder\nDESCRIPTION:{reminder['message']}\n"
        f"DTSTART:{reminder['scheduled_for'].replace('-', '').replace(':', '')[:15]}Z\n"
        "END:VEVENT\nEND:VCALENDAR"
    )
    return PlainTextResponse(ics, media_type="text/calendar")


# ========================================
# OIDC/SSO Authentication Endpoints
# ========================================

@app.get("/auth/oidc/info", tags=["authentication"])
async def oidc_info():
    """
    Get OIDC provider configuration status.
    
    Returns information about the configured OIDC provider (if any).
    Useful for debugging SSO setup.
    """
    provider_type = os.getenv("OIDC_PROVIDER")
    if not provider_type:
        return {
            "enabled": False,
            "message": "OIDC authentication not configured. Set OIDC_PROVIDER environment variable."
        }
    
    return {
        "enabled": True,
        "provider": provider_type,
        "message": f"OIDC provider configured: {provider_type}"
    }


@app.get("/auth/oidc/login", tags=["authentication"])
async def oidc_login(redirect_uri: str, state: str = None):
    """
    Initiate OIDC login flow.
    
    Generates the authorization URL to redirect users to the OIDC provider.
    
    **Parameters:**
    - `redirect_uri`: The callback URL where the provider will send the authorization code
    - `state`: Optional CSRF protection token
    
    **Returns:**
    - `authorization_url`: URL to redirect the user to for login
    
    **Example:**
    ```
    GET /auth/oidc/login?redirect_uri=http://localhost:3000/callback&state=random-string
    ```
    """
    try:
        provider = OIDCFactory.create_from_env()
        if not provider:
            raise HTTPException(
                status_code=501,
                detail="OIDC not configured. Set OIDC_PROVIDER environment variable."
            )
        
        auth_url = await provider.get_authorization_url(
            redirect_uri=redirect_uri,
            state=state
        )
        
        get_db().insert_audit_event(
            event_type="auth.oidc.login_initiated",
            payload={"provider": os.getenv("OIDC_PROVIDER")}
        )
        
        return {"authorization_url": auth_url}
    
    except ValueError as e:
        logger.error(f"OIDC configuration error: {e}")
        raise HTTPException(status_code=500, detail=f"OIDC configuration error: {str(e)}")
    except Exception as e:
        logger.exception("Error generating OIDC authorization URL")
        raise HTTPException(status_code=500, detail=f"Failed to initiate OIDC login: {str(e)}")


@app.post("/auth/oidc/callback", tags=["authentication"])
async def oidc_callback(payload: OidcCallbackRequest):
    """
    Handle OIDC callback after user authentication.
    
    Exchanges the authorization code for tokens and verifies the user.
    
    **Parameters:**
    - `code`: Authorization code from OIDC provider
    - `redirect_uri`: Same redirect URI used in login request
    - `state`: State parameter for CSRF verification (optional)
    
    **Returns:**
    - `access_token`: Access token from provider
    - `id_token`: ID token with user information
    - `user_info`: Decoded user information
    - `session_id`: New session ID for the authenticated user
    
    **Example:**
    ```json
    POST /auth/oidc/callback
    {
        "code": "auth-code-from-provider",
        "redirect_uri": "http://localhost:3000/callback"
    }
    ```
    """
    try:
        provider = OIDCFactory.create_from_env()
        if not provider:
            raise HTTPException(
                status_code=501,
                detail="OIDC not configured"
            )
        
        # Exchange code for tokens
        tokens = await provider.get_token(code=payload.code, redirect_uri=payload.redirect_uri)
        
        # Verify and decode ID token
        id_token = tokens.get("id_token")
        if not id_token:
            raise HTTPException(status_code=400, detail="No ID token in response")
        
        user_info = await provider.verify_token(id_token)
        subject = user_info.email or user_info.sub
        get_rbac().sync_oidc_roles(
            subject,
            groups=user_info.groups or [],
            roles=user_info.roles or [],
        )

        session = create_session(
            user_name=user_info.name or user_info.email or user_info.sub,
            team_name="default",
            role_title="",
            employment_type="fte",
            auth_subject=subject,
            metadata={
                "auth_method": "oidc",
                "provider": os.getenv("OIDC_PROVIDER"),
                "email": user_info.email,
                "sub": user_info.sub,
            },
        )
        session_id = session["session_id"]
        
        get_db().insert_audit_event(
            event_type="auth.oidc.login_completed",
            actor=subject,
            session_id=session_id,
            payload={
                "provider": os.getenv("OIDC_PROVIDER"),
                "email": user_info.email,
                "name": user_info.name,
            }
        )
        
        metrics.inc("oidc_logins_total", provider=os.getenv("OIDC_PROVIDER", "unknown"))
        
        return {
            "access_token": tokens.get("access_token"),
            "id_token": id_token,
            "token_type": tokens.get("token_type", "Bearer"),
            "expires_in": tokens.get("expires_in"),
            "user_info": user_info.model_dump(),
            "session_id": session_id,
        }
    
    except ValueError as e:
        logger.error(f"OIDC token exchange error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("Error processing OIDC callback")
        raise HTTPException(status_code=500, detail=f"OIDC callback failed: {str(e)}")


@app.post("/auth/oidc/verify", tags=["authentication"])
async def oidc_verify_token(token: str):
    """
    Verify an OIDC ID token.
    
    Validates a token received from the OIDC provider and returns user information.
    
    **Parameters:**
    - `token`: ID token to verify
    
    **Returns:**
    - `valid`: Boolean indicating if token is valid
    - `user_info`: Decoded user information (if valid)
    
    **Example:**
    ```json
    POST /auth/oidc/verify
    {
        "token": "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9..."
    }
    ```
    """
    try:
        provider = OIDCFactory.create_from_env()
        if not provider:
            raise HTTPException(
                status_code=501,
                detail="OIDC not configured"
            )
        
        user_info = await provider.verify_token(token)
        
        return {
            "valid": True,
            "user_info": user_info.model_dump()
        }
    
    except jwt.InvalidTokenError as e:
        logger.warning(f"Invalid OIDC token: {e}")
        return {
            "valid": False,
            "error": str(e)
        }
    except Exception as e:
        logger.exception("Error verifying OIDC token")
        raise HTTPException(status_code=500, detail=f"Token verification failed: {str(e)}")


@app.post("/chat", response_model=AgentResponse, tags=["chat"])
@limiter.limit("20/minute")
async def chat(request: Request, payload: OnboardingRequest) -> AgentResponse:
    """
    Main onboarding chat endpoint (AI-powered).
    
    Processes natural language queries about onboarding with context-aware guidance.
    
    **Flow:**
    1. Creates/updates session with employee context
    2. Retrieves relevant memories from knowledge base
    3. Sends to Groq LLM for response generation
    4. Returns guidance + suggested actions (tickets/reminders)
    5. Logs to audit trail for compliance
    
    **Example request:**
    ```json
    {
        "name": "Priya",
        "team": "platform",
        "role": "SDE-1",
        "employee_type": "fte",
        "query": "What should I do on Day 1?"
    }
    ```
    
    **Response includes:**
    - `guidance`: Natural language response
    - `memories_used`: Knowledge base citations
    - `suggested_actions`: Recommended next steps
    - `new_memories_written`: Learned facts
    """
    if not payload.session_id:
        payload.session_id = str(uuid.uuid4())

    request.state.session_id = payload.session_id

    try:
        cache.delete(f"session:{payload.session_id}")
        get_db().upsert_session(
            session_id=payload.session_id,
            user_name=payload.name,
            team_name=payload.team,
            role_title=payload.role,
            employment_type=payload.employee_type,
            auth_subject=request.state.auth.subject,
            metadata={"demo_mode": payload.demo_mode or "person10"},
        )
        get_db().insert_audit_event(
            event_type="chat.requested",
            actor=request.state.auth.subject,
            session_id=payload.session_id,
            payload={
                "name": payload.name,
                "team": payload.team,
                "role": payload.role,
                "employee_type": payload.employee_type,
                "query": payload.query,
                "demo_mode": payload.demo_mode,
            },
        )
        metrics.inc("chat_requests_total", team=payload.team, employment_type=payload.employee_type)
        get_db().insert_chat_message(
            session_id=payload.session_id,
            role="user",
            content=payload.query,
            metadata={"team": payload.team, "demo_mode": payload.demo_mode},
        )
        agent = get_agent()
        response = await agent.run(payload)
        get_db().insert_chat_message(
            session_id=payload.session_id,
            role="agent",
            content=response.message,
            metadata={
                "suggested_actions": response.suggested_actions,
                "tools_used": response.tools_used,
                "memory_count": len(response.memories_used),
            },
        )
        get_db().insert_audit_event(
            event_type="chat.completed",
            actor=request.state.auth.subject,
            session_id=payload.session_id,
            payload={
                "memories_used": len(response.memories_used),
                "new_memories_written": len(response.new_memories_written),
                "suggested_actions": response.suggested_actions,
            },
        )
        if response.new_memories_written:
            _invalidate_memory_cache()
            await ws_manager.broadcast(
                payload.session_id,
                WebSocketMessage(
                    id=str(uuid.uuid4()),
                    type="memory_update",
                    timestamp=datetime.now(timezone.utc).isoformat(),
                    data={
                        "new_memories": [
                            _ui_memory_shape(memory) for memory in response.new_memories_written
                        ],
                    },
                    session_id=payload.session_id,
                ),
            )
        get_analytics_instance().track(
            user_id=request.state.auth.subject,
            event="chat.completed",
            properties={
                "team": payload.team,
                "session_id": payload.session_id,
                "memories_used": len(response.memories_used),
            },
        )
        return response
    except ValueError as e:
        logger.warning("Validation error: %s", e)
        raise HTTPException(status_code=422, detail=str(e))
    except EnvironmentError as e:
        logger.error("Configuration error: %s", e)
        raise HTTPException(status_code=500, detail=f"Server configuration error: {e}")
    except Exception as e:
        logger.exception("Unexpected error processing chat request")
        raise HTTPException(status_code=500, detail=f"Agent error: {str(e)}")


@app.post("/chat/stream", tags=["chat"])
@limiter.limit("20/minute")
async def chat_stream(request: Request, payload: OnboardingRequest):
    """Stream agent reply as Server-Sent Events (word chunks)."""
    if not payload.session_id:
        payload.session_id = str(uuid.uuid4())
    request.state.session_id = payload.session_id

    async def event_generator():
        agent = get_agent()
        response = await agent.run(payload)
        words = response.message.split(" ")
        for index, word in enumerate(words):
            chunk = word if index == 0 else f" {word}"
            yield f"data: {json.dumps({'type': 'token', 'text': chunk})}\n\n"
            await asyncio.sleep(0.03)
        yield f"data: {json.dumps({'type': 'done', 'response': response.model_dump()})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


def _ui_memory_shape(memory) -> dict:
    return {
        "scope": _scope_from_memory(memory.level),
        "type": _type_from_memory(memory),
        "text": memory.content,
    }


def _scope_from_memory(level: str) -> str:
    if level in {"company"}:
        return "company"
    if level in {"division", "org"}:
        return "org"
    if level in {"team", "sub_team", "exception"}:
        return "team"
    return "role"


def _type_from_memory(memory) -> str:
    lower = memory.content.lower()
    if "known blocker" in lower or "blocker" in lower:
        return "blocker"
    if memory.level == "exception" or "exception:" in ",".join(memory.tags):
        return "exception"
    if "slack" in lower or "channel" in lower or "ritual" in lower:
        return "ritual"
    return "access"


@app.websocket("/ws", name="websocket")
async def websocket_endpoint(websocket: WebSocket, session_id: str, user_id: str = None):
    """
    WebSocket endpoint for real-time session updates.
    
    Maintains a persistent connection for a session, allowing:
    - Real-time chat streaming
    - Status updates
    - Notification delivery
    - Connection heartbeat
    
    **Connection URL:**
    ```
    ws://localhost:8000/ws?session_id=abc123&user_id=optional-user-id
    ```
    
    **Message Format:**
    All messages conform to WebSocketMessage schema:
    ```json
    {
        "id": "msg-uuid",
        "type": "chat|status|heartbeat|notification",
        "timestamp": "2026-06-05T10:30:45Z",
        "data": { ... },
        "session_id": "abc123",
        "user_id": "user456"
    }
    ```
    
    **Message Types:**
    - `welcome` - Server sends on connection (contains connection_id)
    - `chat` - Client sends, server broadcasts to other connections
    - `status` - Server sends status updates
    - `heartbeat` - Server periodically sends (keep-alive)
    - `notification` - Server sends alerts/updates
    
    **Example Client Code (JavaScript):**
    ```javascript
    const ws = new WebSocket(`ws://localhost:8000/ws?session_id=${sessionId}`);
    
    ws.onmessage = (event) => {
        const message = JSON.parse(event.data);
        console.log('Received:', message);
    };
    
    ws.send(JSON.stringify({
        type: 'chat',
        data: { text: 'Hello!' }
    }));
    ```
    
    **Automatic Features:**
    - Keep-alive heartbeat (30s interval)
    - Connection pooling per session
    - Automatic cleanup on disconnect
    - Broadcast to all connections in session
    """
    
    # Verify session exists
    if not session_id:
        await websocket.close(code=4000, reason="Missing session_id")
        return
    
    if not get_db().get_session(session_id):
        await websocket.close(code=4004, reason=f"Session {session_id} not found")
        return
    
    # Connect to manager
    connection = await ws_manager.connect(session_id, websocket, user_id)
    
    logger.info(
        "WebSocket connected",
        extra={
            "session_id": session_id,
            "user_id": user_id,
            "connection_id": connection.connection_id,
        }
    )
    
    metrics.inc("websocket_connections_total", session_id=session_id)
    metrics.gauge("websocket_active_connections", len(ws_manager.connections.get(session_id, [])))
    
    try:
        # Keep connection alive and handle incoming messages
        while True:
            # Receive message from client
            data = await connection.receive()
            
            # Parse message
            try:
                message = WebSocketMessage(
                    id=data.get("id", str(uuid.uuid4())),
                    type=data.get("type", "message"),
                    timestamp=data.get("timestamp") or datetime.now(timezone.utc).isoformat(),
                    data=data.get("data", {}),
                    session_id=session_id,
                    user_id=user_id,
                )
            except Exception as e:
                logger.warning(
                    "Invalid WebSocket message",
                    extra={
                        "session_id": session_id,
                        "error": str(e),
                    }
                )
                await connection.send(WebSocketMessage(
                    id=str(uuid.uuid4()),
                    type="error",
                    timestamp=datetime.now(timezone.utc).isoformat(),
                    data={"error": "Invalid message format"},
                    session_id=session_id,
                ))
                continue
            
            logger.debug(
                "WebSocket message received",
                extra={
                    "session_id": session_id,
                    "message_type": message.type,
                    "message_id": message.id,
                }
            )
            
            metrics.inc("websocket_messages_received_total", type=message.type)
            
            # Broadcast to other connections in session
            if message.type != "heartbeat":
                count = await ws_manager.broadcast(
                    session_id,
                    message,
                    exclude_connection_id=connection.connection_id
                )
                logger.info(
                    "WebSocket message broadcast",
                    extra={
                        "session_id": session_id,
                        "recipients": count,
                        "message_type": message.type,
                    }
                )
                metrics.inc("websocket_broadcasts_total", recipients=count)
    
    except WebSocketDisconnect:
        logger.info(
            "WebSocket disconnected",
            extra={
                "session_id": session_id,
                "connection_id": connection.connection_id,
            }
        )
        ws_manager.disconnect(session_id, connection.connection_id)
        metrics.inc("websocket_disconnections_total", session_id=session_id)
    
    except Exception as e:
        logger.exception(
            "WebSocket error",
            extra={
                "session_id": session_id,
                "error": str(e),
            }
        )
        ws_manager.disconnect(session_id, connection.connection_id)
        metrics.inc("websocket_errors_total", session_id=session_id)


# Startup task for periodic heartbeat
async def websocket_heartbeat():
    """Send heartbeat to all active WebSocket connections every 30 seconds."""
    while True:
        try:
            await asyncio.sleep(30)
            for session_id in list(ws_manager.connections.keys()):
                message = WebSocketMessage(
                    id=str(uuid.uuid4()),
                    type="heartbeat",
                    timestamp=datetime.now(timezone.utc).isoformat(),
                    data={"connections": len(ws_manager.connections[session_id])},
                    session_id=session_id,
                )
                await ws_manager.broadcast(session_id, message)
                logger.debug(
                    "WebSocket heartbeat sent",
                    extra={"session_id": session_id}
                )
        except Exception as e:
            logger.warning(f"Heartbeat error: {e}")
