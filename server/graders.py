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
    """
    return 0.35 if decision.value == correct_decision else 0.0

def score_efficiency(turn: int, max_turns: int) -> float:
    """
    +0.15 for resolving in minimum necessary turns.
    Scales linearly down to 0 as turns approach max.
    """
    if max_turns == 1:
        return 0.15
    ratio = 1.0 - (turn - 1) / max(max_turns - 1, 1)
    return round(0.15 * ratio, 2)

def penalty_approving_unfixed_bug(decision: ReviewDecision, bug_still_present: bool) -> float:
    """
    -0.3 if agent approves when the bug is demonstrably still present.
    """
    if decision == ReviewDecision.APPROVE and bug_still_present:
        return -0.3
    return 0.0

def penalty_fooled_by_false_fix(comment: str, false_fix_keywords: list) -> float:
    """
    -0.1 if agent's comment treats a false fix (e.g. strip(), try/except for SQL injection)
    as if it addresses the actual vulnerability.
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
