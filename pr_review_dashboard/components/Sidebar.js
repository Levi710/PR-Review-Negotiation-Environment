"use client";

export default function Sidebar({
  taskName, setTaskName,
  apiUrl, setApiUrl,
  modelId, setModelId,
  apiKey, setApiKey,
  onInit, initStatus,
  rewards,
  isInternal,
}) {
  const TASKS = [
    { value: "single-pass-review", label: "Easy — single pass review" },
    { value: "iterative-negotiation", label: "Medium — iterative negotiation" },
    { value: "escalation-judgment", label: "Hard — escalation judgment" },
    { value: "custom-review", label: "Custom — your own code" },
  ];

  return (
    <div className="sidebar">
      <div>
        <div className="sidebar-label">Scenario</div>
        <select value={taskName} onChange={e => setTaskName(e.target.value)}>
          {TASKS.map(t => <option key={t.value} value={t.value}>{t.label}</option>)}
        </select>
      </div>

      <div>
        <div className="sidebar-label">API base URL</div>
        <input
          type="text"
          value={apiUrl}
          onChange={e => setApiUrl(e.target.value)}
          disabled={isInternal}
        />
      </div>

      <div>
        <div className="sidebar-label">Model</div>
        <input
          type="text"
          value={modelId}
          onChange={e => setModelId(e.target.value)}
        />
      </div>

      {!isInternal && (
        <div>
          <div className="sidebar-label">API Key</div>
          <input
            type="password"
            value={apiKey}
            onChange={e => setApiKey(e.target.value)}
            placeholder="sk-..."
          />
        </div>
      )}
      {isInternal && (
        <div className="status-msg info">🔒 Secure internal key active</div>
      )}

      <div className="sep" />

      <button
        className={`init-btn ${initStatus === "ready" ? "active" : ""}`}
        onClick={onInit}
        disabled={initStatus === "loading"}
      >
        {initStatus === "loading" ? "Initializing…" : initStatus === "ready" ? "Environment ready" : "Initialize environment"}
      </button>

      <div style={{ marginTop: "auto" }}>
        <div className="sidebar-label" style={{ marginBottom: 8 }}>Reward history</div>
        <RewardChart rewards={rewards} />
      </div>
    </div>
  );
}

function RewardChart({ rewards }) {
  if (!rewards || rewards.length === 0) {
    return <div style={{ fontSize: 11, color: "var(--color-text-tertiary)" }}>No data yet</div>;
  }

  const getColor = (val) => {
    if (val >= 0.7) return "#1a7f3c";
    if (val >= 0.4) return "#ef9f27";
    return "#e24b4a";
  };

  return (
    <div className="reward-chart">
      {rewards.map((r, i) => (
        <div className="chart-row" key={i}>
          <span className="chart-label">T{i + 1}</span>
          <div className="chart-bar-wrap">
            <div className="chart-bar" style={{ width: `${Math.min(r * 100, 100)}%`, background: getColor(r) }} />
          </div>
          <span className="chart-val">{r.toFixed(2)}</span>
        </div>
      ))}
    </div>
  );
}
