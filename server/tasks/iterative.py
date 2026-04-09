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
        "Added more sanitization and error handling:\\n```python\\ntry:\\n    bio = bio.strip()\\n    db.execute(\\\"UPDATE users SET bio = '\\\" + bio + \\\"' WHERE id = \\\" + str(user_id))\\nexcept Exception as e:\\n    return {\\\"error\\\": str(e)}\\n```\\nThis should handle any bad inputs now.",
        "Switched to parameterized query as suggested:\\n```python\\nbio = bio.strip()\\ndb.execute(\\\"UPDATE users SET bio = ? WHERE id = ?\\\", (bio, user_id))\\n```",
    ]
}
