const CANDIDATE_URLS = [
  "http://localhost:8000",
  "http://127.0.0.1:8000",
  "http://localhost:8001",
  "http://127.0.0.1:8001",
  "http://localhost:8002",
  "http://127.0.0.1:8002",
  "http://localhost:8010",
  "http://127.0.0.1:8010",
];

let cachedBackendUrl = null;
let cacheExpiresAt = 0;

function uniqueUrls(urls) {
  return [...new Set(urls.filter(Boolean))];
}

function normalizedUrl(url) {
  return url.replace(/\/+$/, "");
}

function expandConfiguredUrl(url) {
  if (!url) return [];

  const values = [normalizedUrl(url.trim())];

  try {
    const parsed = new URL(url);
    if (parsed.hostname === "localhost") {
      parsed.hostname = "127.0.0.1";
      values.push(normalizedUrl(parsed.toString()));
    } else if (parsed.hostname === "127.0.0.1") {
      parsed.hostname = "localhost";
      values.push(normalizedUrl(parsed.toString()));
    }
  } catch (_e) {
    return values;
  }

  return values;
}

async function isPrReviewBackend(baseUrl) {
  try {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 1200);

    const healthRes = await fetch(`${baseUrl}/health`, {
      cache: "no-store",
      signal: controller.signal,
    });
    clearTimeout(timeout);

    if (!healthRes.ok) return false;

    const health = await healthRes.json().catch(() => null);
    if (health?.status !== "healthy") return false;

    const metadataRes = await fetch(`${baseUrl}/metadata`, {
      cache: "no-store",
      signal: AbortSignal.timeout(1200),
    }).catch(() => null);

    if (!metadataRes?.ok) return false;

    const metadata = await metadataRes.json().catch(() => null);
    return metadata?.name === "pr-review-env";
  } catch (_e) {
    return false;
  }
}

export async function resolveBackendBaseUrl() {
  const now = Date.now();
  if (cachedBackendUrl && now < cacheExpiresAt) {
    return cachedBackendUrl;
  }

  const configured = process.env.ENV_BASE_URL || process.env.API_BASE_URL || "";
  const candidates = uniqueUrls([...expandConfiguredUrl(configured), ...CANDIDATE_URLS]);

  for (const baseUrl of candidates) {
    if (await isPrReviewBackend(baseUrl)) {
      cachedBackendUrl = baseUrl;
      cacheExpiresAt = now + 30_000;
      return baseUrl;
    }
  }

  const fallback = configured || "http://localhost:8000";
  cachedBackendUrl = fallback;
  cacheExpiresAt = now + 5_000;
  return fallback;
}
