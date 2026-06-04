"""
server.py
──────────
FastAPI application — the HTTP boundary of the Ramp backend.

Endpoints:
  POST /chat      → main onboarding query
  GET  /health    → liveness probe
  GET  /memories  → (optional) inspect retrieved memories for a profile
"""

import logging
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from backend.interfaces import OnboardingRequest, OnboardingResponse
from backend.agent.agent import get_agent

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────
# App lifecycle — warm up the agent on startup
# ─────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("🚀 Ramp backend starting up...")
    get_agent()  # Initialize singleton (validates GROQ_API_KEY early)
    logger.info("✅ Agent ready")
    yield
    logger.info("🛑 Ramp backend shutting down")


# ─────────────────────────────────────────────
# FastAPI app
# ─────────────────────────────────────────────

app = FastAPI(
    title="Ramp — Onboarding Agent API",
    description="AI-powered onboarding assistant with Hindsight Memory",
    version="1.0.0",
    lifespan=lifespan,
)

# Allow frontend dev server (Vite default: 5173, CRA: 3000)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─────────────────────────────────────────────
# Routes
# ─────────────────────────────────────────────

@app.get("/health")
async def health():
    """Liveness probe — used by frontend to check if backend is up."""
    return {"status": "ok", "service": "ramp-agent"}


@app.post("/chat", response_model=OnboardingResponse)
async def chat(request: OnboardingRequest) -> OnboardingResponse:
    """
    Main onboarding chat endpoint.

    Example request body:
    {
        "name": "Priya",
        "team": "Platform Team",
        "role": "Backend Engineer",
        "employee_type": "contractor",
        "query": "What should I do on Day 1?"
    }
    """
    # Inject a session_id if the client didn't send one
    if not request.session_id:
        request.session_id = str(uuid.uuid4())

    try:
        agent = get_agent()
        response = await agent.run(request)
        return response
    except EnvironmentError as e:
        # Missing API keys — fail with a clear message
        logger.error("Configuration error: %s", e)
        raise HTTPException(status_code=500, detail=f"Server configuration error: {e}")
    except Exception as e:
        logger.exception("Unexpected error processing chat request")
        raise HTTPException(status_code=500, detail=f"Agent error: {str(e)}")
