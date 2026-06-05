# Ramp Onboarding Agent

Cloud-ready onboarding assistant with:
- Groq-backed conversational agent
- hierarchical team context resolution
- memory retrieval and writeback
- demo memory flywheel (`person #1` vs `person #10`)
- operational actions for tickets, reminders, and blocker logging

## Local Run

Backend:

```bash
python3 -m backend.main
```

Frontend:

```bash
cd frontend
npm ci
npm run dev
```

Copy `.env.example` to `.env` and fill in at least `GROQ_API_KEY`.

## Production Run

```bash
docker compose -f docker-compose.prod.yml up --build
```

Services:
- frontend: `http://localhost:3000`
- backend: `http://localhost:8000`

## Environment

Important variables:
- `GROQ_API_KEY`: required
- `GROQ_MODEL`: defaults to `openai/gpt-oss-20b`
- `DATA_DIR`: writable application storage for cloud volumes
- `APP_DB_PATH`: SQLite operational database path
- `AUTH_REQUIRED`: enable API-key auth for protected endpoints
- `APP_API_KEY`: shared secret for server-to-server or protected environments
- `HINDSIGHT_STORE_PATH`: memory persistence file path
- `REMINDER_STORE_PATH`: reminder persistence file path
- `TICKET_STORE_PATH`: ticket persistence file path
- `HINDSIGHT_BACKEND`: `local` or `http`
- `HINDSIGHT_BASE_URL`: required for the HTTP-backed Hindsight adapter

## Cloud Deployment Notes

Recommended production split:
1. Deploy backend as a containerized web service.
2. Mount persistent storage to `/app/data` or override the store paths explicitly.
3. Serve the frontend behind a reverse proxy that forwards `/api/*` to the backend.
4. Set `VITE_API_BASE=/api` for same-origin browser requests.

Recommended next production upgrades:
1. Move the operational SQLite store to managed Postgres or Cloud SQL for multi-instance deployments.
2. Add authentication for employee identity and role-aware authorization.
3. Add tracing, metrics, and request correlation IDs.
4. Replace mock ticket/reminder implementations with Jira/ServiceNow and email/calendar integrations.
5. Replace local Hindsight fallback with the real managed Hindsight service once the exact API contract is available.

## Operational Endpoints

- `GET /health`
- `GET /ready`
- `GET /metrics`
- `GET /analytics/summary`
- `POST /sessions`
- `GET /sessions/{session_id}`
- `GET /sessions/{session_id}/messages`
- `GET /memory/summary`
- `GET /tickets`
- `GET /reminders`
- `GET /reminders/{id}/ics`
- `GET /audit`
- `GET /integrations/status`
- `POST /feedback`
- `POST /demo/reset`
- `POST /chat/stream` (SSE)
- `WS /ws?session_id=...`

See [DEMO.md](DEMO.md) for the 3-minute presentation walkthrough.

## Hindsight Cloud Migration

The code is currently productionized around a local persistent fallback store so the product can run today.

To migrate to a real Hindsight cloud service, collect:
- base API URL
- API key / service token
- project or workspace identifier
- namespace or collection naming rules
- search and write endpoint contract

Once you have those exact Hindsight docs or dashboard fields, the client can be swapped cleanly behind `backend/memory/hindsight_client.py`.
