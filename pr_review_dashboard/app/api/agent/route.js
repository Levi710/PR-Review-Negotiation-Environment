import OpenAI from "openai";

export async function POST(request) {
  try {
    const { observation, modelId, apiUrl, apiKey } = await request.json();

    if (!apiKey || !modelId || !apiUrl) {
      return Response.json({ decision: "error", comment: "Missing API credentials." }, { status: 400 });
    }

    const client = new OpenAI({ baseURL: apiUrl, apiKey: apiKey });

    const systemPrompt = `You are a Senior Software Engineer conducting a thorough Pull Request review.
    Your goal is to evaluate the provided diff and issue a verdict: [approve], [request_changes], or [escalate].
    
    CRITICAL: 
    1. Focus on root causes (e.g., SQL injection, Race conditions, Logic errors), not just style.
    2. If you issue [request_changes], you MUST include a "Proposed Fix" code block (using \`\`\`python) that shows the full CORRECTED version of the logic you are criticizing.
    
    RESPONSE FORMAT (VALID JSON):
    {
      "decision": "approve" | "request_changes" | "escalate",
      "comment": "Detailed technical feedback here. Mention specific line numbers and root causes.",
      "issue_category": "security" | "logic" | "performance" | "style" | "none"
    }`;

    const historyLines = (observation.review_history || [])
      .map(h => `${h.role.toUpperCase()}: ${h.content}`)
      .join("\n") || "None yet.";

    const userPrompt =
      `PR Title: ${observation.pr_title || "N/A"}\n` +
      `PR Description: ${observation.pr_description || "N/A"}\n\n` +
      `Diff:\n${observation.diff || "No diff"}\n\n` +
      `Review History:\n${historyLines}\n\n` +
      `Author's latest response: ${observation.author_response || "N/A"}\n\n` +
      `Submit your review decision as JSON:`;

    const resp = await client.chat.completions.create({
      model: modelId,
      messages: [
        { role: "system", content: systemPrompt },
        { role: "user", content: userPrompt },
      ],
      max_tokens: 500,
      temperature: 0.1,
    });

    let raw = resp.choices[0].message.content.trim();
    if (raw.includes("```json")) raw = raw.split("```json")[1].split("```")[0];
    else if (raw.includes("```")) raw = raw.split("```")[1].split("```")[0];
    raw = raw.trim();

    const parsed = JSON.parse(raw);
    if (!parsed.decision || !parsed.comment) {
      return Response.json({ decision: "error", comment: "Model returned invalid format." }, { status: 200 });
    }

    // Default issue_category if missing to avoid 422 errors
    if (!parsed.issue_category) {
      parsed.issue_category = "none";
    }

    return Response.json(parsed);
  } catch (e) {
    return Response.json({ decision: "error", comment: `API Error: ${e.message}` }, { status: 200 });
  }
}
