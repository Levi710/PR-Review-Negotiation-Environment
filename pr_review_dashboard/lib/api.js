const BASE = "/api/env";

export async function resetEnv(taskName) {
  const res = await fetch(`${BASE}/reset`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ task_name: taskName }),
  });
  if (!res.ok) throw new Error(`Reset failed: ${res.status}`);
  return res.json();
}

export async function stepEnv(action) {
  const res = await fetch(`${BASE}/step`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ action }),
  });
  if (!res.ok) throw new Error(`Step failed: ${res.status}`);
  return res.json();
}

export async function configCustom({ diff, pr_title, pr_description }) {
  const res = await fetch(`${BASE}/config/custom`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ diff, pr_title, pr_description }),
  });
  if (!res.ok) throw new Error(`Config failed: ${res.status}`);
  return res.json();
}

export async function callAgent({ observation, modelId, apiUrl, apiKey }) {
  const res = await fetch("/api/agent", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ observation, modelId, apiUrl, apiKey }),
  });
  if (!res.ok) throw new Error(`Agent failed: ${res.status}`);
  return res.json();
}
