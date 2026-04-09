"use client";

export default function DiffView({ diff }) {
  if (!diff || !diff.trim()) {
    return (
      <div className="diff-box">
        <div className="diff-header"><span>No diff loaded</span></div>
      </div>
    );
  }

  const rawLines = diff.split("\n");

  // Extract filename from +++ header
  let filename = "unknown_file";
  for (const line of rawLines) {
    if (line.startsWith("+++ b/")) {
      filename = line.slice(6);
      break;
    }
  }

  // Filter out file header lines (--- a/ and +++ b/) — they go in the header bar
  const bodyLines = rawLines.filter(
    (l) => !l.startsWith("--- a/") && !l.startsWith("+++ b/") && !l.startsWith("--- /") && !l.startsWith("+++ /")
  );

  // Count additions/deletions
  let adds = 0, dels = 0;
  bodyLines.forEach((l) => {
    if (l.startsWith("+") && !l.startsWith("+++")) adds++;
    if (l.startsWith("-") && !l.startsWith("---")) dels++;
  });

  // Parse lines with proper line numbering
  let newLineNum = 0;
  let oldLineNum = 0;
  const parsedLines = bodyLines.map((line) => {
    let type = "context";
    let displayNum = "";

    if (line.startsWith("@@")) {
      type = "meta";
      // Parse hunk header: @@ -old,count +new,count @@
      const match = line.match(/@@ -(\d+),?\d* \+(\d+)/);
      if (match) {
        oldLineNum = parseInt(match[1]) - 1;
        newLineNum = parseInt(match[2]) - 1;
      }
      displayNum = "···";
    } else if (line.startsWith("+")) {
      type = "add";
      newLineNum++;
      displayNum = newLineNum;
    } else if (line.startsWith("-")) {
      type = "del";
      oldLineNum++;
      displayNum = oldLineNum;
    } else {
      // Context line — both counters advance
      newLineNum++;
      oldLineNum++;
      displayNum = newLineNum;
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
