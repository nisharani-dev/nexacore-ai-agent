# Ramp — From Day One to Day Done

> An AI-powered onboarding assistant that learns from every employee's experience and guides the next one smarter.

---

## What is Ramp?

Onboarding knowledge lives in scattered docs, Slack threads, and tribal knowledge. Every new employee hits the same blockers, asks the same questions, and waits on the same tickets.

Ramp fixes that.

It uses **Hindsight Memory** — a hierarchical memory system that captures real onboarding experiences and surfaces them to the next person joining the same team. The more people onboard, the smarter it gets.

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

Every memory is tagged to a level in the org hierarchy:

```
Company → Engineering → Platform Team → Infrastructure Security
```

A new joiner in Infrastructure Security inherits memories from all four levels — plus any exception memories for their role type (contractor, intern, full-time).

---

## Project Structure

```
backend/
├── agent/
│   ├── agent.py           # AI orchestrator — central workflow controller
│   ├── prompt_builder.py  # system + human prompt construction
│   └── tools.py           # LangChain tool registry (raise_ticket, send_reminder, log_blocker)
├── context/
│   ├── context_builder.py # assembles full context for the agent
│   ├── team_resolver.py   # resolves team hierarchy from teams.yaml
│   └── exception_tagger.py# detects contractor / intern / special case flags
├── memory/
│   ├── hindsight_client.py# Hindsight Memory read/write client
│   ├── retriever.py       # semantic memory retrieval across hierarchy
│   └── writer.py          # writes new memories post-interaction
├── actions/
│   ├── raise_ticket.py    # raises IT / access tickets
│   ├── send_reminder.py   # sends reminders to people/teams
│   └── log_blocker.py     # logs onboarding blockers
├── ingestion/
│   ├── confluence_ingest.py
│   ├── gdocs_ingest.py
│   └── ingest_runner.py
├── interfaces.py          # shared data contracts for all modules
├── server.py              # FastAPI app
└── main.py                # entry point

frontend/
├── src/
│   ├── App.jsx
│   ├── ChatWindow.jsx
│   ├── MemoryPanel.jsx
│   ├── MessageInput.jsx
│   └── api.js

config/
└── teams.yaml             # org hierarchy definition
```

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

### `GET /health`

```json
{ "status": "ok", "service": "ramp-agent" }
```

---

## Setup

### Prerequisites

- Python 3.11+
- A [Groq API key](https://console.groq.com)

### Install

```bash
pip install -r backend/requirements.txt
```

### Configure

```bash
cp .env.example .env
# Add your GROQ_API_KEY to .env
```

### Run

```bash
python -m backend.main
# or
uvicorn backend.server:app --reload --port 8000
```

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
- **Memory**: Hindsight Memory (custom)
- **Frontend**: React + Vite

---

*Built for the Ramp hackathon — From Day One to Day Done.*
