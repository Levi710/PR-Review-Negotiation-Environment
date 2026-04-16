# PR Review Dashboard

Next.js dashboard for the PR Review Negotiation Environment.

## Local Development

Start the FastAPI backend from the repository root:

```bash
python -m uvicorn server.app:app --host 0.0.0.0 --port 8000
```

Then start the dashboard:

```bash
npm run dev -- -p 3000
```

Open [http://localhost:3000](http://localhost:3000).

The dashboard proxies `/api/env/*` to the backend. Override the backend URL with `ENV_BASE_URL` when needed.
