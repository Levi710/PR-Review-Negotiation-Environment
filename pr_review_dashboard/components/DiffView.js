"use client";
import { useState, useCallback } from "react";

export default function DiffView({ diff, onCodeSubmit, isProcessing }) {
  const [inputText, setInputText] = useState("");
  const [isDragOver, setIsDragOver] = useState(false);

  const handleDrop = useCallback((e) => {
    e.preventDefault();
    setIsDragOver(false);
    const file = e.dataTransfer.files[0];
    if (file) {
      const reader = new FileReader();
      reader.onload = (rev) => setInputText(rev.target.result);
      reader.readAsText(file);
    }
  }, []);

  if (!diff || !diff.trim()) {
    return (
      <div 
        className={`diff-box ${isDragOver ? 'drag-over' : ''}`}
        onDragOver={(e) => { e.preventDefault(); setIsDragOver(true); }}
        onDragLeave={() => setIsDragOver(false)}
        onDrop={handleDrop}
        style={{ minHeight: '300px', display: 'flex', flexDirection: 'column', background: '#0d1117' }}
      >
        <div className="diff-header" style={{ borderBottom: '1px solid #30363d' }}>
          <span>Ready for Input</span>
          <span style={{ fontSize: '10px' }}>DRAG FILE OR PASTE BELOW</span>
        </div>
        <div style={{ flex: 1, padding: '20px', display: 'flex', flexDirection: 'column', gap: '15px' }}>
          <textarea
            className="manual-textarea"
            style={{ 
              flex: 1, 
              background: '#161b22', 
              color: '#e6edf3', 
              border: '1px solid #30363d',
              fontFamily: 'var(--font-mono)',
              fontSize: '12px',
              padding: '15px',
              resize: 'none'
            }}
            placeholder="--- a/example.py\n+++ b/example.py\n@@ -1,1 +1,1 @@\n-old code\n+new code\n\n(Or just paste the new code snippet here)"
            value={inputText}
            onChange={(e) => setInputText(e.target.value)}
          />
          <button 
            className="init-btn active" 
            style={{ alignSelf: 'flex-end', width: 'auto', padding: '10px 25px' }}
            disabled={!inputText.trim() || isProcessing}
            onClick={() => onCodeSubmit(inputText)}
          >
            {isProcessing ? "Loading Code..." : "Start Review →"}
          </button>
        </div>
      </div>
    );
  }

  // ── Existing Diff Rendering Logic ──
  const rawLines = diff.trim().split("\n");
  let filename = "unknown_file";
  for (const line of rawLines) {
    if (line.startsWith("+++ b/")) {
      filename = line.slice(6);
      break;
    }
  }

  const bodyLines = rawLines.filter(
    (l) => !l.startsWith("--- a/") && !l.startsWith("+++ b/") && !l.startsWith("--- /") && !l.startsWith("+++ /")
  );

  let adds = 0, dels = 0;
  bodyLines.forEach((l) => {
    if (l.startsWith("+") && !l.startsWith("+++")) adds++;
    if (l.startsWith("-") && !l.startsWith("---")) dels++;
  });

  let newLineNum = null;
  let oldLineNum = null;
  const parsedLines = bodyLines.map((line) => {
    let type = "context";
    let displayNum = "";
    if (line.startsWith("@@")) {
      type = "meta";
      const match = line.match(/@@ -(\d+),?\d* \+(\d+)/);
      if (match) {
        oldLineNum = parseInt(match[1]) - 1;
        newLineNum = parseInt(match[2]) - 1;
      }
      displayNum = "···";
    } else if (line.startsWith("+")) {
      type = "add";
      if (newLineNum !== null) { newLineNum++; displayNum = newLineNum; }
    } else if (line.startsWith("-")) {
      type = "del";
      if (oldLineNum !== null) { oldLineNum++; displayNum = oldLineNum; }
    } else {
      if (newLineNum !== null) { newLineNum++; oldLineNum++; displayNum = newLineNum; }
    }
    return { text: line, type, displayNum };
  });

  return (
    <div className="diff-box">
      <div className="diff-header">
        <span>{filename}</span>
        <span>+{adds} −{dels} lines</span>
      </div>
      <div className="diff-body">
        {parsedLines.map((line, i) => (
          <div key={i} className={`diff-line ${line.type}`}>
            <span className="ln">{line.displayNum}</span>
            <span>{line.text}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
