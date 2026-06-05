// ChatWindow.jsx
// ---------------------------------------------------------------------------
// Renders the message list. Pure display — receives `messages` as a prop.
// Knows nothing about API. If a message has memoryUsed: true, shows the badge.
// ---------------------------------------------------------------------------

import { useEffect, useRef } from "react";

// Format agent reply: detect bullet lines, code-style spans, line breaks
function formatReply(text) {
  return text.split("\n").map((line, i) => {
    if (line.startsWith("•")) {
      return (
        <li key={i} className="reply-bullet">
          {line.slice(1).trim()}
        </li>
      );
    }
    if (/^\d+\./.test(line)) {
      return (
        <li key={i} className="reply-numbered">
          {line.replace(/^\d+\.\s*/, "")}
        </li>
      );
    }
    if (line.trim() === "") return <br key={i} />;
    // inline code-style: words separated by dots treated as paths/channels
    const parts = line.split(/(`[^`]+`)/g);
    return (
      <p key={i} className="reply-line">
        {parts.map((part, j) =>
          part.startsWith("`") && part.endsWith("`") ? (
            <code key={j} className="inline-code">{part.slice(1, -1)}</code>
          ) : part
        )}
      </p>
    );
  });
}

// Typing indicator
function TypingBubble() {
  return (
    <div className="msg msg--agent">
      <div className="msg-avatar">R</div>
      <div className="bubble bubble--agent">
        <div className="typing-dots">
          <span /><span /><span />
        </div>
      </div>
    </div>
  );
}

export default function ChatWindow({ messages, isTyping, userName }) {
  const bottomRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isTyping]);

  const initials = userName
    ? userName.split(" ").map((w) => w[0]).join("").slice(0, 2).toUpperCase()
    : "U";

  return (
    <div className="chat-window" role="log" aria-live="polite" aria-label="Conversation">
      {messages.length === 0 && (
        <div className="empty-state">
          <div className="empty-icon">◈</div>
          <p>Ask anything about your onboarding</p>
          <span>I get smarter with every person who joins</span>
        </div>
      )}

      {messages.map((msg) => (
        <div
          key={msg.id}
          className={`msg msg--${msg.role} ${msg.animate ? "msg--new" : ""}`}
        >
          {msg.role === "agent" && (
            <div className="msg-avatar msg-avatar--agent">R</div>
          )}

          <div className={`bubble bubble--${msg.role}`}>
            {msg.role === "agent" && (
              <div className="bubble-meta">
                <span className="bubble-sender">ramp</span>
                {msg.memoryUsed && (
                  <span className="mem-badge" title="Response drew from team memory">
                    <span className="mem-badge-dot" />
                    memory used
                  </span>
                )}
              </div>
            )}

            {msg.role === "agent" ? (
              <div className="reply-body">
                {formatReply(msg.text)}
              </div>
            ) : (
              <p className="user-text">{msg.text}</p>
            )}

            <span className="bubble-time">{msg.time}</span>
          </div>

          {msg.role === "user" && (
            <div className="msg-avatar msg-avatar--user">{initials}</div>
          )}
        </div>
      ))}

      {isTyping && <TypingBubble />}
      <div ref={bottomRef} />
    </div>
  );
}
