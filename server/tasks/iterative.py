TASK = {
    "name": "iterative-negotiation",
    "pr_title": "Add user input sanitization",
    "pr_description": "Adds sanitization before saving user bio to database.",
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
        "correct_decision_turn_2": "request_changes",   # partial fix not enough
        "correct_decision_turn_3": "approve",            # full fix accepted
        "bug_keywords": ["sql injection", "parameterized", "f-string", "string concatenation", "unsafe", "escape"],
    },
    "max_turns": 3,
    "author_responses": [
        # Turn 1 author response (partial fix — still vulnerable)
        "Fixed the bio input. Added .strip() and also wrapped in try/except now:\n```python\ntry:\n    bio = bio.strip()\n    db.execute(\"UPDATE users SET bio = '\" + bio + \"' WHERE id = \" + str(user_id))\nexcept Exception as e:\n    return {\"error\": str(e)}\n```",
        # Turn 2 author response (full fix — parameterized query)
        "Okay, switched to parameterized query:\n```python\nbio = bio.strip()\ndb.execute(\"UPDATE users SET bio = ? WHERE id = ?\", (bio, user_id))\n```",
    ]
}
