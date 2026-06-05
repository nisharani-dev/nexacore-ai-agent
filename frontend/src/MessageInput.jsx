// MessageInput.jsx
// ---------------------------------------------------------------------------
// The text input bar at the bottom of the chat.
// Knows nothing about API or memory — just calls onSend(text) and clears itself.
// ---------------------------------------------------------------------------

import { useState, useRef, useEffect } from "react";

export default function MessageInput({ onSend, disabled }) {
  const [value, setValue] = useState("");
  const textareaRef = useRef(null);

  // Auto-resize textarea up to ~4 lines
  useEffect(() => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = Math.min(el.scrollHeight, 96) + "px";
  }, [value]);

  const handleSend = () => {
    const text = value.trim();
    if (!text || disabled) return;
    onSend(text);
    setValue("");
  };

  const handleKey = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const SUGGESTIONS = [
    "How do I get AWS access?",
    "Which Confluence spaces do I need?",
    "My Jira ticket has been pending 5 days",
    "What should I do first?",
  ];

  return (
    <div className="input-shell">
      {/* quick suggestion chips — only show when input is empty */}
      {value === "" && (
        <div className="suggestions">
          {SUGGESTIONS.map((s) => (
            <button
              key={s}
              className="chip"
              onClick={() => { onSend(s); }}
              disabled={disabled}
            >
              {s}
            </button>
          ))}
        </div>
      )}

      <div className="input-row">
        <textarea
          ref={textareaRef}
          className="msg-textarea"
          placeholder="Ask anything about your onboarding…"
          value={value}
          onChange={(e) => setValue(e.target.value)}
          onKeyDown={handleKey}
          disabled={disabled}
          rows={1}
        />
        <button
          className={`send-btn ${disabled ? "send-btn--loading" : ""}`}
          onClick={handleSend}
          disabled={disabled}
          aria-label="Send message"
        >
          {disabled ? (
            <span className="spinner" />
          ) : (
            <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
              <path d="M2 8h12M8 2l6 6-6 6" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
            </svg>
          )}
        </button>
      </div>
    </div>
  );
}
