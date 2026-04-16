import json
import re
from typing import Any

from models import PRAction


ALLOWED_CATEGORIES = {"logic", "security", "correctness", "performance", "none"}


def _strip_markdown_fences(text: str) -> str:
    text = text.strip()
    fenced = re.search(r"```(?:json)?\s*(.*?)\s*```", text, re.DOTALL | re.IGNORECASE)
    if fenced:
        return fenced.group(1).strip()
    return text


def _extract_json_object(text: str) -> dict[str, Any] | None:
    candidate = _strip_markdown_fences(text)
    try:
        parsed = json.loads(candidate)
        return parsed if isinstance(parsed, dict) else None
    except json.JSONDecodeError:
        pass

    start = candidate.find("{")
    if start == -1:
        return None

    depth = 0
    in_string = False
    escape = False
    for idx in range(start, len(candidate)):
        char = candidate[idx]
        if in_string:
            if escape:
                escape = False
            elif char == "\\":
                escape = True
            elif char == '"':
                in_string = False
            continue

        if char == '"':
            in_string = True
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                try:
                    parsed = json.loads(candidate[start : idx + 1])
                    return parsed if isinstance(parsed, dict) else None
                except json.JSONDecodeError:
                    return None
    return None


def _coerce_dict(payload: Any) -> tuple[dict[str, Any], str | None]:
    if isinstance(payload, dict):
        if "action" in payload:
            return _coerce_dict(payload["action"])
        for key in ("content", "message", "raw", "text", "response"):
            value = payload.get(key)
            if isinstance(value, str):
                parsed = _extract_json_object(value)
                if parsed:
                    return parsed, value
        return payload, None

    if isinstance(payload, str):
        parsed = _extract_json_object(payload)
        if parsed:
            return parsed, payload
        return {"comment": payload}, payload

    return {}, None


def normalize_decision(value: Any, fallback_text: str = "") -> str:
    text = f"{value or ''} {fallback_text}".lower().replace("-", "_").strip()
    compact = re.sub(r"[\s_]+", "_", text)

    if "escalate" in compact or "security_team" in compact:
        return "escalate"
    if "request_changes" in compact or "changes_requested" in compact:
        return "request_changes"
    if "do_not_approve" in compact or "cannot_approve" in compact or "not_approve" in compact:
        return "request_changes"
    if any(token in compact for token in ("reject", "needs_changes", "require_changes")):
        return "request_changes"
    if any(token in compact for token in ("approve", "approved", "accept", "lgtm", "merge")):
        return "approve"
    return "request_changes"


def normalize_issue_category(value: Any, fallback_text: str = "") -> str:
    explicit = str(value).lower().replace("-", "_") if value is not None else ""
    if explicit in ALLOWED_CATEGORIES:
        return explicit

    text = f"{explicit} {fallback_text}".lower()
    if "security" in text or "injection" in text or "secret" in text or "auth" in text:
        return "security"
    if (
        "logic" in text
        or "off_by_one" in text
        or "off-by-one" in text
        or "pagination" in text
        or "offset" in text
        or "page 1" in text
        or "skips first" in text
    ):
        return "logic"
    if "correct" in text or "bug" in text or "valid" in text:
        return "correctness"
    if "performance" in text or "latency" in text or "slow" in text:
        return "performance"
    return "none"


def normalize_action_payload(payload: Any) -> PRAction:
    data, raw_text = _coerce_dict(payload)
    comment_value = data.get("comment") or data.get("review") or data.get("feedback")
    if comment_value is None:
        comment_value = raw_text or "No detailed comment provided."

    if not isinstance(comment_value, str):
        comment_value = json.dumps(comment_value, ensure_ascii=False)

    decision = normalize_decision(data.get("decision") or data.get("verdict"), comment_value)
    issue_category = normalize_issue_category(
        data.get("issue_category") or data.get("category") or data.get("issue_type"),
        comment_value,
    )

    return PRAction(
        decision=decision,
        comment=comment_value.strip() or "No detailed comment provided.",
        issue_category=issue_category,
    )
