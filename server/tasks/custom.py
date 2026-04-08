# Dynamic Custom Task
# This file is updated via the /set_custom_task API endpoint.

TASK = {
    "name": "custom-review",
    "pr_title": "Custom Review Session",
    "pr_description": "User-provided code snippet for review.",
    "diff": "",
    "ground_truth": {
        "bug_type": "unknown",
        "correct_decision": "request_changes",
        "bug_keywords": [],
    },
    "max_turns": 3,
    "author_responses": [
        "I have addressed the concerns in the latest update. Please take a look.",
        "The suggested changes have been implemented. Ready for final review."
    ]
}
