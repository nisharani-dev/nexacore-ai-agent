// MemoryPanel.jsx
// ---------------------------------------------------------------------------
// Sidebar showing what the agent currently "knows" about this team.
// Pure display — receives `memories` as a prop, knows nothing about API.
// New entries animate in when added mid-conversation.
// ---------------------------------------------------------------------------

const SCOPE_META = {
  company: { label: "company-wide",    color: "scope--company" },
  org:     { label: "engineering org", color: "scope--org"     },
  team:    { label: "team-specific",   color: "scope--team"    },
  role:    { label: "role-specific",   color: "scope--role"    },
};

const TYPE_META = {
  access:    { label: "access",    dot: "dot--teal"   },
  blocker:   { label: "blocker",   dot: "dot--red"    },
  exception: { label: "exception", dot: "dot--amber"  },
  ritual:    { label: "ritual",    dot: "dot--green"  },
};

function MemoryEntry({ entry, isNew }) {
  const type = TYPE_META[entry.type] ?? { label: entry.type, dot: "dot--gray" };
  return (
    <div className={`mem-entry ${isNew ? "mem-entry--new" : ""}`}>
      <div className="mem-entry-top">
        <span className={`mem-dot ${type.dot}`} aria-hidden="true" />
        <span className="mem-type">{type.label}</span>
      </div>
      <p className="mem-text">{entry.text}</p>
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
      <div className="mem-panel-header">
        <div className="mem-panel-title">
          <span className="mem-title-text">memory</span>
          <span className="mem-persona-tag">{personaLabel}</span>
        </div>
        <div className="mem-stat">
          <span className="mem-count">{total}</span>
          <span className="mem-count-label">entries</span>
        </div>

        {/* type legend */}
        <div className="mem-legend">
          {Object.entries(TYPE_META).map(([k, v]) => (
            <div key={k} className="legend-row">
              <span className={`mem-dot ${v.dot}`} aria-hidden="true" />
              <span>{v.label}</span>
            </div>
          ))}
        </div>
      </div>

      <div className="mem-panel-body">
        {scopes.map((sc) => {
          const entries = grouped[sc];
          if (!entries.length) return null;
          const meta = SCOPE_META[sc];
          return (
            <div key={sc} className="mem-group">
              <div className={`mem-scope-label ${meta.color}`}>
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
