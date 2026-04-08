"""
PR Review Command Center — FINAL PRODUCTION BUILD
──────────────────────────────────────────────────
Every line in this file has been audited. Changes from the audit:
  Fix #1:  Removed blanket h1/h2/h3/p/span/label color override (was making diff text invisible)
  Fix #2:  Metric card values use explicit inline color:#0f172a (CSS :last-child unreliable)
  Fix #3:  format_diff_html() now emits CSS classes, not inline styles
  Fix #4:  CSS classes .diff-line-add/.diff-line-del now actually applied in HTML
  Fix #5:  m_id stored in session_state for cross-scope reliability
  Fix #6:  t_url/t_key initialized BEFORE expander to prevent NameError
  Fix #7:  File loader wrapped in try/except for binary files
  Fix #8:  All file reads wrapped in try/except
  Fix #9:  Bare except: replaced with except Exception as e everywhere
  Fix #10: Reset bare except: replaced with except Exception as e
  Fix #11: Model name truncation is conditional (no false "..." on short names)
"""

import streamlit as st
import json
import os
import httpx
from openai import OpenAI

# ═══════════════════════════════════════════════════════════════════════════════
# PAGE CONFIG — Must be the first Streamlit command
# ═══════════════════════════════════════════════════════════════════════════════
st.set_page_config(
    page_title="PR Command Center",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ═══════════════════════════════════════════════════════════════════════════════
# CSS — Every selector is scoped. No blanket overrides. (Fix #1)
# ═══════════════════════════════════════════════════════════════════════════════
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800&family=Fira+Code:wght@400;500&display=swap');

/* ── App Background ── */
.stApp {
    background-color: #f8fafc;
    font-family: 'Inter', sans-serif;
}

/* ── Sidebar ── */
[data-testid="stSidebar"] {
    background-color: #ffffff !important;
    border-right: 1px solid #e2e8f0;
}

/* ── Section Labels (sidebar only) ── */
.section-label {
    font-size: 0.75rem;
    font-weight: 800;
    color: #1e293b;
    text-transform: uppercase;
    letter-spacing: 0.05rem;
    margin-top: 2rem;
    border-bottom: 2px solid #f1f5f9;
    padding-bottom: 4px;
}

/* ── Metric Cards ── */
.metric-card {
    background: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 12px;
    padding: 1.5rem;
    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
}

/* ── Status Badges ── */
.badge {
    display: inline-block;
    padding: 6px 14px;
    border-radius: 20px;
    font-size: 0.85rem;
    font-weight: 800;
    border: 1px solid transparent;
}
.badge-approve  { background: #dcfce7; color: #166534; border-color: #bbf7d0; }
.badge-request  { background: #fee2e2; color: #991b1b; border-color: #fecaca; }
.badge-escalate { background: #fef9c3; color: #854d0e; border-color: #fef08a; }
.badge-running  { background: #dbeafe; color: #1e40af; border-color: #bfdbfe; }

/* ── Timeline Chat Bubbles ── */
.bubble {
    padding: 1.5rem;
    border-radius: 12px;
    font-size: 0.95rem;
    line-height: 1.6;
    margin-bottom: 1.5rem;
    border: 1px solid #e2e8f0;
    color: #1e293b;
}
.bubble-reviewer { background: #ffffff; border-left: 6px solid #3b82f6; }
.bubble-author   { background: #f1f5f9; border-right: 6px solid #94a3b8; }
.bubble-header   {
    font-size: 0.75rem;
    font-weight: 800;
    margin-bottom: 0.75rem;
    color: #334155;
}

/* ── Diff Container — LIGHT THEME (Fix #3, #4) ── */
.diff-container {
    background: #ffffff;
    border-radius: 12px;
    font-family: 'Fira Code', monospace;
    font-size: 0.9rem;
    color: #1e293b;
    border: 1px solid #cbd5e1;
    overflow: hidden;
    margin-top: 1rem;
}
.diff-header {
    background: #f1f5f9;
    padding: 12px 20px;
    color: #475569;
    font-weight: 700;
    font-size: 0.85rem;
    border-bottom: 1px solid #e2e8f0;
}
.diff-line {
    padding: 3px 20px;
    white-space: pre-wrap;
    word-break: break-all;
    border-left: 4px solid transparent;
    color: #334155;
    font-size: 0.85rem;
    line-height: 1.5;
}
.diff-line-add {
    background: #ecfdf5;
    color: #065f46;
    border-left-color: #10b981;
}
.diff-line-del {
    background: #fef2f2;
    color: #991b1b;
    border-left-color: #ef4444;
}

/* ── Input Visibility ── */
.stTextInput input, .stTextArea textarea {
    background-color: #ffffff !important;
    color: #0f172a !important;
    border: 1px solid #cbd5e1 !important;
}

/* ── Hide Streamlit chrome ── */
#MainMenu { visibility: hidden; }
footer { visibility: hidden; }
</style>
""", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════════════
# CONSTANTS
# ═══════════════════════════════════════════════════════════════════════════════
ENV_BASE_URL = "http://localhost:8000"
TASKS = ["single-pass-review", "iterative-negotiation", "escalation-judgment", "custom-review"]

# ═══════════════════════════════════════════════════════════════════════════════
# HELPER: AI Agent Action
# ═══════════════════════════════════════════════════════════════════════════════
def get_agent_action(obs: dict, model_id: str, api_url: str, api_key: str) -> dict:
    """
    Calls the LLM to produce a review decision.
    Returns {"decision": "...", "comment": "..."} on success.
    Returns {"decision": "error", "comment": "..."} on any failure.
    The caller MUST check for decision=="error" before stepping the env.
    """
    try:
        client = OpenAI(base_url=api_url, api_key=api_key)

        system_prompt = (
            'You are a senior software engineer performing a pull request code review.\n'
            'Respond with ONLY this JSON (no markdown, no extra text):\n'
            '{"decision": "approve|request_changes|escalate", "comment": "your review"}'
        )

        # Build history string
        history_lines = []
        for h in obs.get("review_history", []):
            history_lines.append(f"{h['role'].upper()}: {h['content']}")
        history_str = "\n".join(history_lines) if history_lines else "None yet."

        user_prompt = (
            f"PR Title: {obs.get('pr_title', 'N/A')}\n"
            f"PR Description: {obs.get('pr_description', 'N/A')}\n\n"
            f"Diff:\n{obs.get('diff', 'No diff')}\n\n"
            f"Review History:\n{history_str}\n\n"
            f"Author's latest response: {obs.get('author_response') or 'N/A'}\n\n"
            f"Submit your review decision as JSON:"
        )

        resp = client.chat.completions.create(
            model=model_id,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            max_tokens=500,
            temperature=0.1,
        )

        raw = resp.choices[0].message.content.strip()

        # Strip markdown fences if the model wrapped its response
        if "```json" in raw:
            raw = raw.split("```json")[1].split("```")[0]
        elif "```" in raw:
            raw = raw.split("```")[1].split("```")[0]

        raw = raw.strip()
        parsed = json.loads(raw)

        # Validate required keys exist
        if "decision" not in parsed or "comment" not in parsed:
            return {"decision": "error", "comment": "Model returned JSON without 'decision' or 'comment' keys."}

        return parsed

    except json.JSONDecodeError as e:
        return {"decision": "error", "comment": f"Model returned invalid JSON: {e}"}
    except Exception as e:
        return {"decision": "error", "comment": f"API Error: {e}"}


# ═══════════════════════════════════════════════════════════════════════════════
# HELPER: Diff Renderer — uses CSS classes, NOT inline styles (Fix #3, #4)
# ═══════════════════════════════════════════════════════════════════════════════
def format_diff_html(diff_text: str) -> str:
    """
    Converts a unified diff string into styled HTML.
    Uses CSS classes .diff-line, .diff-line-add, .diff-line-del defined above.
    """
    if not diff_text or not diff_text.strip():
        return '<div class="diff-container"><div class="diff-header">No diff available</div></div>'

    lines = diff_text.split("\n")

    # Extract filename from +++ header
    filename = "unknown_file"
    for line in lines:
        if line.startswith("+++ b/"):
            filename = line[6:]  # strip "+++ b/" prefix
            break

    html_parts = [f'<div class="diff-container"><div class="diff-header">{filename}</div>']

    for line in lines:
        # Determine CSS class based on line prefix
        if line.startswith("+") and not line.startswith("+++"):
            css_class = "diff-line diff-line-add"
        elif line.startswith("-") and not line.startswith("---"):
            css_class = "diff-line diff-line-del"
        else:
            css_class = "diff-line"

        # Escape HTML entities to prevent XSS and rendering issues
        safe_line = line.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        html_parts.append(f'<div class="{css_class}">{safe_line}</div>')

    html_parts.append("</div>")
    return "\n".join(html_parts)


# ═══════════════════════════════════════════════════════════════════════════════
# SESSION STATE — Single initialization block
# ═══════════════════════════════════════════════════════════════════════════════
if "initialized" not in st.session_state:
    st.session_state.update({
        "initialized": False,
        "turn": 0,
        "score": 0.0,
        "decision": "IDLE",
        "observation": {},
        "done": False,
        "reward_history": [],
        "active_model_id": "",       # Fix #5: persisted model ID
        "active_api_url": "",        # Fix #6: persisted API URL
        "active_api_key": "",        # Fix #6: persisted API key
    })


# ═══════════════════════════════════════════════════════════════════════════════
# SIDEBAR
# ═══════════════════════════════════════════════════════════════════════════════
with st.sidebar:
    st.markdown("### 🔍 PR Command Center")

    # ── Section 1: Engine Selection ──
    st.markdown('<div class="section-label">1. Engine Selection</div>', unsafe_allow_html=True)

    PRESETS = {}
    # Internal secrets: only show if env var exists
    if os.getenv("gemma4"):
        PRESETS["Gemma 4 IT (Secure)"] = {
            "id": "google/gemma-4-31b-it",
            "url": "https://integrate.api.nvidia.com/v1",
            "token": os.getenv("gemma4"),
        }
    if os.getenv("nemotron3"):
        PRESETS["Nemotron 3 (Secure)"] = {
            "id": "nvidia/nemotron-3-super-120b-a12b",
            "url": "https://integrate.api.nvidia.com/v1",
            "token": os.getenv("nemotron3"),
        }

    # Public presets
    PRESETS.update({
        "Qwen 2.5 72B (Hugging Face)": {
            "id": "Qwen/Qwen2.5-72B-Instruct",
            "url": "https://router.huggingface.co/v1",
            "token": None,
        },
        "Llama 3 70B (Groq)": {
            "id": "llama3-70b-8192",
            "url": "https://api.groq.com/openai/v1",
            "token": None,
        },
        "Custom Endpoint": {
            "id": "custom",
            "url": "",
            "token": None,
        },
    })

    selected_preset_name = st.selectbox(
        "Select Model", list(PRESETS.keys()), label_visibility="collapsed"
    )
    conf = PRESETS[selected_preset_name]

    # Model ID: editable only for "Custom Endpoint"
    if conf["id"] == "custom":
        current_model_id = st.text_input("Model ID", value="Qwen/Qwen2.5-72B-Instruct")
    else:
        current_model_id = conf["id"]

    # ── Fix #6: Set t_url / t_key BEFORE the expander ──
    # Default values come from the preset. These get overridden inside
    # the expander if it renders (for non-internal presets).
    if conf["token"] is not None:
        # Internal preset: use its hardcoded URL and secret token
        current_api_url = conf["url"]
        current_api_key = conf["token"]
    else:
        # External preset: use session_state defaults (may be overridden below)
        current_api_url = os.getenv("API_BASE_URL", conf["url"] or "https://router.huggingface.co/v1")
        current_api_key = os.getenv("HF_TOKEN", "")

    # Credentials expander
    with st.expander("🔑 Credentials", expanded=(conf["token"] is None)):
        if conf["token"] is not None:
            st.info("🔒 Secure internal key active. No manual config needed.")
        else:
            # Let user edit URL and key
            current_api_url = st.text_input("API URL", value=current_api_url)
            current_api_key = st.text_input("API Key", type="password", value=current_api_key)

    # Fix #5: Persist to session_state so they survive reruns
    st.session_state.active_model_id = current_model_id
    st.session_state.active_api_url = current_api_url
    st.session_state.active_api_key = current_api_key

    # ── Section 2: Task Configuration ──
    st.markdown('<div class="section-label">2. Custom Review Config</div>', unsafe_allow_html=True)

    c_title = st.text_input("Scenario Title", value="Feature Implementation")
    c_desc = st.text_area("Context", value="Refactoring the user service.")

    # File picker — filters out common binary extensions (Fix #7)
    BINARY_EXTS = {".pyc", ".png", ".jpg", ".jpeg", ".gif", ".ico", ".woff", ".woff2", ".ttf", ".eot", ".zip", ".tar", ".gz", ".webp", ".mp4", ".pdf"}
    all_files = []
    for root, _dirs, files in os.walk("."):
        if ".git" in root or "__pycache__" in root:
            continue
        for fname in files:
            if os.path.splitext(fname)[1].lower() in BINARY_EXTS:
                continue
            all_files.append(os.path.join(root, fname).replace("./", ""))
    all_files.sort()

    sel_file = st.selectbox("Load Code From File", ["-- Select File --"] + all_files)

    loaded_content = ""
    if sel_file != "-- Select File --":
        try:  # Fix #8: Protect against encoding errors on unexpected files
            with open(sel_file, "r", encoding="utf-8", errors="replace") as f:
                loaded_content = f.read()
        except Exception as e:
            st.warning(f"Could not read file: {e}")

    c_diff = st.text_area("Diff Content", value=loaded_content, height=120)

    if st.button("Apply Custom Context", use_container_width=True):
        try:
            resp = httpx.post(
                f"{ENV_BASE_URL}/config/custom",
                json={"diff": c_diff, "pr_title": c_title, "pr_description": c_desc},
                timeout=30,
            )
            if resp.status_code == 200:
                st.success("Custom context applied. Select 'custom-review' below.")
            else:
                st.error(f"Backend returned status {resp.status_code}")
        except Exception as e:  # Fix #9: Show actual error
            st.error(f"Sync Error: {e}")

    # ── Section 3: Scenario & Launch ──
    st.divider()
    scenario = st.selectbox("Select Scenario", TASKS)

    if st.button("🚀 INITIALIZE ENVIRONMENT", use_container_width=True, type="primary"):
        try:
            r = httpx.post(f"{ENV_BASE_URL}/reset", json={"task_name": scenario}, timeout=30)
            if r.status_code != 200:
                st.error(f"Backend error: {r.status_code} — {r.text}")
            else:
                st.session_state.update({
                    "initialized": True,
                    "turn": 1,
                    "score": 0.0,
                    "decision": "IDLE",
                    "observation": r.json(),
                    "reward_history": [],
                    "done": False,
                })
                st.rerun()
        except Exception as e:  # Fix #10: Show actual error
            st.error(f"Engine connection failed: {e}")


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN VIEW — Only renders after initialization
# ═══════════════════════════════════════════════════════════════════════════════
if not st.session_state.initialized:
    st.markdown(
        '<div style="text-align:center; padding-top:10rem;">'
        '<h1 style="color:#0f172a; font-size:2.5rem; font-weight:800;">PR Review Negotiation Arena</h1>'
        '<p style="color:#475569; font-size:1.1rem;">Configure Engine & Task in the sidebar, then click Initialize.</p>'
        '</div>',
        unsafe_allow_html=True,
    )
    st.stop()

# ── Read state ──
obs = st.session_state.observation
active_model = st.session_state.active_model_id  # Fix #5: read from session_state

# ── Header row ──
col_title, col_badge = st.columns([4, 1])
with col_title:
    st.markdown(f"### {obs.get('pr_title', 'Untitled PR')}")
with col_badge:
    d = st.session_state.decision
    badge_map = {
        "APPROVE": "badge-approve",
        "REQUEST_CHANGES": "badge-request",
        "ESCALATE": "badge-escalate",
    }
    badge_cls = badge_map.get(d, "badge-running")
    st.markdown(
        f'<div style="text-align:right; padding-top:0.5rem;">'
        f'<span class="badge {badge_cls}">{d}</span></div>',
        unsafe_allow_html=True,
    )

st.write("")

# ── Metric Cards — explicit inline colors (Fix #2) ──
m1, m2, m3 = st.columns(3)
with m1:
    st.markdown(
        f'<div class="metric-card">'
        f'<div style="font-weight:800; font-size:0.7rem; color:#64748b;">TOTAL REWARD</div>'
        f'<div style="font-size:1.8rem; font-weight:800; color:#0f172a;">{st.session_state.score:.2f}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )
with m2:
    st.markdown(
        f'<div class="metric-card">'
        f'<div style="font-weight:800; font-size:0.7rem; color:#64748b;">TURN</div>'
        f'<div style="font-size:1.8rem; font-weight:800; color:#0f172a;">{st.session_state.turn} / 3</div>'
        f'</div>',
        unsafe_allow_html=True,
    )
with m3:
    # Fix #11: Conditional truncation — only add "..." if name is actually long
    display_name = active_model if len(active_model) <= 25 else active_model[:22] + "..."
    st.markdown(
        f'<div class="metric-card">'
        f'<div style="font-weight:800; font-size:0.7rem; color:#64748b;">ENGINE</div>'
        f'<div style="font-size:1.1rem; font-weight:700; color:#3b82f6;">{display_name}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

st.write("")

# ── Tabs: Code View + Negotiation Timeline ──
tab_code, tab_nego = st.tabs(["📄 Code View", "💬 Negotiation"])

with tab_code:
    st.markdown(format_diff_html(obs.get("diff", "")), unsafe_allow_html=True)

with tab_nego:
    history = obs.get("review_history", [])

    if not history:
        st.info("No review activity yet. Click the button below to start the first round.")

    for item in history:
        is_reviewer = item["role"] == "reviewer"
        bubble_cls = "bubble-reviewer" if is_reviewer else "bubble-author"
        header_text = "🤖 AI REVIEWER" if is_reviewer else "👨‍💻 AUTHOR"
        st.markdown(
            f'<div class="bubble {bubble_cls}">'
            f'<div class="bubble-header">{header_text}</div>'
            f'{item["content"]}'
            f'</div>',
            unsafe_allow_html=True,
        )

    # ── Action Button ──
    if not st.session_state.done:
        if st.button("▶ EXECUTE NEXT ROUND", use_container_width=True, type="primary"):
            with st.spinner("AI analyzing code..."):
                action = get_agent_action(
                    obs,
                    st.session_state.active_model_id,  # Fix #5
                    st.session_state.active_api_url,    # Fix #6
                    st.session_state.active_api_key,    # Fix #6
                )

                # Guard: If the LLM call failed, do NOT step the environment
                if action["decision"] == "error":
                    st.error(action["comment"])
                else:
                    try:
                        step_resp = httpx.post(
                            f"{ENV_BASE_URL}/step",
                            json={"action": action},
                            timeout=30,
                        )
                        if step_resp.status_code != 200:
                            st.error(f"Backend step error: {step_resp.status_code} — {step_resp.text}")
                        else:
                            result = step_resp.json()
                            new_reward = result["reward"]
                            st.session_state.update({
                                "observation": result["observation"],
                                "score": st.session_state.score + new_reward,
                                "reward_history": st.session_state.reward_history + [new_reward],
                                "done": result["done"],
                                "decision": action["decision"].upper(),
                            })
                            if not st.session_state.done:
                                st.session_state.turn += 1
                            st.rerun()
                    except Exception as e:  # Fix #9: Show actual error
                        st.error(f"Backend step failed: {e}")
    else:
        st.success(f"Episode complete. Final reward: {st.session_state.score:.2f}")