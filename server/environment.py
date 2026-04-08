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
            message="New PR ready for review. Examine the diff and submit your decision.",
        )

    def step(self, action: PRAction) -> tuple[PRObservation, float, bool, dict]:
        assert self._state is not None, "Call reset() first"
        assert not self._state.done, "Episode is already done"

        t = self._state
        task = self._task
        gt = task["ground_truth"]
        turn = t.turn + 1

        # Determine correct decision for this turn
        correct_key = f"correct_decision_turn_{turn}" if f"correct_decision_turn_{turn}" in gt else "correct_decision"
        correct_decision = gt.get(correct_key, gt.get("correct_decision", "request_changes"))

        # Determine if bug is still present or fully fixed at this turn
        author_responses = task.get("author_responses", [])
        # Bug is fixed only on the final author response (last response in list)
        is_final_response = (turn > len(author_responses))
        bug_still_present = not is_final_response or (turn == 1 and task["max_turns"] == 1)
        bug_already_fixed = is_final_response and action.decision == ReviewDecision.REQUEST_CHANGES

        reward = graders.compute_step_reward(
            action=action,
            correct_decision=correct_decision,
            bug_keywords=gt["bug_keywords"],
            bug_still_present=bug_still_present and action.decision == ReviewDecision.APPROVE,
            bug_already_fixed=bug_already_fixed,
            turn=turn,
            max_turns=task["max_turns"],
        )
        self._rewards.append(reward)
        t.cumulative_reward = round(sum(self._rewards), 2)
        t.turn = turn

        # Add agent review to history
        t.review_history.append({"role": "reviewer", "content": f"[{action.decision.value}] {action.comment}"})

        # Check done
        done = (turn >= task["max_turns"]) or (action.decision == ReviewDecision.APPROVE) or (action.decision == ReviewDecision.ESCALATE)
        t.done = done

        # Determine author response for next turn
        author_resp = None
        if not done and turn <= len(author_responses):
            author_resp = author_responses[turn - 1]
            t.review_history.append({"role": "author", "content": author_resp})

        if done:
            final_score = graders.compute_final_score(self._rewards, task["max_turns"])
            t.success = final_score >= 0.5
            message = f"Episode complete. Final score: {final_score:.3f}"
        else:
            message = "Author has responded. Re-review the changes."

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
