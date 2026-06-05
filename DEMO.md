# Ramp Demo Script (3 minutes)

## Setup

```bash
# Terminal 1 — backend
python3 -m backend.main

# Terminal 2 — frontend
cd frontend && npm ci && npm run dev
```

Ensure `frontend/.env` has `VITE_USE_MOCK=false` and `GROQ_API_KEY` is set in backend `.env`.

## Act 1 — Person #1 (sparse memory)

1. Open http://localhost:5173
2. Enter name **Priya**, team **Platform Engineering**, role **SDE-1**, FTE
3. Point out the **persona banner**: ~4 memories, cautious tone
4. Ask: **"How do I get AWS access?"**
5. Note: generic answer, no team-specific SLA

## Act 2 — Person #10 (rich memory)

1. Toggle **person #10** in the top bar
2. Watch memory count jump (+8) and banner update
3. Ask the same AWS question
4. Note: 5-day SLA, Okta pre-approval, proactive steps
5. Show **memory panel** — blockers, rituals, exceptions

## Act 3 — Operations

1. Click **ops** in the top bar
2. Show tickets/reminders created by agent tools (mock mode badge)
3. Mention: `INTEGRATIONS_MODE=live` + Jira creds → real tickets

## Act 4 — Flywheel

1. Ask about a blocker not in memory
2. Agent may write a new memory — watch panel animate
3. Click **reset demo** to replay for next audience

## Talking points

- Hindsight is local JSON today; HTTP adapter ready for cloud migration
- Session IDs thread through chat + audit trail
- 150+ synthetic employee records simulate 2022–2025 onboarding history
