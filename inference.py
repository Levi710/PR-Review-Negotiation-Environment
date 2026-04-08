import os
import httpx
from openai import OpenAI
from typing import List, Optional

# ── Environment variables ──────────────────────────────────────────────────────
API_BASE_URL = os.getenv("API_BASE_URL", "https://router.huggingface.co/v1")
MODEL_NAME   = os.getenv("MODEL_NAME",   "Qwen/Qwen2.5-72B-Instruct")
HF_TOKEN     = os.getenv("HF_TOKEN")
ENV_BASE_URL = os.getenv("ENV_BASE_URL", "http://localhost:7860")

if HF_TOKEN is None:
    raise ValueError("HF_TOKEN environment variable is required")

client = OpenAI(base_url=API_BASE_URL, api_key=HF_TOKEN)

TASKS      = ["single-pass-review", "iterative-negotiation", "escalation-judgment"]
MAX_STEPS  = 8
BENCHMARK  = "pr-review-env"

SYSTEM_PROMPT = """You are a senior software engineer performing a pull request code review.

You will receive a code diff and review history. You must respond with EXACTLY this JSON format and nothing else:
{
  "decision": "<approve|request_changes|escalate>",
  "comment": "<your detailed review comment>"
}

Guidelines:
- Use "request_changes" if you find bugs, security issues, or logic errors that must be fixed.
- Use "approve" only when the code is correct and all previous issues are resolved.
- Use "escalate" only for critical security vulnerabilities (hardcoded secrets, auth bypass, injection) that need immediate senior review beyond normal PR flow.
- Your comment must mention the specific issue found and what fix is needed.
- Be concise but precise. Do not wrap your JSON in markdown."""

def log_start(task, env, model):
    print(f"[START] task={task} env={env} model={model}", flush=True)

def log_step(step, action, reward, done, error):
    err = error if error else "null"
    print(f"[STEP] step={step} action={action} reward={reward:.2f} done={str(done).lower()} error={err}", flush=True)

def log_end(success, steps, score, rewards: List[float]):
    r = ",".join(f"{x:.2f}" for x in rewards)
    print(f"[END] success={str(success).lower()} steps={steps} score={score:.3f} rewards={r}", flush=True)

def build_prompt(obs: dict) -> str:
    history = "\n".join(
        f"[{h['role'].upper()}]: {h['content']}"
        for h in obs.get("review_history", [])
    )
    return f"""PR Title: {obs['pr_title']}
PR Description: {obs['pr_description']}

Diff:
{obs['diff']}

Review History:
{history if history else "None yet — this is your first review."}

Author's latest response: {obs.get('author_response') or 'N/A'}

Now submit your review decision as JSON."""

def get_agent_action(obs: dict) -> dict:
    import json
    prompt = build_prompt(obs)
    try:
        resp = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user",   "content": prompt},
            ],
            max_tokens=300,
            temperature=0.2,
        )
        raw = resp.choices[0].message.content.strip()
        # Strip markdown fences if present
        raw = raw.replace("```json", "").replace("```", "").strip()
        parsed = json.loads(raw)
        return parsed
    except Exception as e:
        return {"decision": "request_changes", "comment": f"[fallback due to error: {e}]"}

def run_task(task_name: str) -> tuple[bool, float, List[float]]:
    rewards: List[float] = []
    steps_taken = 0
    score = 0.0
    success = False

    log_start(task=task_name, env=BENCHMARK, model=MODEL_NAME)

    try:
        # Reset
        r = httpx.post(f"{ENV_BASE_URL}/reset", json={"task_name": task_name}, timeout=30)
        obs = r.json()

        for step in range(1, MAX_STEPS + 1):
            if obs.get("done"):
                break

            action_dict = get_agent_action(obs)
            action_str = f"decision={action_dict.get('decision')} comment={repr(action_dict.get('comment','')[:60])}"

            try:
                step_r = httpx.post(
                    f"{ENV_BASE_URL}/step",
                    json={"action": action_dict},
                    timeout=30,
                )
                step_data = step_r.json()
                reward = step_data.get("reward", 0.0)
                done   = step_data.get("done", False)
                obs    = step_data.get("observation", obs)
                error  = None
            except Exception as e:
                reward = 0.0
                done   = True
                error  = str(e)

            rewards.append(reward)
            steps_taken = step
            log_step(step=step, action=action_str, reward=reward, done=done, error=error)

            if done:
                break

        # Fetch final score from state
        try:
            state_r = httpx.get(f"{ENV_BASE_URL}/state", timeout=10)
            state_data = state_r.json()
            success = state_data.get("success", False)
        except Exception:
            pass

        score = sum(rewards) / max(len(rewards) * 0.8, 1)
        score = min(max(score, 0.0), 1.0)

    except Exception as e:
        log_end(success=False, steps=steps_taken, score=0.0, rewards=rewards)
        return False, 0.0, rewards

    log_end(success=success, steps=steps_taken, score=score, rewards=rewards)
    return success, score, rewards


if __name__ == "__main__":
    for task in TASKS:
        run_task(task)
