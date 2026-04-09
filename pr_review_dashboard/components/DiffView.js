"use client";
import { useState, useCallback } from "react";

/**
 * Lightweight Syntax Highlighter for Python/JS
 */
function highlightCode(text) {
  if (!text) return text;
  
  const rules = [
    { cls: 'tk-cm', re: /(#.*$|\/\/.*$|\/\*[\s\S]*?\*\/)/gm }, // Comments
    { cls: 'tk-st', re: /(['"`])(?:(?!\1)[^\\]|\\.)*\1/g },     // Strings
    { cls: 'tk-kw', re: /\b(def|class|if|else|elif|return|for|while|import|from|with|as|try|except|finally|raise|pass|break|continue|in|is|not|and|or|let|const|var|function|async|await|throw|new|instanceof|catch)\b/g },
    { cls: 'tk-nm', re: /\b(\d+(\.\d+)?)\b/g },                // Numbers
    { cls: 'tk-fn', re: /\b([a-zA-Z_]\w*)(?=\s*\()/g },        // Functions
    { cls: 'tk-cl', re: /\b([A-Z][a-zA-Z0-0_]+)\b/g },        // Classes
    { cls: 'tk-op', re: /([-+*/%=<>!&|^~]+)/g },               // Operators
  ];

  // 1. First, we identify all tokens and replace them with unique placeholders
  // This prevents HTML escaping from breaking the regex matching later.
  const tokens = [];
  let processed = text;

  rules.forEach((rule, ruleIdx) => {
    processed = processed.replace(rule.re, (match) => {
      const id = `__TOKEN_${ruleIdx}_${tokens.length}__`;
      tokens.push({ id, html: `<span class="${rule.cls}">${match}</span>` });
      return id;
    });
  });

  // 2. Now escape the remaining text (non-tokens) for HTML safety
  let finalHtml = processed
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");

  // 3. Put the highlighted tokens back into the escaped string
  // We go backwards to handle any nested-like replacements (though regexes here are flat)
  for (let i = tokens.length - 1; i >= 0; i--) {
    const t = tokens[i];
    // We need to make sure the token HTML itself is not escaped in step 2.
    // Since we used IDs like __TOKEN... they are safe.
    finalHtml = finalHtml.replace(t.id, t.html);
  }

  return finalHtml;
}

export default function DiffView({ diff, onCodeSubmit, isProcessing, isAccepted, isAiProposal, onApplyFix }) {
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
      text = line.slice(1);
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
      <div className="diff-header" style={{ borderLeft: isAiProposal ? '4px solid #ff7b72' : '2px solid transparent' }}>
        <span style={{ color: isAccepted ? "#3fb950" : isAiProposal ? "#ff7b72" : "inherit" }}>
          {isAccepted ? `✓ ${filename} (Concluded)` : isAiProposal ? `⚠️ AI PROPOSAL: ${filename}` : filename}
        </span>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <span style={{ fontSize: '10px', color: '#8b949e' }}>
            {isAccepted ? "HISTORY PRESERVED" : `+${adds} −${dels} lines`}
          </span>
          {isAiProposal && onApplyFix && (
            <button 
              className="hunk-btn accept" 
              onClick={onApplyFix}
              style={{ fontSize: '9px', padding: '2px 8px' }}
            >
              Apply AI Suggestion →
            </button>
          )}
        </div>
      </div>
      <div className="diff-body" style={{ minHeight: '400px' }}>
        {parsedLines.map((line, i) => (
          <div key={i} className={`diff-line ${line.type}`}>
            <span className="ln">{line.displayNum}</span>
            <span 
              className="code-content"
              dangerouslySetInnerHTML={{ __html: line.type === 'meta' ? line.text : highlightCode(line.text) }} 
            />
            
            {(line.type === 'add' || line.type === 'del') && !isAccepted && (
              <div className="hunk-actions">
                <button className="hunk-btn accept">Accept</button>
                <button className="hunk-btn reject">Reject</button>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
