#!/bin/bash

# Start the FastAPI backend on port 8000
echo "Starting FastAPI Backend on port 8000..."
uvicorn server.app:app --host 0.0.0.0 --port 8000 &

# Start the Streamlit dashboard internally on port 8501
echo "Starting Streamlit Dashboard on port 8501..."
streamlit run app.py --server.port 8501 --server.address 0.0.0.0 --server.headless true &

# Start Nginx in the foreground to keep the container alive
echo "Starting Nginx Proxy on port 7860..."
nginx -g "daemon off;"
