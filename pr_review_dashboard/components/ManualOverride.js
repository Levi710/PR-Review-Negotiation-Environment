"use client";
import { useState } from "react";

export default function ManualOverride({ onSubmit, disabled }) {
  const [decision, setDecision] = useState("request_changes");
  const [issueCategory, setIssueCategory] = useState("security");
  const [comment, setComment] = useState("");
  const [response, setResponse] = useState(null);

  const handleSubmit = async () => {
    if (disabled) return;
    const result = await onSubmit({
      decision,
      issue_category: issueCategory,
      comment: comment || "Manual reviewer decision.",
    });
    if (result) setResponse(result);
  };

  return (
    <div className="manual-override">
      <div className="sidebar-label" style={{ marginBottom: 8 }}>Manual override</div>
      <textarea
        className="manual-textarea"
        value={comment}
        onChange={e => setComment(e.target.value)}
        placeholder="Explain the root cause, remaining risk, or reason for approval."
        disabled={disabled}
      />
      <div className="manual-actions">
        <select value={decision} onChange={e => setDecision(e.target.value)} disabled={disabled}>
          <option value="request_changes">Request changes</option>
          <option value="approve">Approve</option>
          <option value="escalate">Escalate</option>
        </select>
        <select value={issueCategory} onChange={e => setIssueCategory(e.target.value)} disabled={disabled}>
          <option value="security">Security</option>
          <option value="logic">Logic</option>
          <option value="correctness">Correctness</option>
          <option value="performance">Performance</option>
          <option value="none">None</option>
        </select>
        <button className="init-btn active manual-submit" onClick={handleSubmit} disabled={disabled}>
          Submit
        </button>
      </div>

      {response && (
        <div className="manual-result">
          Reward {response.reward?.toFixed(2)} | {response.done ? "Episode complete" : "Next author turn ready"}
        </div>
      )}
    </div>
  );
}
