"use client";

export default function Sidebar({
  taskName, setTaskName,
  presets, selectedPreset, setSelectedPreset,
  customApiUrl, setCustomApiUrl,
  customModelId, setCustomModelId,
  customApiKey, setCustomApiKey,
  isInternal,
  onInit, initStatus,
  rewards,
  customTitle, setCustomTitle,
  customDesc, setCustomDesc,
  tasks,
  onOpenCustomReview,
}) {
  const fallbackTasks = [
    { name: "single-pass-review", pr_title: "Fix pagination offset calculation", max_turns: 1 },
    { name: "iterative-negotiation", pr_title: "Add input sanitization to profile update", max_turns: 3 },
    { name: "escalation-judgment", pr_title: "Refactor auth token generation for readability", max_turns: 2 },
    { name: "custom-review", pr_title: "Custom Review Session", max_turns: 3 },
  ];
  const availableTasks = tasks?.length ? tasks : fallbackTasks;
  const preset = presets[selectedPreset] || presets[0];

  return (
    <div className="sidebar">
      <div>
        <div className="sidebar-label">Select review scenario</div>
        <select value={taskName} onChange={e => setTaskName(e.target.value)}>
          {availableTasks.map(t => (
            <option key={t.name} value={t.name}>{t.pr_title || t.name}</option>
          ))}
        </select>
      </div>

      <button className="init-btn secondary" onClick={onOpenCustomReview}>
        Review My Code
      </button>
      <a className="sidebar-link" href="/code">Open `/code` workspace</a>

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
            <div className="sidebar-label">Background info</div>
            <textarea
              style={{ minHeight: "60px" }}
              value={customDesc}
              onChange={e => setCustomDesc(e.target.value)}
              placeholder="Explain the changes..."
            />
          </div>
        </>
      )}

      <div style={{ marginTop: "10px" }}>
        <div className="sidebar-label">Model</div>
        <select value={selectedPreset} onChange={e => setSelectedPreset(parseInt(e.target.value, 10))}>
          {presets.map((p, i) => <option key={i} value={i}>{p.label}</option>)}
        </select>
      </div>

      {preset.id === "custom" && (
        <div className="custom-config">
          <div>
            <div className="sidebar-label">API Base URL</div>
            <input type="text" value={customApiUrl} onChange={e => setCustomApiUrl(e.target.value)} placeholder="https://..." />
          </div>
          <div>
            <div className="sidebar-label">Model ID</div>
            <input type="text" value={customModelId} onChange={e => setCustomModelId(e.target.value)} placeholder="llama3..." />
          </div>
        </div>
      )}

      {!isInternal && (
        <div>
          <div className="sidebar-label">API Key</div>
          <input
            type="password"
            value={customApiKey}
            onChange={e => setCustomApiKey(e.target.value)}
            placeholder="hf_..."
          />
        </div>
      )}

      {isInternal && (
        <div className="status-msg success" style={{ padding: "6px 10px", fontSize: 11, background: "rgba(35, 134, 54, 0.1)" }}>
          Secure key active
        </div>
      )}

      <div className="sep" />

      <button
        className={`init-btn ${initStatus === "loading" ? "loading" : initStatus === "ready" ? "success" : "active"}`}
        onClick={onInit}
        disabled={initStatus === "loading"}
      >
        {initStatus === "loading" ? "Connecting..." :
         initStatus === "ready" ? "System Ready" :
         "Start Session"}
      </button>

      {initStatus === "ready" && (
        <div style={{ marginTop: "10px", fontSize: "11px", color: "#7d8590", textAlign: "center" }}>
          System is live. Run the reviewer or submit a manual decision.
        </div>
      )}

      <div style={{ marginTop: "auto" }}>
        <div className="sidebar-label" style={{ marginBottom: 8 }}>Reward history</div>
        <div className="reward-history">
          {(!rewards || rewards.length === 0) ? (
            <div style={{ fontSize: 11, color: "var(--color-text-secondary)" }}>No data yet</div>
          ) : (
            rewards.map((r, i) => (
              <div key={i} className="reward-bar-wrapper">
                <span className="reward-label">T{i + 1}</span>
                <div className="reward-track">
                  <div
                    className="reward-fill"
                    style={{
                      width: `${Math.max(10, Math.min(100, Math.abs(r) * 100))}%`,
                      background: r >= 0 ? "var(--color-success)" : "var(--color-error)",
                    }}
                  />
                </div>
                <span className="reward-value">{r > 0 ? "+" : ""}{r.toFixed(2)}</span>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}
