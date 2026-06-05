// MemoryPanel.jsx
// ---------------------------------------------------------------------------
// Sidebar showing what the agent currently "knows" about this team.
// Pure display — receives `memories` as a prop, knows nothing about API.
// New entries animate in when added mid-conversation.
// ---------------------------------------------------------------------------

const SCOPE_META = {
  company: { label: "company-wide" },
  org:     { label: "engineering org" },
  team:    { label: "team-specific" },
  role:    { label: "role-specific" },
};

const TYPE_META = {
  access:    { label: "access",    dot: "ldot--access"    },
  blocker:   { label: "blocker",   dot: "ldot--blocker"   },
  exception: { label: "exception", dot: "ldot--exception" },
  ritual:    { label: "ritual",    dot: "ldot--ritual"    },
};

function MemoryEntry({ entry, isNew }) {
  const type = TYPE_META[entry.type] ?? { label: entry.type, dot: "" };
  return (
    <div className={`mem-card ${isNew ? "mem-card--new" : ""}`}>
      <div className="mem-card-type">
        <span className={`mem-type-dot mem-type-dot--${entry.type}`} aria-hidden="true" />
        <span className="mem-type-label">{type.label}</span>
      </div>
      <p className="mem-card-text">{entry.text}</p>
    </div>
  );
}

export default function MemoryPanel({ memories, personaLabel, newMemoryIds }) {
  const scopes = ["company", "org", "team", "role"];

  const grouped = scopes.reduce((acc, sc) => {
    acc[sc] = memories.filter((m) => m.scope === sc);
    return acc;
  }, {});

  const total = memories.length;

  return (
    <aside className="mem-panel" aria-label="Agent memory panel">
      <div className="mem-header">
        <div className="mem-header-top">
          <div>
            <div className="mem-title">memory</div>
            <div className="mem-big-num">{total}</div>
            <div className="mem-num-label">entries</div>
          </div>
          <span className="mem-persona-badge">{personaLabel}</span>
        </div>

        <div className="mem-legend">
          {Object.entries(TYPE_META).map(([k, v]) => (
            <div key={k} className="legend-item">
              <span className={`ldot ${v.dot}`} aria-hidden="true" />
              <span>{v.label}</span>
            </div>
          ))}
        </div>
      </div>

      <div className="mem-body">
        {scopes.map((sc) => {
          const entries = grouped[sc];
          if (!entries.length) return null;
          const meta = SCOPE_META[sc];
          return (
            <div key={sc} className="mem-group">
              <div className={`mem-scope mem-scope--${sc}`}>
                {meta.label}
              </div>
              {entries.map((entry, i) => (
                <MemoryEntry
                  key={`${sc}-${i}`}
                  entry={entry}
                  isNew={newMemoryIds?.has(`${entry.scope}-${entry.text}`)}
                />
              ))}
            </div>
          );
        })}

        {total === 0 && (
          <div className="mem-empty">
            <p>No memories yet.</p>
            <span>They build up as people onboard.</span>
          </div>
        )}
      </div>
    </aside>
  );
}
