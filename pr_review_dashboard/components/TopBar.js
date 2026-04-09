"use client";

export default function TopBar({ title, subtitle, decision }) {
  const badgeMap = {
    APPROVE: "approve",
    REQUEST_CHANGES: "request",
    ESCALATE: "escalate",
    RUNNING: "running",
    IDLE: "idle",
  };
  const cls = badgeMap[decision] || "running";

  return (
    <div className="topbar">
      <div>
        <div className="pr-title">{title || "No PR loaded"}</div>
        <div className="pr-sub">{subtitle || "Initialize a scenario to begin"}</div>
      </div>
      <span className={`badge ${cls}`}>{decision}</span>
    </div>
  );
}
