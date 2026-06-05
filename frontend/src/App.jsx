// App.jsx
// ---------------------------------------------------------------------------
// Root component. Owns all state:
//   - messages (chat history)
//   - memories (what the agent knows)
//   - userContext (name, team, role, employment type)
//   - personaMode ("person1" | "person10") — demo toggle
//   - phase ("onboarding" | "chat")
//
// Passes state + setters down as props. This is the ONLY file that imports api.js
// ---------------------------------------------------------------------------

import { useState, useCallback, useRef } from "react";
import ChatWindow from "./ChatWindow";
import MessageInput from "./MessageInput";
import MemoryPanel from "./MemoryPanel";
import { sendMessage, getMemories } from "./api";
import { MOCK_PERSONAS } from "./mock_responses";

const TEAMS = [
  { value: "platform-eng",  label: "Engineering → Platform Engineering" },
  { value: "infra-sec",     label: "Engineering → Platform → Infra Security" },
  { value: "data-eng",      label: "Engineering → Data Engineering" },
  { value: "finance-ops",   label: "Finance → Finance Ops" },
];

const ROLES = [
  { value: "SDE Intern",        label: "SDE Intern" },
  { value: "SDE-1",             label: "SDE-1 / Junior Engineer" },
  { value: "SDE-2",             label: "SDE-2 / Mid Engineer" },
  { value: "Staff Engineer",    label: "Staff Engineer" },
  { value: "Engineering Manager", label: "Engineering Manager" },
];

const EMPLOYMENT_TYPES = [
  { value: "FTE",        label: "Full-time employee (FTE)" },
  { value: "contractor", label: "Contractor" },
  { value: "intern",     label: "Intern" },
];

function makeId() {
  return Math.random().toString(36).slice(2, 9);
}

function nowTime() {
  return new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

// ---------------------------------------------------------------------------
// Onboarding screen
// ---------------------------------------------------------------------------
function OnboardingScreen({ onStart }) {
  const [name, setName] = useState("");
  const [team, setTeam] = useState("platform-eng");
  const [role, setRole] = useState("SDE-1");
  const [empType, setEmpType] = useState("FTE");

  return (
    <div className="ob-overlay">
      <div className="ob-card">
        <div className="ob-logo">
          <span className="ob-dot" />
          RAMP
        </div>
        <p className="ob-sub">// your onboarding agent</p>

        <div className="ob-field">
          <label className="ob-label">your name</label>
          <input
            className="ob-input"
            placeholder="e.g. Priya Sharma"
            value={name}
            onChange={(e) => setName(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && name.trim() && onStart({ name, team, role, empType })}
          />
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

        <button
          className="ob-btn"
          disabled={!name.trim()}
          onClick={() => onStart({ name, team, role, empType })}
        >
          begin onboarding →
        </button>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// App
// ---------------------------------------------------------------------------
export default function App() {
  const [phase, setPhase] = useState("onboarding"); // "onboarding" | "chat"
  const [personaMode, setPersonaMode] = useState("person1");
  const [messages, setMessages] = useState([]);
  const [memories, setMemories] = useState([]);
  const [newMemIds, setNewMemIds] = useState(new Set());
  const [isTyping, setIsTyping] = useState(false);
  const [userContext, setUserContext] = useState(null);

  const handleStart = useCallback(async ({ name, team, role, empType }) => {
    const ctx = { name, team, role, employmentType: empType, personaMode };
    setUserContext(ctx);
    setPhase("chat");

    // load initial memories
    const mems = await getMemories(team, personaMode);
    setMemories(mems);

    // first agent greeting
    setIsTyping(true);
    const res = await sendMessage("hello", { ...ctx, personaMode });
    setIsTyping(false);
    setMessages([{
      id: makeId(), role: "agent", text: res.reply,
      memoryUsed: res.memory_used, time: nowTime(), animate: true,
    }]);
  }, [personaMode]);

  const handleSend = useCallback(async (text) => {
    if (isTyping) return;

    // add user message
    const userMsg = { id: makeId(), role: "user", text, time: nowTime(), animate: true };
    setMessages((prev) => [...prev, userMsg]);
    setIsTyping(true);

    try {
      const res = await sendMessage(text, { ...userContext, personaMode });
      setIsTyping(false);

      // add agent message
      const agentMsg = {
        id: makeId(), role: "agent", text: res.reply,
        memoryUsed: res.memory_used, time: nowTime(), animate: true,
      };
      setMessages((prev) => [...prev, agentMsg]);

      // handle new memories written by agent
      if (res.new_memories?.length) {
        const ids = new Set(res.new_memories.map((m) => `${m.scope}-${m.text}`));
        setNewMemIds(ids);
        setMemories((prev) => [...prev, ...res.new_memories]);
        setTimeout(() => setNewMemIds(new Set()), 3000);
      }
    } catch (err) {
      setIsTyping(false);
      setMessages((prev) => [...prev, {
        id: makeId(), role: "agent",
        text: "Something went wrong connecting to the backend. Check the console.",
        memoryUsed: false, time: nowTime(), animate: true,
      }]);
    }
  }, [isTyping, userContext, personaMode]);

  // when demo mode is toggled, reload memories for the new persona
  const handlePersonaToggle = useCallback(async (mode) => {
    setPersonaMode(mode);
    if (phase === "chat" && userContext) {
      const mems = await getMemories(userContext.team, mode);
      setMemories(mems);
    }
  }, [phase, userContext]);

  const personaLabel = MOCK_PERSONAS[personaMode]?.label ?? personaMode;

  return (
    <div className="app">
      {/* top bar */}
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

        <div className="demo-toggle" role="group" aria-label="Demo persona toggle">
          <span className="demo-label">demo</span>
          <button
            className={`demo-btn ${personaMode === "person1" ? "demo-btn--active" : ""}`}
            onClick={() => handlePersonaToggle("person1")}
          >
            person #1
          </button>
          <button
            className={`demo-btn ${personaMode === "person10" ? "demo-btn--active" : ""}`}
            onClick={() => handlePersonaToggle("person10")}
          >
            person #10
          </button>
        </div>
      </header>

      {/* main layout */}
      <div className="main">
        <div className="chat-col">
          <ChatWindow
            messages={messages}
            isTyping={isTyping}
            userName={userContext?.name}
          />
          <MessageInput onSend={handleSend} disabled={isTyping || phase === "onboarding"} />
        </div>

        <MemoryPanel
          memories={memories}
          personaLabel={personaLabel}
          newMemoryIds={newMemIds}
        />
      </div>

      {phase === "onboarding" && <OnboardingScreen onStart={handleStart} />}
    </div>
  );
}
