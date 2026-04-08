TASK = {
    "name": "escalation-judgment",
    "pr_title": "Refactor auth token generation for readability",
    "pr_description": "Minor refactor to clean up token generation code. No functional changes.",
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
        "severity": "critical",              # hardcoded secret — must escalate
        "correct_decision_turn_1": "escalate",
        "correct_decision_turn_2": "escalate",  # author's weak fix still not good enough
        "bug_keywords": ["hardcoded", "secret", "environment variable", "jwt secret", "credentials", "critical", "security"],
        "escalation_required": True,
    },
    "max_turns": 2,
    "author_responses": [
        # Turn 1 — author adds a comment but keeps hardcoded value
        "Added a TODO comment to fix later:\n```python\n# TODO: move to env var eventually\nsecret = 'supersecret'\n```",
    ]
}
