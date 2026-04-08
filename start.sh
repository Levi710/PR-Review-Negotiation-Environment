#!/bin/bash

# Start the FastAPI backend on port 8000
echo "Starting FastAPI Backend on port 8000..."
uvicorn server.app:app --host 0.0.0.0 --port 8000 &

# Start the Streamlit dashboard on port 7860 (default HF Spaces port)
echo "Starting Streamlit Dashboard on port 7860..."
streamlit run app.py --server.port 7860 --server.address 0.0.0.0 &

# Wait for all processes to finish
wait
