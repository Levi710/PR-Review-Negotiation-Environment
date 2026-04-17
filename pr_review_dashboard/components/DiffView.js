"use client";
import { useState, useCallback } from "react";

function highlightCode(text) {
  if (!text) return text;

  const rules = [
    { cls: "tk-cm", re: /(#.*$|\/\/.*$|\/\*[\s\S]*?\*\/)/gm },
    { cls: "tk-st", re: /(['"`])(?:(?!\1)[^\\]|\\.)*\1/g },
    { cls: "tk-kw", re: /\b(def|class|if|else|elif|return|for|while|import|from|with|as|try|except|finally|raise|pass|break|continue|in|is|not|and|or|let|const|var|function|async|await|throw|new|instanceof|catch)\b/g },
    { cls: "tk-nm", re: /\b(\d+(\.\d+)?)\b/g },
    { cls: "tk-fn", re: /\b([a-zA-Z_]\w*)(?=\s*\()/g },
    { cls: "tk-cl", re: /\b([A-Z][a-zA-Z0-9_]+)\b/g },
    { cls: "tk-op", re: /([-+*/%=<>!&|^~]+)/g },
  ];

  const tokens = [];
  let processed = text;

  rules.forEach((rule, ruleIdx) => {
    processed = processed.replace(rule.re, (match) => {
      const id = `__TOKEN_${ruleIdx}_${tokens.length}__`;
      tokens.push({ id, html: `<span class="${rule.cls}">${match}</span>` });
      return id;
    });
  });

  let finalHtml = processed
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");

  for (let i = tokens.length - 1; i >= 0; i -= 1) {
    const token = tokens[i];
    finalHtml = finalHtml.replace(token.id, token.html);
  }

  return finalHtml;
}

function InputPane({
  inputText,
  setInputText,
  isDragOver,
  setIsDragOver,
  onCodeSubmit,
  isProcessing,
  reviewReady,
  blockedReason,
}) {
  const handleDrop = useCallback((e) => {
    e.preventDefault();
    setIsDragOver(false);
    const file = e.dataTransfer.files[0];
    if (file) {
      const reader = new FileReader();
      reader.onload = (rev) => setInputText(rev.target.result);
      reader.readAsText(file);
    }
  }, [setInputText, setIsDragOver]);

  return (
    <div
      className={`diff-box ${isDragOver ? "drag-over" : ""}`}
      onDragOver={(e) => { e.preventDefault(); setIsDragOver(true); }}
      onDragLeave={() => setIsDragOver(false)}
      onDrop={handleDrop}
      style={{ minHeight: "450px", display: "flex", flexDirection: "column", background: "#0d1117" }}
    >
      <div className="diff-header" style={{ borderBottom: "1px solid #30363d" }}>
        <span>Ready for Input</span>
        <span style={{ fontSize: "10px" }}>DRAG FILE OR PASTE BELOW</span>
      </div>
      <div style={{ flex: 1, padding: "20px", display: "flex", flexDirection: "column", gap: "15px" }}>
        <textarea
          className="manual-textarea code-input"
          style={{
            flex: 1,
            background: "#161b22",
            color: "#e6edf3",
            border: "1px solid #30363d",
            fontFamily: "var(--font-mono)",
            fontSize: "12px",
            padding: "15px",
            resize: "none",
          }}
          placeholder={"Paste code or a unified diff here...\n\nExamples:\n- a full Python/JS file\n- a PR diff with ---/+++ headers\n- a function snippet you want reviewed"}
          value={inputText}
          onChange={(e) => setInputText(e.target.value)}
        />
        <div className={`step-hint ${reviewReady ? "ready" : "locked"}`}>
          <div className="step-hint-title">Step 4: Run Custom Review</div>
          <div className="step-hint-text">
            {reviewReady
              ? "This submits your code to the custom environment, resets the task, and asks the reviewer for a decision."
              : blockedReason || "Complete the earlier steps to unlock review."}
          </div>
        </div>
        <button
          className="init-btn active"
          style={{ alignSelf: "flex-end", width: "auto", padding: "10px 25px" }}
          disabled={!inputText.trim() || isProcessing || !reviewReady}
          onClick={() => onCodeSubmit(inputText)}
        >
          {isProcessing ? "Reviewing..." : "Step 4: Start Review"}
        </button>
      </div>
    </div>
  );
}

function EmptyPane({ emptyStateTitle, emptyStateMessage, onOpenComposer }) {
  return (
    <div className="empty-pane">
      <div className="empty-pane-inner">
        <div className="empty-pane-title">{emptyStateTitle}</div>
        <div className="empty-pane-text">{emptyStateMessage}</div>
        {onOpenComposer && (
          <button className="init-btn active empty-pane-btn" onClick={onOpenComposer}>
            Paste Custom Code
          </button>
        )}
      </div>
    </div>
  );
}

export default function DiffView({
  diff,
  onCodeSubmit,
  isProcessing,
  isAccepted,
  isAiProposal,
  onApplyFix,
  inputMode = false,
  emptyStateTitle = "No review loaded",
  emptyStateMessage = "Start a review session to inspect a diff.",
  onOpenComposer,
  reviewReady = true,
  blockedReason = "",
  inputText: controlledInputText,
  onInputTextChange,
}) {
  const [internalInputText, setInternalInputText] = useState("");
  const [isDragOver, setIsDragOver] = useState(false);
  const inputText = controlledInputText ?? internalInputText;
  const setInputText = onInputTextChange ?? setInternalInputText;

  if (!diff || !diff.trim()) {
    if (inputMode) {
      return (
        <InputPane
          inputText={inputText}
          setInputText={setInputText}
          isDragOver={isDragOver}
          setIsDragOver={setIsDragOver}
          onCodeSubmit={onCodeSubmit}
          isProcessing={isProcessing}
          reviewReady={reviewReady}
          blockedReason={blockedReason}
        />
      );
    }

    return (
      <EmptyPane
        emptyStateTitle={emptyStateTitle}
        emptyStateMessage={emptyStateMessage}
        onOpenComposer={onOpenComposer}
      />
    );
  }

  const rawLines = diff.split("\n");
  let filename = "custom_file.py";
  const bodyLines = [];

  for (const line of rawLines) {
    if (line.startsWith("+++ b/")) {
      filename = line.slice(6);
    } else if (line.startsWith("--- a/") || line.startsWith("--- /") || line.startsWith("+++ /") || line.startsWith("index ")) {
      continue;
    } else {
      bodyLines.push(line);
    }
  }

  let adds = 0;
  let dels = 0;
  const parsedLines = [];
  let newLineNum = 0;
  let oldLineNum = 0;

  bodyLines.forEach((line) => {
    let type = "context";
    let text = line;
    let displayNum = "";

    if (line.startsWith("@@")) {
      type = "meta";
      const match = line.match(/@@ -(\d+),?\d* \+(\d+)/);
      if (match) {
        oldLineNum = parseInt(match[1], 10) - 1;
        newLineNum = parseInt(match[2], 10) - 1;
      }
      displayNum = "...";
    } else if (line.startsWith("+")) {
      type = "add";
      text = line.slice(1);
      adds += 1;
      newLineNum += 1;
      displayNum = newLineNum;
    } else if (line.startsWith("-")) {
      type = "del";
      text = line.slice(1);
      dels += 1;
      oldLineNum += 1;
      displayNum = oldLineNum;
    } else {
      type = "context";
      text = line.startsWith(" ") ? line.slice(1) : line;
      newLineNum += 1;
      oldLineNum += 1;
      displayNum = newLineNum;
    }

    parsedLines.push({ text, type, displayNum });
  });

  return (
    <div className="diff-box">
      <div className="diff-header" style={{ borderLeft: isAiProposal ? "4px solid #ff7b72" : "2px solid transparent" }}>
        <span style={{ color: isAccepted ? "#3fb950" : isAiProposal ? "#ff7b72" : "inherit" }}>
          {isAccepted ? `Done: ${filename}` : isAiProposal ? `AI Proposal: ${filename}` : filename}
        </span>
        <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
          <span style={{ fontSize: "10px", color: "#8b949e" }}>
            {isAccepted ? "HISTORY PRESERVED" : `+${adds} / -${dels} lines`}
          </span>
          {isAiProposal && onApplyFix && (
            <button
              className="hunk-btn accept"
              onClick={onApplyFix}
              style={{ fontSize: "9px", padding: "2px 8px" }}
            >
              Apply AI Suggestion
            </button>
          )}
        </div>
      </div>
      <div className="diff-body" style={{ minHeight: "400px" }}>
        {parsedLines.map((line, i) => (
          <div key={i} className={`diff-line ${line.type}`}>
            <span className="ln">{line.displayNum}</span>
            <span
              className="code-content"
              dangerouslySetInnerHTML={{ __html: line.type === "meta" ? line.text : highlightCode(line.text) }}
            />
          </div>
        ))}
      </div>
    </div>
  );
}
