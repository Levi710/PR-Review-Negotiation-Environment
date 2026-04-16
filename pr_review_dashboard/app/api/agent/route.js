import OpenAI from "openai";

const ALLOWED_CATEGORIES = new Set(["logic", "security", "correctness", "performance", "none"]);

function stripFences(text) {
  const fenced = text.match(/```(?:json)?\s*([\s\S]*?)\s*```/i);
  return fenced ? fenced[1].trim() : text.trim();
}

function extractJsonObject(text) {
  const candidate = stripFences(text);
  try {
    const parsed = JSON.parse(candidate);
    return parsed && typeof parsed === "object" && !Array.isArray(parsed) ? parsed : null;
  } catch (_e) {
    // Keep scanning below.
  }

  const start = candidate.indexOf("{");
  if (start === -1) return null;

  let depth = 0;
  let inString = false;
  let escape = false;
  for (let i = start; i < candidate.length; i += 1) {
    const ch = candidate[i];
    if (inString) {
      if (escape) escape = false;
      else if (ch === "\\") escape = true;
      else if (ch === "\"") inString = false;
      continue;
    }

    if (ch === "\"") inString = true;
    else if (ch === "{") depth += 1;
    else if (ch === "}") {
      depth -= 1;
      if (depth === 0) {
        try {
          const parsed = JSON.parse(candidate.slice(start, i + 1));
          return parsed && typeof parsed === "object" && !Array.isArray(parsed) ? parsed : null;
        } catch (_e) {
          return null;
        }
      }
    }
  }
  return null;
}

function normalizeDecision(value, comment) {
  const text = `${value || ""} ${comment || ""}`.toLowerCase().replaceAll("-", "_");
  if (text.includes("escalate") || text.includes("security_team")) return "escalate";
  if (text.includes("request_changes") || text.includes("changes_requested")) return "request_changes";
  if (text.includes("do not approve") || text.includes("cannot approve") || text.includes("not approve")) return "request_changes";
  if (text.includes("reject") || text.includes("needs changes") || text.includes("require changes")) return "request_changes";
  if (text.includes("approve") || text.includes("accept") || text.includes("lgtm") || text.includes("merge")) return "approve";
  return "request_changes";
}

function normalizeIssueCategory(value, comment) {
  const raw = String(value || "").toLowerCase().replaceAll("-", "_");
  if (ALLOWED_CATEGORIES.has(raw)) return raw;

  const text = `${raw} ${comment || ""}`.toLowerCase();
  if (text.includes("security") || text.includes("injection") || text.includes("secret") || text.includes("auth")) return "security";
  if (
    text.includes("logic") ||
    text.includes("off_by_one") ||
    text.includes("off-by-one") ||
    text.includes("pagination") ||
    text.includes("offset") ||
    text.includes("page 1") ||
    text.includes("skips first")
  ) return "logic";
  if (text.includes("correct") || text.includes("bug") || text.includes("valid")) return "correctness";
  if (text.includes("performance") || text.includes("latency") || text.includes("slow")) return "performance";
  return "none";
}

function normalizeAction(raw) {
  const parsed = extractJsonObject(raw) || { comment: raw };
  const commentValue = parsed.comment || parsed.review || parsed.feedback || raw || "No detailed comment provided.";
  const comment = typeof commentValue === "string" ? commentValue : JSON.stringify(commentValue);
  const normalized = {
    decision: normalizeDecision(parsed.decision || parsed.verdict, comment),
    issue_category: normalizeIssueCategory(parsed.issue_category || parsed.category || parsed.issue_type, comment),
    comment,
  };

  if (parsed.proposed_fix) normalized.proposed_fix = parsed.proposed_fix;
  return normalized;
}

export async function POST(request) {
  try {
    const { observation, modelId, apiUrl, apiKey } = await request.json();

    if (!apiKey || !modelId || !apiUrl) {
      return Response.json({ decision: "error", comment: "Missing API credentials." }, { status: 400 });
    }

    const client = new OpenAI({ baseURL: apiUrl, apiKey });

    const systemPrompt = `You are a senior software security engineer performing a pull request code review.

Identify root causes, not symptoms. Track whether author replies actually fix the vulnerability or logic flaw.
For critical security issues such as hardcoded secrets, auth bypasses, exposed credentials, or RCE vectors, choose "escalate".

Return only JSON with this shape:
{
  "decision": "approve" | "request_changes" | "escalate",
  "issue_category": "security" | "logic" | "correctness" | "performance" | "none",
  "comment": "Detailed technical feedback explaining the root cause."
}`;

    const historyLines = (observation.review_history || [])
      .map(h => `${String(h.role || "").toUpperCase()}: ${h.content}`)
      .join("\n") || "None yet.";

    const userPrompt =
      `PR Title: ${observation.pr_title || "N/A"}\n` +
      `PR Description: ${observation.pr_description || "N/A"}\n\n` +
      `Diff:\n${observation.diff || "No diff"}\n\n` +
      `Review History:\n${historyLines}\n\n` +
      `Author's latest response: ${observation.author_response || "N/A"}\n\n` +
      `Instructions: ${observation.message || ""}\n\n` +
      `Submit your review decision as JSON.`;

    const resp = await client.chat.completions.create({
      model: modelId,
      messages: [
        { role: "system", content: systemPrompt },
        { role: "user", content: userPrompt },
      ],
      max_tokens: 1500,
      temperature: 0.1,
    });

    const raw = resp.choices[0].message.content?.trim() || "";
    return Response.json(normalizeAction(raw));
  } catch (e) {
    return Response.json({ decision: "error", comment: `API Error: ${e.message}` }, { status: 200 });
  }
}
