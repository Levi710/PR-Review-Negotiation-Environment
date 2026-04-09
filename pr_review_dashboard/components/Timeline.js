"use client";

export default function Timeline({ history, isThinking, onExecute, done }) {
  return (
    <div className="chat-thread">
      {(!history || history.length === 0) && !isThinking && (
        <div style={{ fontSize: 13, color: "var(--color-text-secondary)" }}>
          No review activity yet. Click below to start.
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

      {!done && !isThinking && (
        <button className="init-btn" onClick={onExecute} style={{ marginTop: 8 }}>
          ▶ Execute next round
        </button>
      )}

      {done && (
        <div className="status-msg success" style={{ marginTop: 8 }}>
          ✓ Episode complete
        </div>
      )}
    </div>
  );
}
