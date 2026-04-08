#!/bin/bash

# Start the Streamlit dashboard internally on port 8501
echo "Starting Streamlit Dashboard on port 8501..."
streamlit run app.py --server.port 8501 --server.address 0.0.0.0 --server.headless true &

# Start the FastAPI Gateway on the primary port 7860
# This gateway handles /reset, /step, and proxies everything else to Streamlit
echo "Starting FastAPI Gateway on port 7860..."
uvicorn gateway:app --host 0.0.0.0 --port 7860 &

# Wait for all processes to finish
wait
