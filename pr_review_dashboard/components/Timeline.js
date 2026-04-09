"use client";

export default function Timeline({ history, isThinking, onExecute, onManual, done }) {
  const hasHistory = history && history.length > 0;

  return (
    <div className="chat-thread">
      {(!hasHistory) && !isThinking && (
        <div style={{ fontSize: 13, color: "var(--color-text-secondary)", padding: '10px 0' }}>
          Initializing review session...
        </div>
      )}

      {history.map((item, i) => {
        const isReviewer = item.role === "reviewer";
        return (
          <div key={i} className={`chat-msg ${isReviewer ? "" : "author"}`}>
            <div className={`avatar ${isReviewer ? "reviewer" : "author"}`}>
              {isReviewer ? "AI" : "Env"}
            </div>
            <div>
              <div className={`bubble ${isReviewer ? "reviewer" : "author"}`}>
                {item.content}
              </div>
              <div className="chat-meta" style={isReviewer ? {} : { textAlign: "right" }}>
                {isReviewer ? "Reviewer" : "Author"} · Turn {Math.ceil((i + 1) / 2)}
              </div>
            </div>
          </div>
        );
      })}

      {isThinking && (
        <div className="chat-msg">
          <div className="avatar reviewer pulse">AI</div>
          <div>
            <div className="thinking">
              <div className="dot" />
              <div className="dot" />
              <div className="dot" />
              <span style={{ marginLeft: 2 }}>Reviewer is thinking…</span>
            </div>
          </div>
        </div>
      )}

      {/* Primary Actions Stage */}
      {!done && !isThinking && hasHistory && (
        <div style={{ marginTop: 15, display: 'flex', gap: '10px', flexDirection: 'column' }}>
          <div className="sidebar-label" style={{ fontSize: '11px', color: '#7d8590' }}>Final Verdict</div>
          <div style={{ display: 'flex', gap: '8px' }}>
            <button 
              className="init-btn success" 
              style={{ flex: 1, padding: '8px' }}
              onClick={() => onManual({ decision: "approve", comment: "I accept these changes." })}
            >
              ✅ Accept PR
            </button>
            <button 
              className="init-btn error" 
              style={{ flex: 1, padding: '8px' }}
              onClick={() => onManual({ decision: "request_changes", comment: "Rejecting. More fixes needed." })}
            >
              ❌ Reject PR
            </button>
          </div>
          <button className="init-btn" onClick={onExecute} style={{ fontSize: '11px', opacity: 0.8 }}>
            🔄 Re-run AI Review
          </button>
        </div>
      )}

      {/* Initial Execute Button (If no history) */}
      {!done && !isThinking && !hasHistory && (
        <button className="init-btn active" onClick={onExecute} style={{ marginTop: 8 }}>
          ▶ Start AI Review Round
        </button>
      )}

      {done && (
        <div className="status-msg success" style={{ marginTop: 15 }}>
          ✓ Review process concluded
        </div>
      )}
    </div>
  );
}
