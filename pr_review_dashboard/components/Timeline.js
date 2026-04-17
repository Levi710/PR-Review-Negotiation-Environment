"use client";
import ManualOverride from "./ManualOverride";

export default function Timeline({
  history = [],
  isThinking,
  onExecute,
  onManual,
  done,
  reviewReady,
  blockedReason,
}) {
  const hasHistory = history.length > 0;

  return (
    <div className="chat-thread">
      {!hasHistory && !isThinking && (
        <div style={{ fontSize: 13, color: "var(--color-text-secondary)", padding: "10px 0" }}>
          No reviewer action yet.
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
                {isReviewer ? "Reviewer" : "Author"} | Turn {Math.ceil((i + 1) / 2)}
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
              <span style={{ marginLeft: 2 }}>Reviewer is thinking...</span>
            </div>
          </div>
        </div>
      )}

      {!done && !isThinking && (
        <div className="review-actions">
          <div className={`step-hint ${reviewReady ? "ready" : "locked"}`}>
            <div className="step-hint-title">Step 4: Continue Review</div>
            <div className="step-hint-text">
              {reviewReady
                ? "Run the reviewer for the next turn, or submit a manual decision if you want to test the environment yourself."
                : blockedReason || "Complete the earlier steps to unlock review actions."}
            </div>
          </div>
          <button className="init-btn active" onClick={onExecute} disabled={!reviewReady}>
            Step 4A: Run AI Review
          </button>
          <ManualOverride
            onSubmit={onManual}
            disabled={done || isThinking || !reviewReady}
            title="Step 4B: Manual Decision"
            helperText="This sends your decision to /step without calling the model."
          />
        </div>
      )}

      {done && (
        <div className="status-msg success" style={{ marginTop: 15 }}>
          Review process concluded
        </div>
      )}
    </div>
  );
}
