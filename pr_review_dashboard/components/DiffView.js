"use client";

export default function DiffView({ diff }) {
  if (!diff || !diff.trim()) {
    return (
      <div className="diff-box">
        <div className="diff-header"><span>No diff loaded</span></div>
      </div>
    );
  }

  const lines = diff.split("\n");

  // Extract filename
  let filename = "unknown_file";
  for (const line of lines) {
    if (line.startsWith("+++ b/")) {
      filename = line.slice(6);
      break;
    }
  }

  // Count additions/deletions
  let adds = 0, dels = 0;
  lines.forEach(l => {
    if (l.startsWith("+") && !l.startsWith("+++")) adds++;
    if (l.startsWith("-") && !l.startsWith("---")) dels++;
  });

  // Build line numbers
  let lineNum = 0;
  const parsedLines = lines.map((line) => {
    let type = "context";
    if (line.startsWith("@@")) {
      type = "meta";
      const match = line.match(/@@ -\d+,?\d* \+(\d+)/);
      if (match) lineNum = parseInt(match[1]) - 1;
    } else if (line.startsWith("+") && !line.startsWith("+++")) {
      type = "add";
      lineNum++;
    } else if (line.startsWith("-") && !line.startsWith("---")) {
      type = "del";
    } else if (!line.startsWith("---") && !line.startsWith("+++")) {
      lineNum++;
    }
    return { text: line, type, num: type === "meta" ? "···" : type === "del" ? "" : lineNum || "" };
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
            <span className="ln">{line.num}</span>
            <span>{line.text}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
