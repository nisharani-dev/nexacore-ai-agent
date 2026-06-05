// App.jsx — root state owner

import { useState, useCallback, useEffect } from "react";
import ChatWindow from "./ChatWindow";
import MessageInput from "./MessageInput";
import MemoryPanel from "./MemoryPanel";
import OpsPanel from "./OpsPanel";
import PersonaBanner from "./PersonaBanner";
import AuthButton from "./AuthButton";
import { useWebSocket } from "./hooks/useWebSocket";
import {
  sendMessage,
  getMemories,
  createSession,
  resetDemo,
  getTickets,
  getReminders,
  getAudit,
  getIntegrationsStatus,
  getSessionMessages,
} from "./api";
import { MOCK_PERSONAS } from "./mock_responses";

const TEAMS = [
  { value: "platform",       label: "Engineering → Platform Engineering" },
  { value: "infra_security", label: "Engineering → Platform → Infra Security" },
  { value: "data_platform",  label: "Engineering → Data Platform" },
  { value: "fp_and_a",       label: "Finance → FP&A" },
];

const ROLES = [
  { value: "SDE Intern",          label: "SDE Intern" },
  { value: "SDE-1",               label: "SDE-1 / Junior Engineer" },
  { value: "SDE-2",               label: "SDE-2 / Mid Engineer" },
  { value: "Staff Engineer",      label: "Staff Engineer" },
  { value: "Engineering Manager", label: "Engineering Manager" },
];

const EMPLOYMENT_TYPES = [
  { value: "fte",        label: "Full-time employee (FTE)" },
  { value: "contractor", label: "Contractor" },
  { value: "intern",     label: "Intern" },
];

function makeId() {
  return Math.random().toString(36).slice(2, 9);
}

function nowTime() {
  return new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

function OnboardingScreen({ onStart }) {
  const [name, setName] = useState("");
  const [team, setTeam] = useState("platform");
  const [role, setRole] = useState("SDE-1");
  const [empType, setEmpType] = useState("fte");

  return (
    <div className="ob-overlay">
      <div className="ob-card">
        <div className="ob-logo"><span className="ob-dot" />RAMP</div>
        <p className="ob-sub">// your onboarding agent</p>
        <div className="ob-field">
          <label className="ob-label">your name</label>
          <input className="ob-input" placeholder="e.g. Priya Sharma" value={name}
            onChange={(e) => setName(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && name.trim() && onStart({ name, team, role, empType })} />
        </div>
        <div className="ob-field">
          <label className="ob-label">team</label>
          <select className="ob-select" value={team} onChange={(e) => setTeam(e.target.value)}>
            {TEAMS.map((t) => <option key={t.value} value={t.value}>{t.label}</option>)}
          </select>
        </div>
        <div className="ob-row">
          <div className="ob-field ob-field--half">
            <label className="ob-label">role / level</label>
            <select className="ob-select" value={role} onChange={(e) => setRole(e.target.value)}>
              {ROLES.map((r) => <option key={r.value} value={r.value}>{r.label}</option>)}
            </select>
          </div>
          <div className="ob-field ob-field--half">
            <label className="ob-label">employment type</label>
            <select className="ob-select" value={empType} onChange={(e) => setEmpType(e.target.value)}>
              {EMPLOYMENT_TYPES.map((e) => <option key={e.value} value={e.value}>{e.label}</option>)}
            </select>
          </div>
        </div>
        <button className="ob-btn" disabled={!name.trim()} onClick={() => onStart({ name, team, role, empType })}>
          begin onboarding →
        </button>
      </div>
    </div>
  );
}

export default function App() {
  const [phase, setPhase] = useState("onboarding");
  const [personaMode, setPersonaMode] = useState("person1");
  const [prevMemoryCount, setPrevMemoryCount] = useState(null);
  const [messages, setMessages] = useState([]);
  const [memories, setMemories] = useState([]);
  const [newMemIds, setNewMemIds] = useState(new Set());
  const [isTyping, setIsTyping] = useState(false);
  const [userContext, setUserContext] = useState(null);
  const [showOps, setShowOps] = useState(false);
  const [opsData, setOpsData] = useState({ tickets: [], reminders: [], audit: [], integrations: null });
  const [opsLoading, setOpsLoading] = useState(false);
  const refreshOps = useCallback(async () => {
    setOpsLoading(true);
    try {
      const [tickets, reminders, audit, integrations] = await Promise.all([
        getTickets(), getReminders(), getAudit(), getIntegrationsStatus(),
      ]);
      setOpsData({ tickets, reminders, audit, integrations });
    } finally {
      setOpsLoading(false);
    }
  }, []);

  useWebSocket(userContext?.sessionId, (payload) => {
    if (payload.type === "memory_update" && payload.data?.new_memories?.length) {
      const additions = payload.data.new_memories;
      const ids = new Set(additions.map((m) => `${m.scope}-${m.text}`));
      setNewMemIds(ids);
      setMemories((prev) => {
        const existing = new Set(prev.map((m) => `${m.scope}-${m.text}`));
        return [...prev, ...additions.filter((m) => !existing.has(`${m.scope}-${m.text}`))];
      });
      setTimeout(() => setNewMemIds(new Set()), 3000);
    }
  });

  useEffect(() => {
    if (showOps) refreshOps();
  }, [showOps, refreshOps, messages.length]);

  const handleStart = useCallback(async ({ name, team, role, empType }) => {
    const session = await createSession({
      name, team, role, employmentType: empType, personaMode,
    });
    const ctx = {
      name, team, role, employmentType: empType, personaMode,
      sessionId: session.session_id,
    };
    setUserContext(ctx);
    setPhase("chat");

    const mems = await getMemories(team, personaMode, empType, role);
    setMemories(mems);
    setPrevMemoryCount(null);

    const history = await getSessionMessages(session.session_id);
    if (history.length) {
      setMessages(history.map((m) => ({
        id: m.id,
        role: m.role,
        text: m.content,
        memoryUsed: Boolean(m.metadata?.memory_count),
        suggestedActions: m.metadata?.suggested_actions,
        toolsUsed: m.metadata?.tools_used,
        time: m.created_at?.slice(11, 16) || nowTime(),
      })));
      return;
    }

    setIsTyping(true);
    const res = await sendMessage("hello", { ...ctx, personaMode });
    setIsTyping(false);
    setMessages([buildAgentMessage(res, "hello")]);
  }, [personaMode]);

  const buildAgentMessage = (res, query) => ({
    id: makeId(),
    role: "agent",
    text: res.reply,
    memoryUsed: res.memory_used,
    suggestedActions: res.suggested_actions,
    toolsUsed: res.tools_used,
    integrationsMode: res.integrations_mode,
    time: nowTime(),
    animate: true,
    feedbackQuery: query,
  });

  const handleSend = useCallback(async (text) => {
    if (isTyping) return;
    setMessages((prev) => [...prev, { id: makeId(), role: "user", text, time: nowTime(), animate: true }]);
    setIsTyping(true);

    try {
      const res = await sendMessage(text, { ...userContext, personaMode });
      setIsTyping(false);
      setMessages((prev) => [...prev, buildAgentMessage(res, text)]);

      if (res.new_memories?.length) {
        const ids = new Set(res.new_memories.map((m) => `${m.scope}-${m.text}`));
        setNewMemIds(ids);
        setMemories((prev) => {
          const existing = new Set(prev.map((m) => `${m.scope}-${m.text}`));
          return [...prev, ...res.new_memories.filter((m) => !existing.has(`${m.scope}-${m.text}`))];
        });
        setTimeout(() => setNewMemIds(new Set()), 3000);
      }
    } catch {
      setIsTyping(false);
      setMessages((prev) => [...prev, {
        id: makeId(), role: "agent",
        text: "Something went wrong connecting to the backend. Check the console.",
        memoryUsed: false, time: nowTime(), animate: true,
      }]);
    }
  }, [isTyping, userContext, personaMode]);

  const handlePersonaToggle = useCallback(async (mode) => {
    setPrevMemoryCount(memories.length);
    setPersonaMode(mode);
    if (phase === "chat" && userContext) {
      const mems = await getMemories(
        userContext.team, mode, userContext.employmentType, userContext.role,
      );
      setMemories(mems);
    }
  }, [phase, userContext, memories.length]);

  const handleDemoReset = useCallback(async () => {
    await resetDemo();
    if (userContext) {
      const mems = await getMemories(
        userContext.team, personaMode, userContext.employmentType, userContext.role,
      );
      setMemories(mems);
      setPrevMemoryCount(null);
    }
    setMessages([]);
    setPhase("onboarding");
    setUserContext(null);
  }, [userContext, personaMode]);

  const personaLabel = MOCK_PERSONAS[personaMode]?.label ?? personaMode;

  return (
    <div className="app">
      <header className="topbar">
        <div className="topbar-logo">
          <span className="topbar-dot" aria-hidden="true" />
          <span className="topbar-name">RAMP</span>
          <span className="topbar-tag">/ onboarding agent</span>
        </div>

        {phase === "chat" && (
          <div className="topbar-center">
            <span className="ctx-pill ctx-pill--team">{userContext?.team}</span>
            <span className="ctx-pill ctx-pill--role">{userContext?.role}</span>
            <span className="ctx-pill ctx-pill--emp">{userContext?.employmentType}</span>
          </div>
        )}

        <div className="topbar-actions">
          <AuthButton />
          <button className="topbar-btn" type="button" onClick={() => setShowOps((v) => !v)}>
            {showOps ? "hide ops" : "ops"}
          </button>
          <button className="topbar-btn topbar-btn--reset" type="button" onClick={handleDemoReset}>
            reset demo
          </button>
          <div className="demo-toggle" role="group" aria-label="Demo persona toggle">
            <span className="demo-label">demo</span>
            <button className={`demo-btn ${personaMode === "person1" ? "demo-btn--active" : ""}`}
              onClick={() => handlePersonaToggle("person1")}>person #1</button>
            <button className={`demo-btn ${personaMode === "person10" ? "demo-btn--active" : ""}`}
              onClick={() => handlePersonaToggle("person10")}>person #10</button>
          </div>
        </div>
      </header>

      {phase === "chat" && (
        <PersonaBanner
          personaMode={personaMode}
          memoryCount={memories.length}
          prevCount={prevMemoryCount}
          team={userContext?.team}
        />
      )}

      <div className={`main ${showOps ? "main--with-ops" : ""}`}>
        <div className="chat-col">
          <ChatWindow
            messages={messages}
            isTyping={isTyping}
            userName={userContext?.name}
            sessionId={userContext?.sessionId}
            team={userContext?.team}
          />
          <MessageInput onSend={handleSend} disabled={isTyping || phase === "onboarding"} />
        </div>

        <MemoryPanel memories={memories} personaLabel={personaLabel} newMemoryIds={newMemIds} />

        {showOps && (
          <OpsPanel
            tickets={opsData.tickets}
            reminders={opsData.reminders}
            audit={opsData.audit}
            integrations={opsData.integrations}
            loading={opsLoading}
          />
        )}
      </div>

      {phase === "onboarding" && <OnboardingScreen onStart={handleStart} />}
    </div>
  );
}
