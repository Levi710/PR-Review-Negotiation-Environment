# Start Local PR Review Environment
# This script starts the FastAPI backend and Streamlit dashboard simultaneously on Windows.

Write-Host "Starting FastAPI Backend on port 8000..." -ForegroundColor Cyan
Start-Process powershell -ArgumentList "-NoExit", "-Command", "uvicorn server.app:app --host 0.0.0.0 --port 8000"

Write-Host "Starting Streamlit Dashboard on port 8501..." -ForegroundColor Green
streamlit run app.py --server.port 8501 --server.address 0.0.0.0
