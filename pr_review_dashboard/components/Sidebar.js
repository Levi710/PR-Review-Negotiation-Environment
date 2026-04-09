"use client";

export default function Sidebar({
  taskName, setTaskName,
  customDiff, setCustomDiff,
  customTitle, setCustomTitle,
  customDesc, setCustomDesc,
  presets, selectedPreset, setSelectedPreset,
  customApiUrl, setCustomApiUrl,
  customModelId, setCustomModelId,
  customApiKey, setCustomApiKey,
  isInternal,
  onInit, initStatus,
  rewards,
}) {
  const TASKS = [
    { value: "single-pass-review", label: "Easy — single pass review" },
    { value: "iterative-negotiation", label: "Medium — iterative negotiation" },
    { value: "escalation-judgment", label: "Hard — escalation judgment" },
    { value: "custom-review", label: "Custom — your own code" },
  ];

  const preset = presets[selectedPreset] || presets[0];

  return (
    <div className="sidebar">
      {/* Task selector */}
      <div>
        <div className="sidebar-label">Task difficulty</div>
        <select value={taskName} onChange={e => setTaskName(e.target.value)}>
          {TASKS.map(t => <option key={t.value} value={t.value}>{t.label}</option>)}
        </select>
      </div>

      {/* Custom Task Inputs — Only for Custom Review */}
      {taskName === "custom-review" && (
        <>
          <div>
            <div className="sidebar-label">PR Title</div>
            <input
              type="text"
              value={customTitle}
              onChange={e => setCustomTitle(e.target.value)}
              placeholder="Fix widget logic..."
            />
          </div>
          <div>
            <div className="sidebar-label">PR Description</div>
            <textarea
              style={{ minHeight: "60px" }}
              value={customDesc}
              onChange={e => setCustomDesc(e.target.value)}
              placeholder="Explain the changes..."
            />
          </div>
          <div>
            <div className="sidebar-label">Custom Diff (write here)</div>
            <textarea
              style={{ minHeight: "120px", fontFamily: "var(--font-mono)", fontSize: "11px" }}
              value={customDiff}
              onChange={e => setCustomDiff(e.target.value)}
              placeholder="--- a/file.py\n+++ b/file.py\n@@ -1,1 +1,1 @@\n-old\n+new"
            />
          </div>
        </>
      )}

      {/* Model preset selector */}
      <div>
        <div className="sidebar-label">Model</div>
        <select
          value={selectedPreset}
          onChange={e => setSelectedPreset(Number(e.target.value))}
        >
          {presets.map((p, i) => (
            <option key={i} value={i}>{p.label}</option>
          ))}
        </select>
      </div>

      {/* API URL — shown for non-internal, non-custom */}
      {!isInternal && (
        <div>
          <div className="sidebar-label">API base URL</div>
          <input
            type="text"
            value={preset.id === "custom" ? customApiUrl : preset.url}
            onChange={e => setCustomApiUrl(e.target.value)}
            disabled={preset.id !== "custom"}
          />
        </div>
      )}

      {/* Model ID — editable only for custom */}
      {preset.id === "custom" && (
        <div>
          <div className="sidebar-label">Model ID</div>
          <input
            type="text"
            value={customModelId}
            onChange={e => setCustomModelId(e.target.value)}
            placeholder="e.g. gpt-4o"
          />
        </div>
      )}

      {/* API Key — hidden for internal presets */}
      {!isInternal && (
        <div>
          <div className="sidebar-label">API Key</div>
          <input
            type="password"
            value={customApiKey}
            onChange={e => setCustomApiKey(e.target.value)}
            placeholder="sk-..."
          />
        </div>
      )}
      {isInternal && (
        <div className="status-msg info">🔒 Secure key active</div>
      )}

      <div className="sep" />

      <button
        className={`init-btn ${initStatus === "ready" ? "active" : ""}`}
        onClick={onInit}
        disabled={initStatus === "loading"}
      >
        {initStatus === "loading" ? "Initializing…" : initStatus === "ready" ? "Environment ready" : "Initialize environment"}
      </button>

      {/* Reward history at bottom */}
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
