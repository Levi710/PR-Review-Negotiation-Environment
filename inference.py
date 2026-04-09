import os
import json
import httpx
from openai import OpenAI
from typing import List, Optional

# --- Configuration ---
API_BASE_URL = os.getenv("API_BASE_URL", "https://router.huggingface.co/v1")
MODEL_NAME   = os.getenv("MODEL_NAME",   "Qwen/Qwen2.5-72B-Instruct")
HF_TOKEN     = os.getenv("HF_TOKEN")
ENV_BASE_URL = os.getenv("ENV_BASE_URL", "http://localhost:7860")

if HF_TOKEN is None:
    raise ValueError("HF_TOKEN environment variable is required")

client = OpenAI(base_url=API_BASE_URL, api_key=HF_TOKEN)

TASKS     = ["single-pass-review", "iterative-negotiation", "escalation-judgment"]
MAX_STEPS = 8
BENCHMARK = "pr-review-env"

SYSTEM_PROMPT = """You are a senior software security engineer performing a pull request code review.

Your job is not to find surface-level issues — it is to understand what the code is SUPPOSED to do
versus what it ACTUALLY does, and identify the ROOT CAUSE of any problem, not just its symptom.

For security issues: explain exactly what the attack vector is and why the proposed fix (if any) does
or does not address it. Do not be fooled by cosmetic fixes that leave the actual vulnerability intact.

For logic issues: explain what invariant or assumption is violated, not just that the output is wrong.

You must respond with EXACTLY this JSON format and nothing else:
{
  "decision": "<approve|request_changes|escalate>",
  "issue_category": "<logic|security|correctness|performance|none>",
  "comment": "<your detailed review comment identifying root cause>"
}

Decision guidelines:
- "request_changes": bug or security issue found, fixable in normal review cycle
- "approve": code is correct and all previously raised issues are genuinely resolved
- "escalate": critical security issue (hardcoded secrets, auth bypass, RCE vector) that requires
  immediate security team involvement — do NOT use request_changes for these

Do not wrap your JSON in markdown. Output only the JSON object."""

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
    ) or "None — this is your first review of this PR."
    return f"""PR Title: {obs['pr_title']}
PR Description: {obs['pr_description']}

Diff:
{obs['diff']}

Review History:
{history}

Author's latest response: {obs.get('author_response') or 'N/A'}

Instructions: {obs.get('message', '')}

Identify the root cause. Submit your JSON review."""

def get_agent_action(obs: dict) -> dict:
    try:
        resp = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user",   "content": build_prompt(obs)},
            ],
            max_tokens=400,
            temperature=0.1,
        )
        raw = resp.choices[0].message.content.strip()
        raw = raw.replace("```json", "").replace("```", "").strip()
        return json.loads(raw)
    except Exception as e:
        return {"decision": "request_changes", "issue_category": "logic", "comment": f"[fallback: {e}]"}

def run_task(task_name: str) -> tuple[bool, float, List[float]]:
    rewards: List[float] = []
    steps_taken = 0
    score = 0.0
    success = False

    log_start(task=task_name, env=BENCHMARK, model=MODEL_NAME)

    try:
        r = httpx.post(f"{ENV_BASE_URL}/reset", json={"task_name": task_name}, timeout=30)
        obs = r.json()

        for stepNum in range(1, MAX_STEPS + 1):
            if obs.get("done"):
                break

            action_dict = get_agent_action(obs)
            action_str = (
                f"decision={action_dict.get('decision')} "
                f"category={action_dict.get('issue_category')} "
                f"comment={repr(action_dict.get('comment','')[:60])}"
            )

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
            steps_taken = stepNum
            log_step(step=stepNum, action=action_str, reward=reward, done=done, error=error)

            if done:
                break

        try:
            state_r = httpx.get(f"{ENV_BASE_URL}/state", timeout=10)
            success = state_r.json().get("success", False)
        except Exception:
            pass

        score = sum(rewards) / max(len(rewards) * 0.9, 1)
        score = min(max(score, 0.0), 1.0)

    except Exception as e:
        log_end(success=False, steps=steps_taken, score=0.0, rewards=rewards)
        return False, 0.0, rewards

    log_end(success=success, steps=steps_taken, score=score, rewards=rewards)
    return success, score, rewards


if __name__ == "__main__":
    for t_name in TASKS:
        run_task(t_name)
