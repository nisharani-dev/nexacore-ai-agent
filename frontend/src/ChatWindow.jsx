// ChatWindow.jsx
// ---------------------------------------------------------------------------
// Renders the message list. Pure display — receives `messages` as a prop.
// Knows nothing about API. If a message has memoryUsed: true, shows the badge.
// ---------------------------------------------------------------------------

import { useEffect, useRef } from "react";
import FeedbackBar from "./FeedbackBar";

// Parse agent replies into semantic sections (cards, chips, steps)
function formatReply(text) {
  const lines = text.split("\n").filter(Boolean);
  const sections = [];
  let currentList = null;
  let inCodeBlock = false;
  let codeBlockContent = [];
  let codeBlockLang = "";

  for (const line of lines) {
    const t = line.trim();

    if (t.startsWith("```")) {
      if (!inCodeBlock) {
        inCodeBlock = true;
        codeBlockLang = t.slice(3).trim() || "text";
        codeBlockContent = [];
        currentList = null;
      } else {
        sections.push({
          type: "code",
          lang: codeBlockLang,
          text: codeBlockContent.join("\n"),
        });
        inCodeBlock = false;
        codeBlockContent = [];
        codeBlockLang = "";
      }
      continue;
    }

    if (inCodeBlock) {
      codeBlockContent.push(line);
      continue;
    }

    const stepMatch = t.match(/^(\d+)\.\s+(.+)/);
    if (stepMatch) {
      if (!currentList || currentList.type !== "steps") {
        currentList = { type: "steps", items: [] };
        sections.push(currentList);
      }
      currentList.items.push({ num: stepMatch[1], text: stepMatch[2] });
      continue;
    }

    if (t.match(/^[•\-\*]\s/)) {
      if (!currentList || currentList.type !== "bullets") {
        currentList = { type: "bullets", items: [] };
        sections.push(currentList);
      }
      currentList.items.push(t.replace(/^[•\-\*]\s+/, ""));
      continue;
    }

    currentList = null;

    if (t.match(/^\*\*(.+)\*\*$/) || t.startsWith("##")) {
      sections.push({
        type: "label",
        text: t.replace(/\*\*/g, "").replace(/^#+\s*/, ""),
      });
      continue;
    }

    if (t.length > 0) {
      sections.push({ type: "para", text: t });
    }
  }

  return sections.map((s, i) => {
    if (s.type === "para") {
      return <p key={i} className="rp-para">{formatInline(s.text)}</p>;
    }
    if (s.type === "label") {
      return <div key={i} className="rp-label">{s.text}</div>;
    }
    if (s.type === "bullets") {
      return (
        <div key={i} className="rp-chips">
          {s.items.map((item, j) => (
            <span key={j} className="rp-chip">{formatInline(item)}</span>
          ))}
        </div>
      );
    }
    if (s.type === "steps") {
      return (
        <div key={i} className="rp-steps">
          {s.items.map((item, j) => (
            <div key={j} className="rp-step">
              <span className="rp-step-num">{item.num}</span>
              <span className="rp-step-text">{formatInline(item.text)}</span>
            </div>
          ))}
        </div>
      );
    }
    if (s.type === "code") {
      return (
        <pre key={i} className="code-block">
          <div className="code-block-header">
            <span className="code-block-lang">{s.lang}</span>
            <button
              className="code-copy-btn"
              onClick={() => navigator.clipboard.writeText(s.text)}
              title="Copy code"
            >
              copy
            </button>
          </div>
          <code className={`language-${s.lang}`}>{s.text}</code>
        </pre>
      );
    }
    return null;
  });
}

// Format inline elements (bold, italic, code, links)
function formatInline(text) {
  const parts = [];
  let current = "";
  let i = 0;

  while (i < text.length) {
    // Code (backticks)
    if (text[i] === "`") {
      if (current) {
        parts.push(current);
        current = "";
      }
      let codeContent = "";
      i++;
      while (i < text.length && text[i] !== "`") {
        codeContent += text[i];
        i++;
      }
      parts.push(
        <code key={`code-${parts.length}`} className="inline-code">
          {codeContent}
        </code>
      );
      i++;
      continue;
    }

    // Bold (**text**)
    if (text.slice(i, i + 2) === "**") {
      if (current) {
        parts.push(current);
        current = "";
      }
      let boldContent = "";
      i += 2;
      while (i < text.length && text.slice(i, i + 2) !== "**") {
        boldContent += text[i];
        i++;
      }
      parts.push(
        <strong key={`bold-${parts.length}`} className="reply-bold">
          {boldContent}
        </strong>
      );
      i += 2;
      continue;
    }

    // Links [text](url)
    if (text[i] === "[") {
      const linkMatch = text.slice(i).match(/^\[([^\]]+)\]\(([^)]+)\)/);
      if (linkMatch) {
        if (current) {
          parts.push(current);
          current = "";
        }
        parts.push(
          <a
            key={`link-${parts.length}`}
            href={linkMatch[2]}
            className="reply-link"
            target="_blank"
            rel="noopener noreferrer"
          >
            {linkMatch[1]}
          </a>
        );
        i += linkMatch[0].length;
        continue;
      }
    }

    current += text[i];
    i++;
  }

  if (current) {
    parts.push(current);
  }

  return parts.length > 0 ? parts : text;
}

// Typing indicator
function TypingBubble() {
  return (
    <div className="msg msg--agent">
      <div className="msg-avatar msg-avatar--agent">R</div>
      <div className="bubble bubble--agent">
        <div className="typing-dots">
          <span /><span /><span />
        </div>
      </div>
    </div>
  );
}

export default function ChatWindow({ messages, isTyping, userName, sessionId, team }) {
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

          <div className={`bubble bubble--${msg.role} ${msg.memoryUsed ? "bubble--has-memory" : ""}`}>
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
              <>
                <div className="reply-body">
                  {formatReply(msg.text)}
                </div>
                {msg.toolsUsed?.length > 0 && (
                  <details className="tools-taken">
                    <summary>Actions taken ({msg.toolsUsed.length})</summary>
                    <ul className="tools-taken-list">
                      {msg.toolsUsed.map((tool, i) => (
                        <li key={i}>{tool}</li>
                      ))}
                    </ul>
                  </details>
                )}
                {msg.suggestedActions?.length > 0 && (
                  <div className="action-cards">
                    {msg.suggestedActions.map((action, i) => (
                      <div key={i} className="action-card">
                        <span className="action-card-icon">⚡</span>
                        <span className="action-card-text">{action}</span>
                      </div>
                    ))}
                  </div>
                )}
                {msg.feedbackQuery && (
                  <div className="feedback-slot">
                    <FeedbackBar sessionId={sessionId} team={team} query={msg.feedbackQuery} />
                  </div>
                )}
              </>
            ) : (
              <p className="user-text">{msg.text}</p>
            )}

            {msg.integrationsMode && (
              <span className={`integration-badge integration-badge--${msg.integrationsMode}`}>
                {msg.integrationsMode === "live" ? "live integration" : "mock integration"}
              </span>
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
