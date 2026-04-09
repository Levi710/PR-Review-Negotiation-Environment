"use client";

export default function MetricCards({ score, turn, maxTurns, status, statusSub }) {
  const pct = Math.min((score / (maxTurns * 0.8)) * 100, 100);

  return (
    <div className="metrics">
      <div className="metric-card">
        <div className="m-label">Cumulative reward</div>
        <div className="m-val">{score.toFixed(2)}</div>
        <div className="progress-bar">
          <div className="progress-fill" style={{ width: `${pct}%` }} />
        </div>
      </div>
      <div className="metric-card">
        <div className="m-label">Turn</div>
        <div className="m-val">
          {turn} <span style={{ fontSize: 14, color: "var(--color-text-tertiary)" }}>/ {maxTurns}</span>
        </div>
        <div className="m-sub">
          {status === "Running" ? "Reviewer processing…" : status === "Complete" ? "Episode finished" : "Waiting…"}
        </div>
      </div>
      <div className="metric-card">
        <div className="m-label">Episode status</div>
        <div className="m-val" style={{ fontSize: 14, fontWeight: 500, paddingTop: 4 }}>{status}</div>
        <div className="m-sub">{statusSub}</div>
      </div>
    </div>
  );
}
