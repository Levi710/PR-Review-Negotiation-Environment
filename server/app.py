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

class StepResponse(BaseModel):
    observation: PRObservation
    reward: float
    done: bool
    info: dict

@app.get("/health")
def health():
    return {"status": "ok"}

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

def main():
    import uvicorn
    import os
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)

if __name__ == "__main__":
    main()
