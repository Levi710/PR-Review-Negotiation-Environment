#!/bin/bash

echo "===== Application Startup at $(date) ====="

# Start the FastAPI backend on port 8000
echo "Starting FastAPI Backend on port 8000..."
uvicorn server.app:app --host 0.0.0.0 --port 8000 &

# Start the Next.js frontend on port 3000
echo "Starting Next.js Dashboard on port 3000..."
cd pr_review_dashboard && npm start -- -p 3000 &
cd /app

# Give services a moment to start
sleep 3

# Start Nginx in the foreground to keep the container alive
echo "Starting Nginx Proxy on port 7860..."
nginx -g "daemon off;"
