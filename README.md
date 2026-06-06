# NexaCore - AI-Powered Onboarding Assistant

Cloud-ready onboarding assistant with:
- 🤖 Groq-backed conversational agent
- 🧠 **Hindsight Cloud Memory** - AI-powered knowledge base
- 🎯 Hierarchical team context resolution
- 📝 Memory retrieval and writeback
- 🎭 Demo memory flywheel (`person #1` vs `person #10`)
- 🎫 Operational actions for tickets, reminders, and blocker logging

## ⚡ Quick Start

### Backend

```bash
python3 -m backend.main
```

### Frontend

```bash
cd frontend
npm ci
npm run dev
```

### Configuration

Copy `.env.example` to `.env` and set:

**Required:**
- `GROQ_API_KEY` - Your Groq API key
- `HINDSIGHT_API_KEY` - Your Hindsight Cloud API key
- `HINDSIGHT_BASE_URL` - `https://api.hindsight.vectorize.io`

**Optional:**
- `DATABASE_URL` - PostgreSQL connection (uses SQLite if not set)
- `AUTH_REQUIRED` - Enable API authentication (`false` by default)

## 🧠 Hindsight Cloud Memory

NexaCore uses **Hindsight Cloud** for intelligent memory and context management:

- ☁️ **Cloud-native** - No self-hosting required
- 🔍 **Semantic search** - Find relevant context automatically  
- 🤖 **LLM integration** - Generate AI-powered answers
- 📚 **Mental models** - Living documents that stay current
- ⚡ **Auto-fallback** - Falls back to local storage if unavailable

### Setup

```env
HINDSIGHT_BACKEND=http
HINDSIGHT_BASE_URL=https://api.hindsight.vectorize.io
HINDSIGHT_API_KEY=hsk_...
HINDSIGHT_PROJECT=default
```

See `HINDSIGHT_READY.md` for complete setup guide.

## 🐳 Production Run

```bash
docker compose -f docker-compose.prod.yml up --build
```

Services:
- frontend: `http://localhost:3000`
- backend: `http://localhost:8000`

## 📝 Environment Variables

### Core Settings
- `GROQ_API_KEY` - Groq LLM API key (required)
- `GROQ_MODEL` - Model name (default: `openai/gpt-oss-20b`)
- `APP_ENV` - Environment (`development` or `production`)
- `PORT` - Backend port (default: `8000`)

### Hindsight Memory
- `HINDSIGHT_BACKEND` - Memory backend (`local` or `http`)
- `HINDSIGHT_BASE_URL` - Cloud API URL (for `http` mode)
- `HINDSIGHT_API_KEY` - Cloud API authentication key
- `HINDSIGHT_PROJECT` - Bank/project ID (default: `default`)

### Database
- `DATABASE_URL` - PostgreSQL connection string (optional, uses SQLite if not set)
- `DATA_DIR` - Data storage directory (default: `./data`)

### Authentication
- `AUTH_REQUIRED` - Enable API key auth (default: `false`)
- `APP_API_KEY` - Shared secret for protected endpoints
- `RBAC_ENFORCE` - Enable role-based access control

### Integrations
- `INTEGRATIONS_MODE` - `demo` (mock) or `live` (real APIs)
- `JIRA_BASE_URL`, `JIRA_API_TOKEN` - Jira integration
- `SMTP_HOST`, `SMTP_USER`, `SMTP_PASSWORD` - Email integration
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
