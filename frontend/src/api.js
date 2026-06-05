// api.js
// ---------------------------------------------------------------------------
// All communication with the backend lives here.
// The rest of the app never does fetch() directly — it calls these functions.
//
// TO SWITCH FROM MOCK TO REAL:
//   1. Set USE_MOCK = false
//   2. Set API_BASE to Person 1's backend URL
//   That's it. No other file changes.
// ---------------------------------------------------------------------------

import { MOCK_PERSONAS, classifyMessage } from "./mock_responses.js";

const USE_MOCK = true; // flip to false when backend is ready
const API_BASE = "http://localhost:8000"; // Person 1's FastAPI/Express URL

// Simulated network delay for mock (makes it feel real)
const mockDelay = (ms) => new Promise((res) => setTimeout(res, ms));

// ---------------------------------------------------------------------------
// sendMessage
// ---------------------------------------------------------------------------
// @param userMessage  string   — what the user typed
// @param context      object   — { name, team, role, personaMode }
//
// @returns Promise<{
//   reply:         string,
//   memory_used:   boolean,
//   new_memories:  Array<{ scope, type, text }> | null
// }>
// ---------------------------------------------------------------------------
export async function sendMessage(userMessage, context) {
  if (USE_MOCK) {
    await mockDelay(800 + Math.random() * 500);
    const persona = MOCK_PERSONAS[context.personaMode] || MOCK_PERSONAS.person1;
    const key = classifyMessage(userMessage);
    const response = persona.responses[key] || persona.responses.default;
    // new_memories from mock can be a single object — normalise to array
    const mems = response.new_memories
      ? Array.isArray(response.new_memories)
        ? response.new_memories
        : [response.new_memories]
      : null;
    return { ...response, new_memories: mems };
  }

  // --- real backend ---
  const res = await fetch(`${API_BASE}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      message: userMessage,
      user_name: context.name,
      team: context.team,
      role: context.role,
      employment_type: context.employmentType,
    }),
  });
  if (!res.ok) throw new Error(`Backend error: ${res.status}`);
  return await res.json();
}

// ---------------------------------------------------------------------------
// getMemories
// ---------------------------------------------------------------------------
// Fetch the current memory state for a team path.
// In mock mode returns pre-seeded memories from the selected persona.
//
// @param teamPath     string   — e.g. "platform-eng"
// @param personaMode  string   — "person1" | "person10"  (mock only)
//
// @returns Promise<Array<{ scope, type, text }>>
// ---------------------------------------------------------------------------
export async function getMemories(teamPath, personaMode = "person1") {
  if (USE_MOCK) {
    await mockDelay(200);
    return MOCK_PERSONAS[personaMode]?.memories ?? [];
  }

  const res = await fetch(
    `${API_BASE}/memories?team=${encodeURIComponent(teamPath)}`
  );
  if (!res.ok) throw new Error(`Memory fetch error: ${res.status}`);
  const data = await res.json();
  return data.memories ?? [];
}
