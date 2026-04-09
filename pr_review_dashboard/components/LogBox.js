"use client";
import { useState } from "react";

export default function LogBox({ logs }) {
  const [open, setOpen] = useState(false);

  return (
    <div className="log-box">
      <div className="log-toggle" onClick={() => setOpen(!open)}>
        <span>Behind the scenes — raw logs</span>
        <span>{open ? "▼" : "▶"}</span>
      </div>
      {open && (
        <div className="log-content">
          {logs.length === 0
            ? "No logs yet. Initialize an environment to begin."
            : logs.join("\n")}
        </div>
      )}
    </div>
  );
}
