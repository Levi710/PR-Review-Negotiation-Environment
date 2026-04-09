TASK = {
    "name": "single-pass-review",
    "pr_title": "Fix pagination offset calculation",
    "pr_description": "Updates the page offset logic in the user listing API to use cleaner arithmetic.",
    "diff": """
--- a/api/users.py
+++ b/api/users.py
@@ -14,7 +14,7 @@ def get_users(page: int, page_size: int = 10):
     if page < 1:
         raise ValueError("Page must be >= 1")
-    offset = (page - 1) * page_size
+    offset = page * page_size
     return db.query(User).offset(offset).limit(page_size).all()
""",
    "ground_truth": {
        "bug_type": "logic",
        "correct_decision": "request_changes",
        "root_cause_keywords": [
            "page 1", "first page", "offset 0", "1-based", "zero-based",
            "off-by-one", "page minus 1", "page - 1", "skips first"
        ],
        "symptom_only_keywords": [
            "wrong offset", "incorrect", "should be different", "bug"
        ],
        "correct_issue_category": "logic",
    },
    "max_turns": 1,
    "author_responses": []
}
