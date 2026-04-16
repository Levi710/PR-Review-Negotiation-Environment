import uuid
import difflib
import re
from models import PRAction, PRObservation, PRState, ReviewDecision
from server.tasks import single_pass, iterative, escalation, custom
from server import graders

TASKS = {
    "single-pass-review": single_pass.TASK,
    "iterative-negotiation": iterative.TASK,
    "escalation-judgment": escalation.TASK,
    "custom-review": custom.TASK,
}

class PRReviewEnvironment:
    def __init__(self):
        self._state = None
        self._task = None
        self._rewards = []
        self._current_diff = ""
        self._initial_diff = ""

    def _extract_code(self, text: str) -> str:
        """Extracts python code from markdown triple backticks if present."""
        match = re.search(r"```python\n(.*?)\n```", text, re.DOTALL)
        if match:
            return match.group(1).strip()
        # Fallback to any backticks
        match = re.search(r"```\n(.*?)\n```", text, re.DOTALL)
        if match:
            return match.group(1).strip()
        return None

    def _generate_unified_diff(self, old_code: str, new_code: str, filename: str = "file.py") -> str:
        """Generates a standard unified diff string between two versions of code."""
        old_lines = old_code.splitlines(keepends=True)
        new_lines = new_code.splitlines(keepends=True)
        diff = difflib.unified_diff(
            old_lines, new_lines, 
            fromfile=f"a/{filename}", tofile=f"b/{filename}"
        )
        return "".join(diff)

    def _get_base_code(self, diff_text: str) -> str:
        """Heuristic to extract the 'result' of a diff or just the text if it's a snippet."""
        if not any(x in diff_text for x in ["--- ", "+++ ", "@@ "]):
            return diff_text.strip()
        
        # If it's a real diff, we try to reconstruct the NEW state (all context + all additions)
        lines = diff_text.splitlines()
        result_lines = []
        for l in lines:
            if l.startswith("--- ") or l.startswith("+++ ") or l.startswith("@@ ") or l.startswith("index "):
                continue
            if l.startswith("-"):
                continue
            if l.startswith("+"):
                result_lines.append(l[1:])
            elif l.startswith(" "):
                result_lines.append(l[1:])
            else:
                result_lines.append(l)
        return "\n".join(result_lines).strip()

    def reset(self, task_name: str = "single-pass-review") -> PRObservation:
        self._task = TASKS[task_name]
        self._rewards = []
        self._initial_diff = self._task["diff"]
        self._current_diff = self._task["diff"]
        
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
            diff=self._current_diff,
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
        bug_still_present = correct_decision != ReviewDecision.APPROVE.value

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
            escalation_required=gt.get("escalation_required", False) and correct_decision == ReviewDecision.ESCALATE.value,
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
            
            # --- DYNAMIC DIFF INJECTION ---
            proposed_fix = self._extract_code(author_resp)
            if proposed_fix:
                # Compare the fix against the INITIAL buggy state to generate a fresh Red/Green diff
                base_code = self._get_base_code(self._initial_diff)
                self._current_diff = self._generate_unified_diff(base_code, proposed_fix)

        if done:
            final_score = graders.compute_final_score(self._rewards, task["max_turns"])
            t.success = final_score >= 0.5
            message = f"Episode complete. Final score: {final_score:.3f}"
        else:
            message = "Author has responded. Re-read the diff. Has the actual root cause been addressed, or just the symptom?"

        return PRObservation(
            turn=turn,
            diff=self._current_diff,
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
