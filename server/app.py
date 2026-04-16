import json
from typing import Optional

from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel
from models import PRAction, PRObservation, PRState
from server.action_normalizer import normalize_action_payload
from server.environment import PRReviewEnvironment

app = FastAPI(
    title="PR Review Negotiation Environment",
    version="1.0.0",
    description="A multi-turn pull request review negotiation benchmark for engineering judgment.",
)
env = PRReviewEnvironment()

class ResetRequest(BaseModel):
    task_name: Optional[str] = "single-pass-review"

class CustomTaskConfig(BaseModel):
    diff: str
    pr_title: Optional[str] = "Custom Review Session"
    pr_description: Optional[str] = "User-provided code snippet for review."

class StepResponse(BaseModel):
    observation: PRObservation
    reward: float
    done: bool
    info: dict


def _task_metadata(task_name: str, task: dict) -> dict:
    return {
        "name": task_name,
        "pr_title": task.get("pr_title", task_name),
        "pr_description": task.get("pr_description", ""),
        "max_turns": task.get("max_turns", 1),
    }


def _model_schema(model: type[BaseModel]) -> dict:
    if hasattr(model, "model_json_schema"):
        return model.model_json_schema()
    return model.schema()


async def _read_payload(request: Request):
    body = await request.body()
    if not body:
        raise HTTPException(status_code=400, detail="Request body is required.")
    try:
        return json.loads(body)
    except json.JSONDecodeError:
        return body.decode("utf-8", errors="replace")

@app.get("/")
def index():
    return {
        "message": "Backend API is running!",
        "action": "Visit the dashboard at http://localhost:3000 locally or http://localhost:7860 in Docker.",
        "api_docs": "/docs"
    }

@app.get("/health")
def health():
    return {"status": "healthy"}

@app.get("/metadata")
def metadata():
    return {
        "name": "pr-review-env",
        "description": "A multi-turn pull request review negotiation benchmark for root-cause depth, false-fix resistance, and escalation judgment.",
        "version": "1.0.0",
        "author": "Levi710",
    }

@app.get("/schema")
def schema():
    return {
        "action": _model_schema(PRAction),
        "observation": _model_schema(PRObservation),
        "state": _model_schema(PRState),
    }

@app.post("/mcp")
async def mcp(request: Request):
    try:
        payload = await request.json()
    except Exception:
        payload = {}
    return {
        "jsonrpc": "2.0",
        "id": payload.get("id") if isinstance(payload, dict) else None,
        "error": {
            "code": -32601,
            "message": "MCP tools are not implemented for this environment.",
        },
    }

@app.get("/tasks")
def tasks():
    from server.environment import TASKS
    return {"tasks": [_task_metadata(name, task) for name, task in TASKS.items()]}

@app.post("/config/custom")
def set_custom_task(config: CustomTaskConfig):
    from server.tasks import custom
    custom.TASK["diff"] = config.diff
    custom.TASK["pr_title"] = config.pr_title
    custom.TASK["pr_description"] = config.pr_description
    return {"status": "success"}

@app.post("/reset", response_model=PRObservation)
def reset(req: ResetRequest = ResetRequest()):
    from server.environment import TASKS
    if req.task_name not in TASKS:
        raise HTTPException(status_code=404, detail=f"Unknown task: {req.task_name}")
    return env.reset(task_name=req.task_name)

@app.post("/step", response_model=StepResponse)
async def step(request: Request):
    if env._state is None or env._state.done:
        raise HTTPException(status_code=400, detail="Call /reset first or episode is done.")
    payload = await _read_payload(request)
    try:
        action = normalize_action_payload(payload)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Invalid action payload: {exc}") from exc
    obs, reward, done, info = env.step(action)
    return StepResponse(observation=obs, reward=reward, done=done, info=info)

@app.get("/state", response_model=PRState)
def state():
    if env._state is None:
        raise HTTPException(status_code=400, detail="No active episode. Call /reset first.")
    return env.state()

@app.post("/diff")
async def generate_diff(payload: dict):
    old_code = payload.get("old_code", "")
    new_code = payload.get("new_code", "")
    filename = payload.get("filename", "file.py")
    
    import difflib
    old_lines = old_code.splitlines(keepends=True)
    new_lines = new_code.splitlines(keepends=True)
    diff = difflib.unified_diff(
        old_lines, new_lines,
        fromfile=f"a/{filename}",
        tofile=f"b/{filename}"
    )
    return {"diff": "".join(diff)}

def main():
    import uvicorn
    import os
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)

if __name__ == "__main__":
    main()
