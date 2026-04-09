import OpenAI from "openai";

export async function POST(request) {
  try {
    const { observation, modelId, apiUrl, apiKey } = await request.json();

    if (!apiKey || !modelId || !apiUrl) {
      return Response.json({ decision: "error", comment: "Missing API credentials." }, { status: 400 });
    }

    const client = new OpenAI({ baseURL: apiUrl, apiKey: apiKey });

    const systemPrompt =
      'You are a senior software engineer performing a pull request code review.\n' +
      'Respond with ONLY this JSON (no markdown, no extra text):\n' +
      '{\n' +
      '  "decision": "approve|request_changes|escalate",\n' +
      '  "issue_category": "logic|security|performance|correctness|none",\n' +
      '  "comment": "your detailed review identifying root cause"\n' +
      '}';

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
