import os
import httpx
from fastapi import FastAPI, Request, Response
from fastapi.responses import StreamingResponse
from server.app import app as env_app

# The Gateway App
app = FastAPI(title="PR Review Gateway")

# 1. Mount Environment API Routes (Primary for OpenEnv Validator)
# These will be available on the main port 7860
app.include_router(env_app.router)

# 2. Proxy for Streamlit Dashboard (Internal port 8501)
STREAMLIT_URL = "http://localhost:8501"
client = httpx.AsyncClient(base_url=STREAMLIT_URL)

@app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "HEAD", "PATCH"])
async def proxy_to_streamlit(request: Request, path: str):
    """
    Catch-all route to proxy everything else to the Streamlit dashboard on port 8501.
    """
    url = f"{STREAMLIT_URL}/{path}"
    
    # Forward the request headers and body
    headers = dict(request.headers)
    # Remove 'host' to avoid proxy confusion
    headers.pop("host", None)
    
    # Handle Streamlit's WebSocket and long-polling if needed
    # (Note: For full WebSocket support, a more complex proxy is usually needed, 
    # but for standard Streamlit on HF, this basic forwarder often works for the UI)
    
    # Get request body if it exists
    body = await request.body()
    
    # Send request to Streamlit
    try:
        response = await client.request(
            method=request.method,
            url=url,
            headers=headers,
            params=request.query_params,
            content=body,
            timeout=30.0
        )
        
        # Return the response back to the user
        return Response(
            content=response.content,
            status_code=response.status_code,
            headers=dict(response.headers)
        )
    except Exception as e:
        return Response(content=f"Gateway Error: {e}", status_code=502)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=7860)
