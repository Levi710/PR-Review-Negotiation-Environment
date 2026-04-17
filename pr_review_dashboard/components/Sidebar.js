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
  modelConfigured,
  modelBlockedReason,
  showComposer,
  initialized,
  done,
  reviewStarted,
}) {
  const fallbackTasks = [
    { name: "single-pass-review", pr_title: "Fix pagination offset calculation", max_turns: 1 },
    { name: "iterative-negotiation", pr_title: "Add input sanitization to profile update", max_turns: 3 },
    { name: "escalation-judgment", pr_title: "Refactor auth token generation for readability", max_turns: 2 },
    { name: "custom-review", pr_title: "Custom Review Session", max_turns: 3 },
  ];
  const availableTasks = tasks?.length ? tasks : fallbackTasks;
  const preset = presets[selectedPreset] || presets[0];
  const isCustomTask = taskName === "custom-review";
  const usingCustomEndpoint = preset.id === "custom";
  const sessionReady = initStatus === "ready";
  const keyPlaceholder = usingCustomEndpoint ? "Optional bearer token" : preset.url?.includes("groq.com") ? "gsk_..." : "hf_...";

  const workflowSteps = isCustomTask
    ? [
        {
          title: "Choose review type",
          detail: "Select Custom Review Session and describe the snippet if needed.",
          status: "done",
        },
        {
          title: "Configure reviewer access",
          detail: modelConfigured ? "Model, endpoint, and required credentials are ready." : modelBlockedReason,
          status: modelConfigured ? "done" : "active",
        },
        {
          title: "Open the code workspace",
          detail: sessionReady ? "Workspace unlocked. Step 4 is ready below." : "Click the Step 3 button after Step 2 is complete.",
          status: sessionReady ? "done" : modelConfigured ? "active" : "locked",
        },
        {
          title: "Paste code and run review",
          detail: done ? "Review complete." : reviewStarted ? "Results are on screen." : "Use the editor in the main panel.",
          status: done ? "done" : sessionReady ? "active" : "locked",
        },
      ]
    : [
        {
          title: "Choose benchmark scenario",
          detail: "Pick the benchmark task you want to run.",
          status: "done",
        },
        {
          title: "Configure reviewer access",
          detail: modelConfigured ? "Model and credentials are ready." : modelBlockedReason,
          status: modelConfigured ? "done" : "active",
        },
        {
          title: "Load benchmark session",
          detail: initialized ? "Scenario loaded from the environment." : "Click the Step 3 button after Step 2 is complete.",
          status: initialized ? "done" : modelConfigured ? "active" : "locked",
        },
        {
          title: "Run the next review turn",
          detail: done ? "Review complete." : reviewStarted ? "Use Step 4A or Step 4B in the timeline." : "Review actions unlock after Step 3.",
          status: done ? "done" : initialized ? "active" : "locked",
        },
      ];

  const actionLabel = sessionReady
    ? isCustomTask
      ? "Step 3 Complete: Workspace Ready"
      : "Step 3 Complete: Session Loaded"
    : isCustomTask
      ? "Step 3: Open Code Workspace"
      : "Step 3: Load Benchmark Session";

  const actionHelp = !modelConfigured
    ? `Locked until Step 2 is complete. ${modelBlockedReason}`
    : sessionReady
      ? isCustomTask
        ? "The code editor is unlocked below. Use Step 4 to submit your snippet."
        : "The benchmark is loaded. Use Step 4 in the timeline to continue."
      : isCustomTask
        ? "This unlocks the custom editor and enables the Step 4 review button."
        : "This calls /reset for the selected benchmark and unlocks Step 4.";

  return (
    <div className="sidebar">
      <div className="workflow-card">
        <div className="sidebar-label">Workflow</div>
        <div className="workflow-list">
          {workflowSteps.map((step, index) => (
            <div key={step.title} className={`workflow-step ${step.status}`}>
              <div className="workflow-step-index">{index + 1}</div>
              <div className="workflow-step-copy">
                <div className="workflow-step-title">{step.title}</div>
                <div className="workflow-step-text">{step.detail}</div>
              </div>
            </div>
          ))}
        </div>
      </div>

      <div>
        <div className="sidebar-label">Step 1: Select review scenario</div>
        <select value={taskName} onChange={e => setTaskName(e.target.value)}>
          {availableTasks.map(t => (
            <option key={t.name} value={t.name}>{t.pr_title || t.name}</option>
          ))}
        </select>
      </div>

      {isCustomTask && (
        <>
          <div>
            <div className="sidebar-label">Step 1A: PR title</div>
            <input
              type="text"
              value={customTitle}
              onChange={e => setCustomTitle(e.target.value)}
              placeholder="Fix widget logic..."
            />
          </div>
          <div>
            <div className="sidebar-label">Step 1B: Background info</div>
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
        <div className="sidebar-label">Step 2: Reviewer model</div>
        <select value={selectedPreset} onChange={e => setSelectedPreset(parseInt(e.target.value, 10))}>
          {presets.map((p, i) => <option key={i} value={i}>{p.label}</option>)}
        </select>
      </div>

      <div className="status-msg info sidebar-note">
        {usingCustomEndpoint
          ? "Bring your own OpenAI-compatible endpoint. Step 2 is complete after you enter the base URL and model ID."
          : preset.url?.includes("huggingface.co")
            ? "This uses the Hugging Face router. If that provider returns 404, switch to Groq or supply a Custom Endpoint."
            : "This preset uses an OpenAI-compatible hosted endpoint."}
      </div>

      {usingCustomEndpoint && (
        <div className="custom-config">
          <div>
            <div className="sidebar-label">API Base URL</div>
            <input type="text" value={customApiUrl} onChange={e => setCustomApiUrl(e.target.value)} placeholder="https://..." />
          </div>
          <div>
            <div className="sidebar-label">Model ID</div>
            <input type="text" value={customModelId} onChange={e => setCustomModelId(e.target.value)} placeholder="gpt-4.1-mini" />
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
            placeholder={keyPlaceholder}
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
        disabled={initStatus === "loading" || !modelConfigured || initStatus === "ready"}
      >
        {initStatus === "loading" ? "Step 3: Working..." : actionLabel}
      </button>

      <div className="sidebar-action-text">{actionHelp}</div>

      {isCustomTask && !showComposer && (
        <a className="sidebar-link" href="/code">Prefer a direct editor route? Open `/code`.</a>
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
