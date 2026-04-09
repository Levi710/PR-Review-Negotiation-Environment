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
      {/* Session Config */}
      <div>
        <div className="sidebar-label">Select review scenario</div>
        <select value={taskName} onChange={e => setTaskName(e.target.value)}>
          {TASKS.map(t => <option key={t.value} value={t.value}>{t.label}</option>)}
        </select>
      </div>

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

      {/* Model preset selector */}
      <div style={{ marginTop: '10px' }}>
        <div className="sidebar-label">Model</div>
        <select value={selectedPreset} onChange={e => setSelectedPreset(parseInt(e.target.value))}>
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
          🔒 Secure key active
        </div>
      )}

      <div className="sep" />

      <button 
        className={`init-btn ${initStatus === 'loading' ? 'loading' : initStatus === 'ready' ? 'success' : 'active'}`}
        onClick={onInit}
        disabled={initStatus === 'loading'}
      >
        {initStatus === 'loading' ? 'Connecting...' : 
         initStatus === 'ready' ? '✅ System Ready' : 
         'Test Connection'}
      </button>

      {initStatus === 'ready' && (
        <div style={{ marginTop: '10px', fontSize: '11px', color: '#7d8590', textAlign: 'center' }}>
          System is live. Paste your code in the workspace.
        </div>
      )}

      {/* Reward history at bottom */}
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
                      background: r >= 0 ? "var(--color-success)" : "var(--color-error)"
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
