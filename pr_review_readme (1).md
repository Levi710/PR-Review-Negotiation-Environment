# PR Review Negotiation Environment — Full Build Instructions
> Feed this entire file to your AI coding tool. It contains every decision already made. Just build it.

---

## What You Are Building

An OpenEnv-compliant RL environment called **`pr-review-env`**.

An AI agent acts as a senior code reviewer in a simulated pull request lifecycle. The environment is inspired by how Anthropic's Mythos Preview model approaches code review in practice — not surface-level pattern matching, but deep reasoning about **what code is supposed to do vs. what it actually does**, catching subtle logic errors, security vulnerabilities disguised as style changes, and root causes rather than symptoms.

The agent must:
- Read a code diff and understand the **intent** vs. **implementation gap**
- Identify the correct issue category (logic, security, performance, correctness)
- Write an **actionable comment** that diagnoses the root cause, not just the symptom
- Make the right **decision** per turn (approve / request_changes / escalate)
- Track author responses across turns and judge whether fixes are genuine or superficial

This is a multi-turn negotiation loop. The agent reviews, the author responds (sometimes fixing correctly, sometimes partially, sometimes deceptively), and the agent must re-evaluate with full context of what was requested and whether it was actually addressed.

**Deployment target:** Hugging Face Spaces (Docker SDK), port 7860.

---

## Exact File Structure to Create

```
pr-review-env/
├── inference.py              ← MUST be in root, named exactly this
├── openenv.yaml
├── Dockerfile
├── requirements.txt
├── models.py
├── README.md
└── server/
    ├── __init__.py
    ├── app.py
    ├── environment.py
    ├── graders.py
    └── tasks/
        ├── __init__.py
        ├── single_pass.py
        ├── iterative.py
        └── escalation.py
```

---

## `openenv.yaml`

```yaml
name: pr-review-env
version: 0.1.0
description: >
  A multi-turn pull request review negotiation environment modeled after
  how senior engineers and capable AI systems actually review code: reasoning
  about intent vs. implementation, catching subtle security and logic bugs,
  evaluating root causes rather than symptoms, and negotiating with authors
  across multiple rounds to ensure genuine fixes.
tags:
  - openenv
  - code-review
  - software-engineering
  - security
  - multi-turn
tasks:
  - single-pass-review
  - iterative-negotiation
  - escalation-judgment
```

---

## `requirements.txt`

```
fastapi==0.115.0
uvicorn==0.30.6
pydantic==2.7.1
openai==1.30.1
openenv-core==0.2.1
httpx==0.27.0
```

---

## `models.py`

```python
from pydantic import BaseModel
from typing import Optional, List
from enum import Enum

class ReviewDecision(str, Enum):
    APPROVE = "approve"
    REQUEST_CHANGES = "request_changes"
    ESCALATE = "escalate"

class PRAction(BaseModel):
    decision: ReviewDecision
    comment: str        # Full reviewer comment — must identify root cause, not just symptom
    issue_category: str # One of: "logic", "security", "correctness", "performance", "none"

class PRObservation(BaseModel):
    turn: int
    diff: str
    pr_title: str
    pr_description: str
    review_history: List[dict]       # {"role": "reviewer"|"author", "content": str}
    author_response: Optional[str]
    done: bool
    message: str

class PRState(BaseModel):
    episode_id: str
    task_name: str
    turn: int
    max_turns: int
    review_history: List[dict]
    done: bool
    success: bool
    cumulative_reward: float
```

---

## `server/tasks/single_pass.py`

**Easy.** A subtle off-by-one in pagination logic. The bug is real but not obvious — requires understanding what the function is *supposed* to return for page 1, not just reading the arithmetic.

```python
TASK = {
    "name": "single-pass-review",
    "pr_title": "Fix pagination offset calculation",
    "pr_description": "Updates the page offset logic in the user listing API to use cleaner arithmetic.",
    "diff": """
--- a/api/users.py
+++ b/api/users.py
@@ -14,7 +14,7 @@ def get_users(page: int, page_size: int = 10):
     if page < 1:
         raise ValueError("Page must be >= 1")
-    offset = (page - 1) * page_size
+    offset = page * page_size
     return db.query(User).offset(offset).limit(page_size).all()
""",
    "ground_truth": {
        "bug_type": "logic",
        "correct_decision": "request_changes",
        # Root cause: page=1 should give offset=0, but new formula gives offset=page_size
        # Symptom is wrong offset. Root cause is the author removed the -1 adjustment
        # that accounts for 1-based page indexing. Agent must identify WHY it's wrong,
        # not just THAT it's wrong.
        "root_cause_keywords": [
            "page 1", "first page", "offset 0", "1-based", "zero-based",
            "off-by-one", "page minus 1", "page - 1", "skips first"
        ],
        "symptom_only_keywords": [
            "wrong offset", "incorrect", "should be different", "bug"
        ],
        "correct_issue_category": "logic",
    },
    "max_turns": 1,
    "author_responses": []
}
```

---

## `server/tasks/iterative.py`

**Medium.** SQL injection vulnerability disguised as a "sanitization improvement" PR. The author adds `.strip()` and frames it as a security fix — but the actual injection vector (string concatenation into a raw query) is untouched. On turn 2, the author adds a try/except — still not fixed. On turn 3, they finally use a parameterized query.

The agent must understand that `.strip()` and try/except do **nothing** to prevent SQL injection. This tests whether the agent reasons about *what the vulnerability actually is* vs. being fooled by the appearance of a fix.

```python
TASK = {
    "name": "iterative-negotiation",
    "pr_title": "Add input sanitization to profile update",
    "pr_description": "Adds sanitization before saving user bio to prevent malformed input.",
    "diff": """
--- a/api/profile.py
+++ b/api/profile.py
@@ -8,6 +8,7 @@ def update_bio(user_id: int, bio: str):
+    bio = bio.strip()
     db.execute("UPDATE users SET bio = '" + bio + "' WHERE id = " + str(user_id))
     return {"status": "updated"}
""",
    "ground_truth": {
        "bug_type": "security",
        "correct_decision_turn_1": "request_changes",
        "correct_decision_turn_2": "request_changes",  # try/except is not a fix
        "correct_decision_turn_3": "approve",           # parameterized query is a real fix
        # Root cause: string concatenation directly into SQL. strip() does not sanitize
        # SQL metacharacters. Agent must identify parameterized queries as the fix,
        # not any form of string preprocessing.
        "root_cause_keywords": [
            "sql injection", "string concatenation", "parameterized",
            "prepared statement", "user input in query", "raw sql",
            "escape", "unsanitized", "direct interpolation"
        ],
        "false_fix_keywords": [
            "strip", "try except", "exception handling", "error handling"
        ],
        "correct_issue_category": "security",
    },
    "max_turns": 3,
    "author_responses": [
        # Turn 1: superficial fix — strip + try/except, injection vector unchanged
        "Added more sanitization and error handling:\n```python\ntry:\n    bio = bio.strip()\n    db.execute(\"UPDATE users SET bio = '\" + bio + \"' WHERE id = \" + str(user_id))\nexcept Exception as e:\n    return {\"error\": str(e)}\n```\nThis should handle any bad inputs now.",
        # Turn 2: real fix — parameterized query
        "Switched to parameterized query as suggested:\n```python\nbio = bio.strip()\ndb.execute(\"UPDATE users SET bio = ? WHERE id = ?\", (bio, user_id))\n```",
    ]
}
```

---

## `server/tasks/escalation.py`

**Hard.** A hardcoded JWT secret disguised as a "readability refactor" — the PR description says "no functional changes." This is the Mythos-style test: the dangerous change is **hidden in plain sight** inside a PR that looks cosmetic. The author's first response adds a TODO comment but keeps the hardcoded secret. The agent must escalate (not just request_changes) because this is a critical security issue — hardcoded secrets in source code are immediately exploitable and cannot be treated as a normal review cycle item.

```python
TASK = {
    "name": "escalation-judgment",
    "pr_title": "Refactor auth token generation for readability",
    "pr_description": "Minor cleanup of token generation code. No functional changes.",
    "diff": """
--- a/auth/tokens.py
+++ b/auth/tokens.py
@@ -5,7 +5,7 @@ import time
 def generate_token(user_id: int) -> str:
-    secret = os.environ.get("JWT_SECRET", "supersecret")
+    secret = "supersecret"
     payload = {"user_id": user_id, "exp": time.time() + 3600}
     return jwt.encode(payload, secret, algorithm="HS256")
""",
    "ground_truth": {
        "bug_type": "security",
        "severity": "critical",
        # The diff removed the os.environ.get() call entirely and replaced it with
        # a hardcoded literal. This means:
        # 1. The secret is now in source control
        # 2. Anyone with repo access can forge tokens
        # 3. Cannot be rotated without a code deploy
        # 4. The PR description actively lies ("no functional changes")
        # Agent must recognize that this warrants ESCALATION, not just request_changes,
        # because: (a) it's critical severity, (b) the secret may already be exposed,
        # (c) the PR description is deceptive — this IS a functional change
        "correct_decision_turn_1": "escalate",
        "correct_decision_turn_2": "escalate",  # TODO comment is not acceptable for this severity
        "root_cause_keywords": [
            "hardcoded", "source control", "secret", "environment variable",
            "jwt secret", "forge", "token", "credentials", "repo access",
            "cannot rotate", "already exposed", "deceptive", "functional change"
        ],
        "escalation_trigger_keywords": [
            "critical", "immediate", "secret rotation", "security team",
            "already compromised", "not a normal review"
        ],
        "correct_issue_category": "security",
        "escalation_required": True,
    },
    "max_turns": 2,
    "author_responses": [
        # Turn 1: author adds a TODO but keeps the hardcoded secret
        "Added a TODO to fix this later:\n```python\n# TODO: move to env var before prod\nsecret = 'supersecret'\n```\nWe can clean this up in the next sprint.",
    ]
}
```

---

## `server/graders.py`

The grader evaluates **three dimensions** per step: issue category correctness, comment quality (root cause vs. symptom), and decision correctness. This reflects how a real senior reviewer would be assessed — not just "did you catch it" but "did you understand why."

```python
from models import PRAction, ReviewDecision
from typing import List

def score_issue_category(action: PRAction, correct_category: str) -> float:
    """
    +0.15 if agent correctly identifies issue category (logic/security/etc.)
    0.0 otherwise.
    Category must match exactly (case-insensitive).
    """
    return 0.15 if action.issue_category.lower() == correct_category.lower() else 0.0

def score_comment_quality(comment: str, root_cause_keywords: list, symptom_only_keywords: list = None) -> float:
    """
    Evaluates whether the comment identifies ROOT CAUSE, not just symptom.
    
    +0.25 if root cause keyword found in comment
    +0.0  if only symptom-level keywords found (comment is too shallow)
    -0.05 penalty if comment only uses symptom keywords with no root cause signal
    
    This is the key differentiator from simple keyword matching:
    a comment saying "this is wrong" scores 0, a comment explaining WHY it's
    wrong and WHAT the actual fix needs to be scores 0.25.
    """
    comment_lower = comment.lower()
    has_root_cause = any(kw.lower() in comment_lower for kw in root_cause_keywords)
    has_symptom_only = symptom_only_keywords and any(
        kw.lower() in comment_lower for kw in symptom_only_keywords
    )
    if has_root_cause:
        return 0.25
    elif has_symptom_only and not has_root_cause:
        return -0.05
    return 0.0

def score_decision(decision: ReviewDecision, correct_decision: str) -> float:
    """
    +0.35 if decision matches expected decision for this turn.
    0.0 otherwise.
    This is weighted highest because the decision is the most load-bearing signal.
    """
    return 0.35 if decision.value == correct_decision else 0.0

def score_efficiency(turn: int, max_turns: int) -> float:
    """
    +0.15 for resolving in minimum necessary turns.
    Scales linearly down to 0 as turns approach max.
    Single-turn tasks always get the full 0.15 if resolved.
    """
    if max_turns == 1:
        return 0.15
    ratio = 1.0 - (turn - 1) / max(max_turns - 1, 1)
    return round(0.15 * ratio, 2)

def penalty_approving_unfixed_bug(decision: ReviewDecision, bug_still_present: bool) -> float:
    """
    -0.3 if agent approves when the bug is demonstrably still present.
    This is the most severe penalty — approving broken/insecure code is the
    worst failure mode for a code reviewer.
    """
    if decision == ReviewDecision.APPROVE and bug_still_present:
        return -0.3
    return 0.0

def penalty_fooled_by_false_fix(comment: str, false_fix_keywords: list) -> float:
    """
    -0.1 if agent's comment treats a false fix (e.g. strip(), try/except for SQL injection)
    as if it addresses the actual vulnerability. Tests whether the agent understands
    what fixes the bug vs. what merely looks like it does.
    """
    if not false_fix_keywords:
        return 0.0
    comment_lower = comment.lower()
    if any(kw.lower() in comment_lower for kw in false_fix_keywords):
        # Only penalize if the comment seems to accept the false fix as valid
        acceptance_signals = ["fixed", "addressed", "handled", "resolved", "looks good", "approve"]
        if any(sig in comment_lower for sig in acceptance_signals):
            return -0.1
    return 0.0

def penalty_no_escalation(decision: ReviewDecision, escalation_required: bool) -> float:
    """
    -0.2 if escalation was required but agent only requested changes.
    Critical security issues (hardcoded secrets, auth bypass) are not normal
    review items — they require immediate escalation.
    """
    if escalation_required and decision == ReviewDecision.REQUEST_CHANGES:
        return -0.2
    return 0.0

def compute_step_reward(
    action: PRAction,
    correct_decision: str,
    root_cause_keywords: list,
    correct_issue_category: str,
    bug_still_present: bool,
    turn: int,
    max_turns: int,
    symptom_only_keywords: list = None,
    false_fix_keywords: list = None,
    escalation_required: bool = False,
) -> float:
    reward = 0.0
    reward += score_issue_category(action, correct_issue_category)
    reward += score_comment_quality(action.comment, root_cause_keywords, symptom_only_keywords)
    reward += score_decision(action.decision, correct_decision)
    reward += score_efficiency(turn, max_turns)
    reward += penalty_approving_unfixed_bug(action.decision, bug_still_present)
    reward += penalty_fooled_by_false_fix(action.comment, false_fix_keywords or [])
    reward += penalty_no_escalation(action.decision, escalation_required)
    return round(max(-1.0, min(1.0, reward)), 2)

def compute_final_score(rewards: list, max_turns: int) -> float:
    """Normalize cumulative reward to [0, 1]. Max possible per turn is 0.9."""
    max_possible = 0.9 * max_turns
    raw = sum(rewards)
    return round(min(max(raw / max(max_possible, 1), 0.0), 1.0), 3)
```

---

## `server/environment.py`

```python
import uuid
from models import PRAction, PRObservation, PRState, ReviewDecision
from server.tasks import single_pass, iterative, escalation
from server import graders

TASKS = {
    "single-pass-review": single_pass.TASK,
    "iterative-negotiation": iterative.TASK,
    "escalation-judgment": escalation.TASK,
}

class PRReviewEnvironment:
    def __init__(self):
        self._state = None
        self._task = None
        self._rewards = []

    def reset(self, task_name: str = "single-pass-review") -> PRObservation:
        self._task = TASKS[task_name]
        self._rewards = []
        self._state = PRState(
            episode_id=str(uuid.uuid4()),
            task_name=task_name,
            turn=0,
            max_turns=self._task["max_turns"],
            review_history=[],
            done=False,
            success=False,
            cumulative_reward=0.0,
        )
        return PRObservation(
            turn=0,
            diff=self._task["diff"],
            pr_title=self._task["pr_title"],
            pr_description=self._task["pr_description"],
            review_history=[],
            author_response=None,
            done=False,
            message="New PR ready for review. Read the diff carefully. Identify the root cause of any issues, not just the symptom. Submit your decision.",
        )

    def step(self, action: PRAction) -> tuple[PRObservation, float, bool, dict]:
        assert self._state is not None, "Call reset() first"
        assert not self._state.done, "Episode is already done"

        t = self._state
        task = self._task
        gt = task["ground_truth"]
        turn = t.turn + 1

        correct_key = f"correct_decision_turn_{turn}" if f"correct_decision_turn_{turn}" in gt else "correct_decision"
        correct_decision = gt.get(correct_key, gt.get("correct_decision", "request_changes"))

        author_responses = task.get("author_responses", [])
        # Bug is only genuinely fixed on the last author response
        is_final_author_response = (turn > len(author_responses))
        bug_still_present = not is_final_author_response

        reward = graders.compute_step_reward(
            action=action,
            correct_decision=correct_decision,
            root_cause_keywords=gt.get("root_cause_keywords", []),
            correct_issue_category=gt.get("correct_issue_category", "logic"),
            bug_still_present=bug_still_present and action.decision == ReviewDecision.APPROVE,
            turn=turn,
            max_turns=task["max_turns"],
            symptom_only_keywords=gt.get("symptom_only_keywords"),
            false_fix_keywords=gt.get("false_fix_keywords"),
            escalation_required=gt.get("escalation_required", False) and turn <= len(author_responses),
        )
        self._rewards.append(reward)
        t.cumulative_reward = round(sum(self._rewards), 2)
        t.turn = turn
        t.review_history.append({"role": "reviewer", "content": f"[{action.decision.value}] {action.comment}"})

        done = (
            turn >= task["max_turns"]
            or action.decision == ReviewDecision.APPROVE
            or action.decision == ReviewDecision.ESCALATE
        )
        t.done = done

        author_resp = None
        if not done and turn <= len(author_responses):
            author_resp = author_responses[turn - 1]
            t.review_history.append({"role": "author", "content": author_resp})

        if done:
            final_score = graders.compute_final_score(self._rewards, task["max_turns"])
            t.success = final_score >= 0.5
            message = f"Episode complete. Final score: {final_score:.3f}"
        else:
            message = "Author has responded. Re-read the diff. Has the actual root cause been addressed, or just the symptom?"

        return PRObservation(
            turn=turn,
            diff=task["diff"],
            pr_title=task["pr_title"],
            pr_description=task["pr_description"],
            review_history=list(t.review_history),
            author_response=author_resp,
            done=done,
            message=message,
        ), reward, done, {"episode_id": t.episode_id, "task": t.task_name}

    def state(self) -> PRState:
        return self._state

    def get_rewards(self):
        return self._rewards

    def get_final_score(self):
        return graders.compute_final_score(self._rewards, self._task["max_turns"])
```

---

## `server/app.py`

```python
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
```

---

## `Dockerfile`

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PYTHONPATH=/app
EXPOSE 7860

CMD ["uvicorn", "server.app:app", "--host", "0.0.0.0", "--port", "7860"]
```

---

## `inference.py`

**MUST be named exactly `inference.py` and placed in the root directory.**

```python
import os
import json
import httpx
from openai import OpenAI
from typing import List, Optional

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

        for step in range(1, MAX_STEPS + 1):
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
            steps_taken = step
            log_step(step=step, action=action_str, reward=reward, done=done, error=error)

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
    for task in TASKS:
        run_task(task)
```

---

## `server/__init__.py` and `server/tasks/__init__.py`

Both files: empty, just `# __init__.py`.

---

## `README.md`

```markdown
# PR Review Negotiation Environment

An OpenEnv-compliant RL environment where an AI agent acts as a senior code reviewer
in a multi-turn pull request negotiation loop.

## Motivation

Inspired by how Anthropic's Mythos Preview model approaches code review in practice:
not surface pattern-matching, but deep reasoning about what code is *supposed* to do
versus what it *actually* does. The environment rewards agents that identify root causes,
not symptoms — and penalizes agents fooled by cosmetic fixes that leave real vulnerabilities
intact.

## Action Space

```json
{
  "decision": "approve | request_changes | escalate",
  "issue_category": "logic | security | correctness | performance | none",
  "comment": "string — must identify root cause, not just symptom"
}
```

## Observation Space

```json
{
  "turn": "int",
  "diff": "string — the code diff",
  "pr_title": "string",
  "pr_description": "string",
  "review_history": "[{role, content}]",
  "author_response": "string | null",
  "done": "bool",
  "message": "string"
}
```

## Tasks

| Task | Difficulty | Description |
|---|---|---|
| `single-pass-review` | Easy | Off-by-one in pagination. Agent must explain WHY page=1 breaks, not just that it does. |
| `iterative-negotiation` | Medium | SQL injection disguised as a sanitization PR. Agent must recognize that strip() and try/except do not fix the injection vector. 3-turn loop. |
| `escalation-judgment` | Hard | Hardcoded JWT secret disguised as a readability refactor. PR description actively misleads. Agent must escalate, not just request changes. |

## Reward Function

Per step (max ~0.9):
- +0.35 correct decision (approve / request_changes / escalate)
- +0.25 comment identifies root cause (not just symptom)
- +0.15 correct issue category (logic / security / etc.)
- +0.15 efficiency bonus (resolved in minimum turns)
- −0.30 approving code with bug still present
- −0.20 failing to escalate a critical security issue
- −0.10 comment treats a false fix as if it resolves the vulnerability
- −0.05 comment only identifies symptom with no root cause signal

## Setup

```bash
pip install -r requirements.txt
uvicorn server.app:app --host 0.0.0.0 --port 7860
```

## Docker

```bash
docker build -t pr-review-env .
docker run -p 7860:7860 pr-review-env
```

## Baseline Scores (approximate)

| Task | Score |
|---|---|
| single-pass-review | ~0.70 |
| iterative-negotiation | ~0.45 |
| escalation-judgment | ~0.30 |

## Environment Variables

| Variable | Default | Required |
|---|---|---|
| `API_BASE_URL` | `https://router.huggingface.co/v1` | No |
| `MODEL_NAME` | `Qwen/Qwen2.5-72B-Instruct` | No |
| `HF_TOKEN` | — | Yes |
| `ENV_BASE_URL` | `http://localhost:7860` | No |
```

---

## Deployment Checklist

1. Push all files to GitHub repo
2. Create HF Space → Docker SDK → port 7860
3. Push repo to Space, wait for build
4. Test: `curl -X POST https://your-space.hf.space/reset -H "Content-Type: application/json" -d '{"task_name": "single-pass-review"}'`
5. Run validator: `./validate-submission.sh https://your-space.hf.space`
6. Submit HF Space URL before 11:59 PM IST

## Critical Rules (Do Not Break)

- `inference.py` must be at root, named exactly `inference.py`
- `API_BASE_URL` and `MODEL_NAME` must have default values in `inference.py`
- `HF_TOKEN` must have no default — raise ValueError if missing
- All LLM calls must use the OpenAI client
- stdout must emit exactly `[START]`, `[STEP]`, `[END]` lines in that order
- HF Space must be in "Running" state at submission time
- Container must fit within 2 vCPU / 8 GB RAM
