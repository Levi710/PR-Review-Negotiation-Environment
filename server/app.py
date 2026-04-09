from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional
from models import PRAction, PRObservation, PRState
from server.environment import PRReviewEnvironment

app = FastAPI(title="PR Review Negotiation Environment")
env = PRReviewEnvironment()

class ResetRequest(BaseModel):
    task_name: Optional[str] = "single-pass-review"

class StepRequest(BaseModel):
    action: PRAction

class CustomTaskConfig(BaseModel):
    diff: str
    pr_title: Optional[str] = "Custom Review Session"
    pr_description: Optional[str] = "User-provided code snippet for review."

class StepResponse(BaseModel):
    observation: PRObservation
    reward: float
    done: bool
    info: dict

@app.get("/")
def index():
    return {
        "message": "Backend API is running!",
        "action": "Visit the dashboard at http://localhost:8501",
        "api_docs": "/docs"
    }

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/config/custom")
def set_custom_task(config: CustomTaskConfig):
    from server.tasks import custom
    custom.TASK["diff"] = config.diff
    custom.TASK["pr_title"] = config.pr_title
    custom.TASK["pr_description"] = config.pr_description
    return {"status": "success"}

@app.post("/reset", response_model=PRObservation)
def reset(req: ResetRequest = ResetRequest()):
    return env.reset(task_name=req.task_name)

@app.post("/step", response_model=StepResponse)
def step(req: StepRequest):
    if env._state is None or env._state.done:
        raise HTTPException(status_code=400, detail="Call /reset first or episode is done.")
    obs, reward, done, info = env.step(req.action)
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
