from pydantic import BaseModel
from typing import Optional, List, Literal
from enum import Enum

class ReviewDecision(str, Enum):
    APPROVE = "approve"
    REQUEST_CHANGES = "request_changes"
    ESCALATE = "escalate"

class PRAction(BaseModel):
    decision: ReviewDecision
    comment: str  # The reviewer's comment/feedback text

class PRObservation(BaseModel):
    turn: int
    diff: str                        # The code diff being reviewed
    pr_title: str
    pr_description: str
    review_history: List[dict]       # List of {"role": "reviewer"|"author", "content": str}
    author_response: Optional[str]   # Author's latest response (None on first turn)
    done: bool
    message: str                     # Feedback message to agent

class PRState(BaseModel):
    episode_id: str
    task_name: str
    turn: int
    max_turns: int
    review_history: List[dict]
    done: bool
    success: bool
    cumulative_reward: float
