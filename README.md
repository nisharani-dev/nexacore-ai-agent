# Ramp — From Day One to Day Done

> An AI-powered onboarding assistant that learns from every employee's experience and guides the next one smarter.

Cloud-ready onboarding assistant with:
- Groq-backed conversational agent
- Hierarchical team context resolution
- Memory retrieval and writeback
- Demo memory flywheel (`person #1` vs `person #10`)
- Operational actions for tickets, reminders, and blocker logging

---

## How It Works

```
New Employee Query
       │
       ▼
  Context Builder  →  resolves team hierarchy + exceptions
       │
       ▼
  Memory Retrieval →  fetches relevant memories across all hierarchy levels
       │
       ▼
  AI Agent (Groq)  →  constructs prompt + generates personalized guidance
       │
       ▼
  Tool Calling     →  raises tickets / sends reminders / logs blockers
       │
       ▼
  Response
```

### Hierarchical Memory

```
Company → Engineering → Platform Team → Infrastructure Security
```

A new joiner inherits memories from all levels — plus exception memories for their role type (contractor, intern, full-time).

---

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

---

## Production Run

```bash
docker compose -f docker-compose.prod.yml up --build
```

Services:
- frontend: `http://localhost:3000`
- backend: `http://localhost:8000`

---

## Environment

| Variable | Description |
|---|---|
| `GROQ_API_KEY` | Required |
| `GROQ_MODEL` | Defaults to `llama3-70b-8192` |
| `DATA_DIR` | Writable storage for cloud volumes |
| `APP_DB_PATH` | SQLite operational database path |
| `AUTH_REQUIRED` | Enable API-key auth for protected endpoints |
| `APP_API_KEY` | Shared secret for server-to-server calls |
| `HINDSIGHT_STORE_PATH` | Memory persistence file path |
| `REMINDER_STORE_PATH` | Reminder persistence file path |
| `TICKET_STORE_PATH` | Ticket persistence file path |
| `HINDSIGHT_BACKEND` | `local` or `http` |
| `HINDSIGHT_BASE_URL` | Required for HTTP-backed Hindsight adapter |

---

## API

### `POST /chat`

```json
// Request
{
  "name": "Priya",
  "team": "Platform Team",
  "role": "Backend Engineer",
  "employee_type": "contractor",
  "query": "What should I do on Day 1?"
}

// Response
{
  "message": "Here's what previous Platform Team contractors found most critical on Day 1...",
  "memories_used": [...],
  "suggested_actions": ["raise_ticket: AWS access request submitted"],
  "new_memories_written": []
}
```

### Operational Endpoints

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
- `GET /audit`
- `POST /feedback`
- `POST /demo/reset`
- `POST /chat/stream` (SSE)
- `WS /ws?session_id=...`

---

## Project Structure

```
backend/
├── agent/
│   ├── agent.py           # AI orchestrator — central workflow controller
│   ├── prompt_builder.py  # system + human prompt construction
│   └── tools.py           # LangChain tool registry
├── context/
│   ├── context_builder.py
│   ├── team_resolver.py
│   └── exception_tagger.py
├── memory/
│   ├── hindsight_client.py
│   ├── retriever.py
│   └── writer.py
├── actions/
│   ├── raise_ticket.py
│   ├── send_reminder.py
│   └── log_blocker.py
├── ingestion/
│   ├── confluence_ingest.py
│   ├── gdocs_ingest.py
│   └── ingest_runner.py
├── interfaces.py          # shared data contracts
├── server.py              # FastAPI app
└── main.py                # entry point

config/
└── teams.yaml             # org hierarchy definition
```

---

## Cloud Deployment Notes

1. Deploy backend as a containerized web service.
2. Mount persistent storage to `/app/data` or override store paths explicitly.
3. Serve frontend behind a reverse proxy that forwards `/api/*` to the backend.
4. Set `VITE_API_BASE=/api` for same-origin browser requests.

Recommended next upgrades:
1. Move SQLite to managed Postgres for multi-instance deployments.
2. Add authentication for employee identity and role-aware authorization.
3. Add tracing, metrics, and request correlation IDs.
4. Replace mock ticket/reminder implementations with Jira/ServiceNow integrations.
5. Replace local Hindsight fallback with the real managed Hindsight service.

---

## Team

| Person | Responsibility |
|---|---|
| Person 1 — Nisha | Agent Orchestrator + LLM Integration |
| Person 2 | Hindsight Memory Layer |
| Person 3 | Context Builder + Team Resolver |
| Person 4 | Action Layer + Data Ingestion |
| Person 5 | Frontend + Demo Experience |

---

## Tech Stack

- **LLM**: Groq (llama3-70b-8192)
- **Agent Framework**: LangChain + LangGraph
- **API**: FastAPI + Uvicorn
- **Memory**: Hindsight Memory
- **Frontend**: React + Vite

---

*Built for the Ramp hackathon — From Day One to Day Done.*
