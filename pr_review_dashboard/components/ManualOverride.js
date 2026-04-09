"use client";
import { useState } from "react";

export default function ManualOverride({ onSubmit, disabled }) {
  const [comment, setComment] = useState("");
  const [response, setResponse] = useState(null);

  const handleSubmit = async (decision) => {
    if (disabled) return;
    const result = await onSubmit({ decision, comment });
    if (result) setResponse(result);
  };

  return (
    <div>
      <div style={{ fontSize: 13, color: "var(--color-text-secondary)", marginBottom: 12 }}>
        Act as the reviewer. Submit feedback to see how the environment responds.
      </div>
      <textarea
        className="manual-textarea"
        value={comment}
        onChange={e => setComment(e.target.value)}
        placeholder="e.g. I found a potential null pointer issue in line 47…"
      />
      <div className="manual-actions">
        <button className="init-btn" onClick={() => handleSubmit("request_changes")} disabled={disabled}>
          Request changes
        </button>
        <button className="init-btn active" onClick={() => handleSubmit("approve")} disabled={disabled}>
          Approve
        </button>
        <button
          className="init-btn"
          style={{ borderColor: "#856404", color: "#856404" }}
          onClick={() => handleSubmit("escalate")}
          disabled={disabled}
        >
          Escalate
        </button>
      </div>

      {response && (
        <div style={{ marginTop: 14 }}>
          <div className="section-head" style={{ marginBottom: 8 }}>Environment response</div>
          <div className="bubble reviewer" style={{ maxWidth: "100%" }}>
            Reward: {response.reward?.toFixed(2)} | Done: {response.done ? "Yes" : "No"}
          </div>
        </div>
      )}
    </div>
  );
}
