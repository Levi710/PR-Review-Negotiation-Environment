"use client";
import { useState, useCallback } from "react";

export default function DiffView({ diff, onCodeSubmit, isProcessing, isAccepted }) {
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
        style={{ minHeight: '450px', display: 'flex', flexDirection: 'column', background: '#0d1117' }}
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
            placeholder="Upload your code here...\n\n(Use + and - prefixes if you want to show specific additions/deletions)"
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

  // ── Strict Diff Rendering Logic ──
  const rawLines = diff.split("\n");
  
  let filename = "custom_file.py";
  const bodyLines = [];
  
  for (const line of rawLines) {
    if (line.startsWith("+++ b/")) {
      filename = line.slice(6);
    } else if (line.startsWith("--- a/") || line.startsWith("--- /") || line.startsWith("+++ /") || line.startsWith("index ")) {
      continue; // Skip metadata lines
    } else {
      bodyLines.push(line);
    }
  }

  let adds = 0, dels = 0;
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
        oldLineNum = parseInt(match[1]) - 1;
        newLineNum = parseInt(match[2]) - 1;
      }
      displayNum = "···";
    } else if (line.startsWith("+")) {
      type = "add";
      text = line.slice(1); // Remove prefix for cleaner look if accepted
      adds++;
      newLineNum++;
      displayNum = newLineNum;
    } else if (line.startsWith("-")) {
      type = "del";
      text = line.slice(1);
      dels++;
      oldLineNum++;
      displayNum = oldLineNum;
    } else {
      // Standard Context Line: No background color
      type = "context";
      text = line.startsWith(" ") ? line.slice(1) : line;
      newLineNum++;
      oldLineNum++;
      displayNum = newLineNum;
    }

    parsedLines.push({ text, type, displayNum });
  });

  return (
    <div className="diff-box">
      <div className="diff-header">
        <span style={{ color: isAccepted ? "#2ea043" : "inherit" }}>
          {isAccepted ? `✓ ${filename} (Concluded)` : filename}
        </span>
        <span style={{ fontSize: '10px' }}>
          {isAccepted ? "CHANGES PERSISTED" : `+${adds} −${dels} lines`}
        </span>
      </div>
      <div className="diff-body" style={{ minHeight: '400px' }}>
        {parsedLines.map((line, i) => (
          <div key={i} className={`diff-line ${line.type}`}>
            <span className="ln">{line.displayNum}</span>
            <span>{line.text}</span>
          </div>
        ))}
        {parsedLines.length === 0 && <div style={{ padding: '20px', color: '#8b949e', fontSize: '12px' }}>No code content found.</div>}
      </div>
    </div>
  );
}
