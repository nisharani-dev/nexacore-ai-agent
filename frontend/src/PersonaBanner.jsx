const PERSONA_COPY = {
  person1: {
    headline: "Person #1 — sparse team memory",
    detail: "Only company-wide basics. Agent is cautious and generic.",
  },
  person10: {
    headline: "Person #10 — rich team memory",
    detail: "9 prior joiners logged blockers, rituals, and exact access paths.",
  },
};

export default function PersonaBanner({ personaMode, memoryCount, prevCount, team }) {
  const copy = PERSONA_COPY[personaMode] || PERSONA_COPY.person1;
  const delta = prevCount != null ? memoryCount - prevCount : null;

  return (
    <div className={`persona-banner persona-banner--${personaMode}`}>
      <div className="persona-banner-main">
        <span className="persona-banner-headline">{copy.headline}</span>
        <span className="persona-banner-detail">{copy.detail}</span>
        {team && <span className="persona-banner-team">team: {team}</span>}
      </div>
      <div className="persona-banner-stat">
        <span className="persona-banner-num">{memoryCount}</span>
        <span className="persona-banner-label">memories</span>
        {delta != null && delta !== 0 && (
          <span className={`persona-banner-delta ${delta > 0 ? "up" : "down"}`}>
            {delta > 0 ? "+" : ""}{delta}
          </span>
        )}
      </div>
    </div>
  );
}
