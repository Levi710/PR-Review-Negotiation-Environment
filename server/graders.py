from models import PRAction, ReviewDecision
from typing import List

def score_comment_relevance(comment: str, keywords: list[str]) -> float:
    """Returns 0.3 if any ground truth keyword appears in the comment (case-insensitive), else 0.0"""
    comment_lower = comment.lower()
    for kw in keywords:
        if kw.lower() in comment_lower:
            return 0.3
    return 0.0

def score_decision(decision: ReviewDecision, correct_decision: str) -> float:
    """Returns 0.3 if decision matches expected, 0.0 otherwise"""
    return 0.3 if decision.value == correct_decision else 0.0

def score_efficiency(turns_taken: int, max_turns: int) -> float:
    """Returns 0.2 if resolved in minimum turns, scales down linearly"""
    if max_turns == 1:
        return 0.2
    ratio = 1.0 - (turns_taken - 1) / max(max_turns - 1, 1)
    return round(0.2 * ratio, 2)

def penalty_wrong_approve(decision: ReviewDecision, bug_still_present: bool) -> float:
    """Returns -0.2 if agent approves when bug is still present"""
    if decision == ReviewDecision.APPROVE and bug_still_present:
        return -0.2
    return 0.0

def penalty_unnecessary_request(decision: ReviewDecision, bug_already_fixed: bool) -> float:
    """Returns -0.1 if agent keeps requesting changes after bug is fully fixed"""
    if decision == ReviewDecision.REQUEST_CHANGES and bug_already_fixed:
        return -0.1
    return 0.0

def compute_step_reward(
    action: PRAction,
    correct_decision: str,
    bug_keywords: list[str],
    bug_still_present: bool,
    bug_already_fixed: bool,
    turn: int,
    max_turns: int,
) -> float:
    reward = 0.0
    reward += score_comment_relevance(action.comment, bug_keywords)
    reward += score_decision(action.decision, correct_decision)
    reward += score_efficiency(turn, max_turns)
    reward += penalty_wrong_approve(action.decision, bug_still_present)
    reward += penalty_unnecessary_request(action.decision, bug_already_fixed)
    return round(max(0.0, min(1.0, reward)), 2)

def compute_final_score(rewards: list[float], max_turns: int) -> float:
    """Normalize cumulative reward to [0, 1]"""
    max_possible = 0.8 * max_turns  # 0.3 + 0.3 + 0.2 per turn
    raw = sum(rewards)
    return round(min(max(raw / max(max_possible, 1), 0.0), 1.0), 3)
