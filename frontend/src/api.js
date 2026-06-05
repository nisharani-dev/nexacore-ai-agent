// api.js — all backend communication

import { MOCK_PERSONAS, classifyMessage, getPersonaMemories } from "./mock_responses.js";

const USE_MOCK = import.meta.env.VITE_USE_MOCK === "true";
const API_BASE = import.meta.env.VITE_API_BASE || "/api";
const USE_STREAM = import.meta.env.VITE_USE_STREAM === "true";

const mockDelay = (ms) => new Promise((res) => setTimeout(res, ms));

function sessionHeaders(sessionId) {
  const headers = { "Content-Type": "application/json" };
  if (sessionId) headers["X-Session-ID"] = sessionId;
  return headers;
}

function mapResponse(data) {
  return {
    reply: data.message || data.answer || "",
    memory_used: Array.isArray(data.memories_used) && data.memories_used.length > 0,
    new_memories: (data.new_memories_written || data.new_memories || []).map((memory) => ({
      scope: mapScope(memory.level),
      type: inferType(memory),
      text: memory.content,
    })),
    suggested_actions: data.suggested_actions || [],
    tools_used: data.tools_used || [],
    integrations_mode: data.integrations_mode || "demo",
  };
}

export async function sendMessage(userMessage, context) {
  if (USE_MOCK) {
    await mockDelay(800 + Math.random() * 500);
    const persona = MOCK_PERSONAS[context.personaMode] || MOCK_PERSONAS.person1;
    const key = classifyMessage(userMessage);
    const response = persona.responses[key] || persona.responses.default;
    const mems = response.new_memories
      ? Array.isArray(response.new_memories) ? response.new_memories : [response.new_memories]
      : null;
    return { ...response, new_memories: mems, tools_used: response.tools_used || [], integrations_mode: "demo" };
  }

  if (USE_STREAM) {
    return sendMessageStream(userMessage, context);
  }

  const res = await fetch(`${API_BASE}/chat`, {
    method: "POST",
    headers: sessionHeaders(context.sessionId),
    body: JSON.stringify({
      name: context.name,
      team: context.team,
      role: context.role,
      employee_type: context.employmentType,
      query: userMessage,
      session_id: context.sessionId,
      demo_mode: context.personaMode,
    }),
  });
  if (!res.ok) throw new Error(`Backend error: ${res.status}`);
  return mapResponse(await res.json());
}

export async function sendMessageStream(userMessage, context) {
  const res = await fetch(`${API_BASE}/chat/stream`, {
    method: "POST",
    headers: sessionHeaders(context.sessionId),
    body: JSON.stringify({
      name: context.name,
      team: context.team,
      role: context.role,
      employee_type: context.employmentType,
      query: userMessage,
      session_id: context.sessionId,
      demo_mode: context.personaMode,
    }),
  });
  if (!res.ok) throw new Error(`Stream error: ${res.status}`);

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let reply = "";
  let finalResponse = null;

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n");
    buffer = lines.pop() || "";
    for (const line of lines) {
      if (!line.startsWith("data: ")) continue;
      const payload = JSON.parse(line.slice(6));
      if (payload.type === "token") reply += payload.text;
      if (payload.type === "done") finalResponse = mapResponse(payload.response);
    }
  }

  return { ...finalResponse, reply: reply || finalResponse?.reply || "" };
}

export async function createSession(context) {
  if (USE_MOCK) return { session_id: crypto.randomUUID() };

  const res = await fetch(`${API_BASE}/sessions`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      name: context.name,
      team: context.team,
      role: context.role,
      employee_type: context.employmentType,
      metadata: { persona_mode: context.personaMode },
    }),
  });
  if (!res.ok) throw new Error(`Session create error: ${res.status}`);
  return await res.json();
}

export async function getMemories(teamPath, personaMode = "person1", employmentType = "fte", role = "") {
  if (USE_MOCK) {
    await mockDelay(200);
    return getPersonaMemories(personaMode, teamPath);
  }

  const res = await fetch(
    `${API_BASE}/memories?team=${encodeURIComponent(teamPath)}&employee_type=${encodeURIComponent(employmentType)}&role=${encodeURIComponent(role)}&demo_mode=${encodeURIComponent(personaMode)}`
  );
  if (!res.ok) throw new Error(`Memory fetch error: ${res.status}`);
  const data = await res.json();
  return data.memories ?? [];
}

export async function getSessionMessages(sessionId) {
  if (USE_MOCK) return [];
  const res = await fetch(`${API_BASE}/sessions/${sessionId}/messages`, {
    headers: sessionHeaders(sessionId),
  });
  if (!res.ok) return [];
  const data = await res.json();
  return data.messages ?? [];
}

export async function resetDemo() {
  if (USE_MOCK) return { status: "reset" };
  const res = await fetch(`${API_BASE}/demo/reset`, { method: "POST" });
  if (!res.ok) throw new Error(`Reset error: ${res.status}`);
  return await res.json();
}

export async function getTickets() {
  if (USE_MOCK) return [];
  const res = await fetch(`${API_BASE}/tickets`);
  if (!res.ok) return [];
  return (await res.json()).tickets ?? [];
}

export async function getReminders() {
  if (USE_MOCK) return [];
  const res = await fetch(`${API_BASE}/reminders`);
  if (!res.ok) return [];
  return (await res.json()).reminders ?? [];
}

export async function getAudit() {
  if (USE_MOCK) return [];
  const res = await fetch(`${API_BASE}/audit`);
  if (!res.ok) return [];
  return (await res.json()).events ?? [];
}

export async function getIntegrationsStatus() {
  if (USE_MOCK) return { mode: "demo", label: "mock integrations (demo)" };
  const res = await fetch(`${API_BASE}/integrations/status`);
  if (!res.ok) return { mode: "demo", label: "unknown" };
  return await res.json();
}

export async function getAnalyticsSummary() {
  if (USE_MOCK) return { chat_requests_total: 0 };
  const res = await fetch(`${API_BASE}/analytics/summary`);
  if (!res.ok) return {};
  return await res.json();
}

export async function submitFeedback({ sessionId, team, query, helpful, comment = "" }) {
  if (USE_MOCK) return { helpful };
  const res = await fetch(`${API_BASE}/feedback`, {
    method: "POST",
    headers: sessionHeaders(sessionId),
    body: JSON.stringify({
      session_id: sessionId,
      team,
      query,
      helpful,
      comment,
    }),
  });
  if (!res.ok) throw new Error(`Feedback error: ${res.status}`);
  return await res.json();
}

export async function getOidcInfo() {
  const res = await fetch(`${API_BASE}/auth/oidc/info`);
  if (!res.ok) throw new Error(`OIDC info error: ${res.status}`);
  return await res.json();
}

export async function startOidcLogin() {
  const redirectUri = `${window.location.origin}/callback`;
  const res = await fetch(
    `${API_BASE}/auth/oidc/login?redirect_uri=${encodeURIComponent(redirectUri)}&state=ramp`
  );
  if (!res.ok) throw new Error(`OIDC login error: ${res.status}`);
  const data = await res.json();
  if (data.authorization_url) window.location.href = data.authorization_url;
}

function mapScope(level) {
  if (level === "company") return "company";
  if (level === "division" || level === "org") return "org";
  if (level === "team" || level === "sub_team") return "team";
  return "role";
}

function inferType(memory) {
  const lower = memory.content.toLowerCase();
  if (lower.includes("known blocker") || lower.includes("blocker")) return "blocker";
  if (memory.level === "exception" || (memory.tags || []).some((tag) => tag.startsWith("exception:"))) {
    return "exception";
  }
  if (lower.includes("slack") || lower.includes("channel")) return "ritual";
  return "access";
}
