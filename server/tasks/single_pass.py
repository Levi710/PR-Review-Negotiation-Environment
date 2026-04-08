TASK = {
    "name": "single-pass-review",
    "pr_title": "Fix pagination offset calculation",
    "pr_description": "Updates the page offset logic in the user listing API.",
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
        "bug_type": "logic",               # off-by-one: page 1 should have offset 0, not page_size
        "correct_decision": "request_changes",
        "bug_keywords": ["off-by-one", "offset", "page 1", "page-1", "first page", "wrong offset", "should be page-1", "page minus"],
    },
    "max_turns": 1,
    "author_responses": []  # No author response needed — single pass only
}
