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
