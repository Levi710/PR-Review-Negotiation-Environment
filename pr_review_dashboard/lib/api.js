const BASE = "/api/env";

async function readJson(res, label) {
  let data = null;
  try {
    data = await res.json();
  } catch (_e) {
    data = null;
  }
  if (!res.ok) {
    const detail = data?.detail || data?.error || res.statusText;
    throw new Error(`${label} failed: ${res.status} ${detail}`);
  }
  return data;
}

export async function listTasks() {
  const res = await fetch(`${BASE}/tasks`);
  return readJson(res, "Task list");
}

export async function getEnvState() {
  const res = await fetch(`${BASE}/state`);
  return readJson(res, "State");
}

export async function resetEnv(taskName) {
  const res = await fetch(`${BASE}/reset`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ task_name: taskName }),
  });
  return readJson(res, "Reset");
}

export async function stepEnv(action) {
  const res = await fetch(`${BASE}/step`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ action }),
  });
  return readJson(res, "Step");
}

export async function configCustom({ diff, pr_title, pr_description }) {
  const res = await fetch(`${BASE}/config/custom`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ diff, pr_title, pr_description }),
  });
  return readJson(res, "Config");
}

export async function callAgent({ observation, modelId, apiUrl, apiKey }) {
  const res = await fetch("/api/agent", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ observation, modelId, apiUrl, apiKey }),
  });
  return readJson(res, "Agent");
}
