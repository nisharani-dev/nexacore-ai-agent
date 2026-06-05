// OpsPanel.jsx — tickets, reminders, audit trail

export default function OpsPanel({ tickets, reminders, audit, integrations, loading }) {
  return (
    <aside className="ops-panel" aria-label="Operations panel">
      <div className="ops-header">
        <span className="ops-title">operations</span>
        {integrations && (
          <span className={`ops-mode ops-mode--${integrations.mode}`}>
            {integrations.label}
          </span>
        )}
      </div>

      {loading ? (
        <div className="ops-loading">loading…</div>
      ) : (
        <div className="ops-body">
          <section className="ops-section">
            <h3 className="ops-section-title">tickets ({tickets.length})</h3>
            {tickets.slice(0, 5).map((t) => (
              <div key={t.id} className="ops-row">
                <span className="ops-row-title">{t.title}</span>
                <span className="ops-row-meta">{t.status} · {t.priority}</span>
              </div>
            ))}
            {tickets.length === 0 && <p className="ops-empty">No tickets yet</p>}
          </section>

          <section className="ops-section">
            <h3 className="ops-section-title">reminders ({reminders.length})</h3>
            {reminders.slice(0, 5).map((r) => (
              <div key={r.id} className="ops-row">
                <span className="ops-row-title">{r.message}</span>
                <span className="ops-row-meta">{r.recipient}</span>
              </div>
            ))}
            {reminders.length === 0 && <p className="ops-empty">No reminders yet</p>}
          </section>

          <section className="ops-section">
            <h3 className="ops-section-title">recent audit</h3>
            {audit.slice(0, 6).map((e) => (
              <div key={e.id} className="ops-row ops-row--audit">
                <span className="ops-row-title">{e.event_type}</span>
                <span className="ops-row-meta">{e.created_at?.slice(0, 19)}</span>
              </div>
            ))}
          </section>
        </div>
      )}
    </aside>
  );
}
