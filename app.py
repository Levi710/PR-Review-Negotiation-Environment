"""
PR Review Command Center — Streamlit Dashboard
Light Theme Revision — Matches User Specification
"""

import streamlit as st
import json
import time
import os
import httpx
from openai import OpenAI
from models import PRAction, ReviewDecision

# ─── Page Config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="PR Review Command Center",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── Custom CSS (Light Theme Optimization) ────────────────────────────────────
st.markdown("""
<style>
/* Base Light Theme */
.stApp { background-color: #ffffff; color: #31333f; }

/* Sidebar Styling */
[data-testid="stSidebar"] { 
    background-color: #f0f2f6; 
    border-right: 1px solid #e6e9ef; 
}
[data-testid="stSidebar"] .section-label { 
    color: #5e6a75; 
    font-size: 0.7rem; 
    font-weight: 700; 
    text-transform: uppercase; 
    letter-spacing: 0.05em;
    margin-top: 1.5rem;
    margin-bottom: 0.5rem;
}

/* Metric Cards */
[data-testid="stMetric"] {
    background: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 0.5rem;
    padding: 1.25rem;
    box-shadow: 0 1px 3px rgba(0,0,0,0.02);
}
[data-testid="stMetricLabel"] { color: #64748b !important; font-size: 0.8rem; font-weight: 500; text-transform: none; }
[data-testid="stMetricValue"] { color: #1e293b !important; font-size: 1.75rem; font-weight: 600; }

/* Status Badges */
.badge-approve  { background:#e6ffec; color:#1a7f3c; border:1px solid #acf2bd; padding:4px 12px; border-radius:20px; font-size:12px; font-weight:600; }
.badge-request  { background:#ffebe9; color:#cf222e; border:1px solid #ff818244; padding:4px 12px; border-radius:20px; font-size:12px; font-weight:600; }
.badge-escalate { background:#fff8c5; color:#9a6700; border:1px solid #d4a72c44; padding:4px 12px; border-radius:20px; font-size:12px; font-weight:600; }
.badge-running  { background:#ddf4ff; color:#0969da; border:1px solid #54aeff44; padding:4px 12px; border-radius:20px; font-size:12px; font-weight:600; }

/* Tabs Integration */
.stTabs [data-baseweb="tab-list"] { gap: 24px; border-bottom: 1px solid #e2e8f0; margin-bottom: 1rem; }
.stTabs [data-baseweb="tab"] { color: #64748b; font-weight: 500; border-bottom: none; padding-bottom: 8px; }
.stTabs [aria-selected="true"] { color: #1e293b; border-bottom: 2px solid #1e293b !important; }

/* Dark Diff View (Embedded for Contrast) */
.diff-container {
    background: #0d1117;
    border: 1px solid #30363d;
    border-radius: 6px;
    font-family: 'SFMono-Regular', Consolas, monospace;
    font-size: 13px;
    overflow: hidden;
}
.diff-header-bar {
    background: #161b22;
    border-bottom: 1px solid #30363d;
    padding: 8px 16px;
    color: #8b949e;
    font-size: 12px;
    display: flex;
    justify-content: space-between;
}
.diff-line       { padding: 2px 16px; display: flex; gap: 12px; color: #e6edf3; white-space: pre-wrap; }
.diff-line-add   { padding: 2px 16px; display: flex; gap: 12px; background: rgba(46,160,67,0.15); color: #aff5b4; white-space: pre-wrap; }
.diff-line-del   { padding: 2px 16px; display: flex; gap: 12px; background: rgba(248,81,73,0.15); color: #ffa198; white-space: pre-wrap; }
.diff-line-meta  { padding: 4px 16px; color: #8b949e; background: #161b22; font-size: 12px; }
.diff-ln         { color: #484f58; min-width: 32px; text-align: right; user-select: none; }

/* Chat Bubbles (Light Theme) */
.bubble-reviewer {
    background: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 4px 12px 12px 12px;
    padding: 12px 16px;
    font-size: 14px;
    margin-bottom: 4px;
    max-width: 85%;
    box-shadow: 0 1px 2px rgba(0,0,0,0.03);
}
.bubble-author {
    background: #f1f5f9;
    border: 1px solid #e2e8f0;
    border-radius: 12px 4px 12px 12px;
    padding: 12px 16px;
    font-size: 14px;
    margin-left: auto;
    max-width: 85%;
    margin-bottom: 4px;
}
.chat-meta { font-size: 11px; color: #94a3b8; margin-bottom: 12px; margin-left:12px; }

/* Custom Progress Bar in Metric */
.reward-bar-wrap { height: 4px; background: #f1f5f9; border-radius: 2px; overflow: hidden; margin-top: 8px; width: 100px; }
.reward-bar-fill { height: 100%; border-radius: 2px; transition: width 0.4s ease-out; }

/* Forms */
.stTextArea textarea, .stTextInput input, .stSelectbox select {
    background: #ffffff !important;
    border: 1px solid #e2e8f0 !important;
    color: #1e293b !important;
}

/* Sidebar override for consistent casing */
.section-label { 
    color: #64748b !important;
    font-size: 0.7rem !important;
    font-weight: 700 !important;
    text-transform: uppercase !important;
    margin-bottom: 0.5rem !important;
}
</style>
""", unsafe_allow_html=True)

# ─── Constants ───────────────────────────────────────────────────────────────
ENV_BASE_URL = "http://localhost:8000"
TASKS = ["single-pass-review", "iterative-negotiation", "escalation-judgment"]

# ─── Helper Functions ─────────────────────────────────────────────────────────
def get_agent_action(obs: dict, model_name: str, api_base: str, token: str) -> dict:
    client = OpenAI(base_url=api_base, api_key=token)
    
    system_prompt = """You are a senior software engineer performing a pull request code review.
You must respond with EXACTLY this JSON format and nothing else:
{
  "decision": "<approve|request_changes|escalate>",
  "comment": "<your detailed review comment>"
}"""

    history = "\n".join(f"[{h['role'].upper()}]: {h['content']}" for h in obs.get("review_history", []))
    prompt = f"PR Title: {obs['pr_title']}\nPR Description: {obs['pr_description']}\n\nDiff:\n{obs['diff']}\n\nReview History:\n{history if history else 'First turn.'}\n\nAuthor's latest response: {obs.get('author_response') or 'N/A'}\n\nDecision JSON:"

    try:
        resp = client.chat.completions.create(
            model=model_name,
            messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": prompt}],
            max_tokens=300,
            temperature=0.2,
        )
        raw = resp.choices[0].message.content.strip()
        raw = raw.replace("```json", "").replace("```", "").strip()
        return json.loads(raw)
    except Exception as e:
        return {"decision": "request_changes", "comment": f"[Agent Error: {e}]"}

def format_diff_html(diff_text: str):
    lines = diff_text.split("\n")
    html_lines = ['<div class="diff-container">']
    html_lines.append('<div class="diff-header-bar"><span>src/api/users.py</span><span>Active Hunks</span></div>')
    
    for i, line in enumerate(lines):
        if line.startswith("+++") or line.startswith("---"):
            html_lines.append(f'<div class="diff-line-meta">{line}</div>')
        elif line.startswith("@@"):
            html_lines.append(f'<div class="diff-line-meta" style="background:#161b22">{line}</div>')
        elif line.startswith("+"):
            html_lines.append(f'<div class="diff-line-add"><span class="diff-ln">{i}</span><span>{line}</span></div>')
        elif line.startswith("-"):
            html_lines.append(f'<div class="diff-line-del"><span class="diff-ln">{i}</span><span>{line}</span></div>')
        else:
            html_lines.append(f'<div class="diff-line"><span class="diff-ln">{i}</span><span>{line}</span></div>')
            
    html_lines.append("</div>")
    return "\n".join(html_lines)

# ─── Session State ────────────────────────────────────────────────────────────
def init_state():
    if "initialized" not in st.session_state:
        st.session_state.update({
            "initialized": False,
            "turn": 0,
            "score": 0.0,
            "decision": "IDLE",
            "observation": {},
            "reward_history": [],
            "logs": [],
            "done": False
        })

init_state()

# ─── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown('<div class="section-label">Task Difficulty</div>', unsafe_allow_html=True)
    task_name = st.selectbox("Select Task", TASKS, label_visibility="collapsed")
    
    st.markdown('<div class="section-label">API Base URL</div>', unsafe_allow_html=True)
    api_url   = st.text_input("URL", value="https://router.huggingface.co/v1", label_visibility="collapsed")
    
    st.markdown('<div class="section-label">Model</div>', unsafe_allow_html=True)
    model_id  = st.text_input("ID", value="Qwen/Qwen2.5-72B-Instruct", label_visibility="collapsed")
    
    st.markdown('<div class="section-label">HF Token</div>', unsafe_allow_html=True)
    hf_token  = st.text_input("Token", type="password", value=os.getenv("HF_TOKEN", ""), label_visibility="collapsed")

    st.divider()

    if st.button("Initialize environment", use_container_width=True):
        try:
            r = httpx.post(f"{ENV_BASE_URL}/reset", json={"task_name": task_name}, timeout=30)
            obs = r.json()
            st.session_state.update({
                "initialized": True,
                "turn": 1,
                "score": 0.0,
                "decision": "RUNNING",
                "observation": obs,
                "reward_history": [],
                "logs": [f"[START] task={task_name}"],
                "done": False
            })
            st.rerun()
        except Exception as e:
            st.error(f"Reset failed: {e}")

    if st.session_state.reward_history:
        st.divider()
        st.markdown('<div class="section-label">Reward History</div>', unsafe_allow_html=True)
        import pandas as pd
        df = pd.DataFrame({"Turn": [f"T{i+1}" for i in range(len(st.session_state.reward_history))], "Reward": st.session_state.reward_history})
        st.bar_chart(df.set_index("Turn"), color="#1a7f3c", height=140)

# ─── Main Header ──────────────────────────────────────────────────────────────
if not st.session_state.initialized:
    st.markdown("## PR Review Negotiation Environment")
    st.info("Configure the environment in the sidebar and click **Initialize environment** to begin.")
    st.stop()

col_info, col_status = st.columns([4, 1])
obs = st.session_state.observation

with col_info:
    st.markdown(f"## {obs.get('pr_title', 'No Task Loaded')}")
    st.caption(f"#4821 · {task_name} · opened 2h ago by env-author")

with col_status:
    d = st.session_state.decision
    badge_class = {"APPROVE": "badge-approve", "REQUEST_CHANGES": "badge-request", "ESCALATE": "badge-escalate"}.get(d, "badge-running")
    st.markdown(f'<div style="text-align:right; margin-top:24px"><span class="{badge_class}">{d}</span></div>', unsafe_allow_html=True)

st.divider()

# ─── Metrics ──────────────────────────────────────────────────────────────────
m1, m2, m3 = st.columns(3)
with m1:
    st.metric("Cumulative reward", f"{st.session_state.score:.2f}")
    bar_color = "#1a7f3c" if st.session_state.score >= 0.7 else ("#ef9f27" if st.session_state.score >= 0.4 else "#e24b4a")
    st.markdown(f'<div class="reward-bar-wrap"><div class="reward-bar-fill" style="width:{int(min(1, st.session_state.score)*100)}%;background:{bar_color}"></div></div>', unsafe_allow_html=True)
with m2:
    st.metric("Turn", f"{st.session_state.turn} / 3")
    st.caption("Reviewer processing...")
with m3:
    st.metric("Episode status", "Running")
    st.caption("AI turn active")

st.divider()

# ─── Tabs ──────────────────────────────────────────────────────────────────────
tab_diff, tab_nego, tab_logs = st.tabs(["Diff view", "Negotiation timeline", "Raw logs"])

with tab_diff:
    st.markdown(format_diff_html(obs.get("diff", "")), unsafe_allow_html=True)

with tab_nego:
    history = obs.get("review_history", [])
    if not history:
        st.info("No turns taken yet. Click below to start.")
    else:
        for item in history:
            if item["role"] == "reviewer":
                st.markdown(f'<div class="bubble-reviewer"><strong>Reviewer (AI)</strong><br>{item["content"]}</div>', unsafe_allow_html=True)
                st.markdown(f'<div class="chat-meta">Turn {st.session_state.turn} Review</div>', unsafe_allow_html=True)
            else:
                st.markdown(f'<div class="bubble-author"><strong>Author (Env)</strong><br>{item["content"]}</div>', unsafe_allow_html=True)
                st.markdown(f'<div class="chat-meta" style="text-align:right; margin-right:12px">Author response</div>', unsafe_allow_html=True)
    
    if not st.session_state.done:
        st.divider()
        if st.button("▶ Run AI Review Step", use_container_width=True, type="primary"):
            if not hf_token:
                st.error("Missing HF Token.")
            else:
                with st.spinner("Analyzing..."):
                    action = get_agent_action(obs, model_id, api_url, hf_token)
                    try:
                        r = httpx.post(f"{ENV_BASE_URL}/step", json={"action": action}, timeout=30)
                        res = r.json()
                        st.session_state.observation = res["observation"]
                        st.session_state.score += res["reward"]
                        st.session_state.reward_history.append(res["reward"])
                        st.session_state.done = res["done"]
                        st.session_state.decision = action["decision"].upper()
                        if not st.session_state.done: st.session_state.turn += 1
                        st.rerun()
                    except Exception as e:
                        st.error(f"Step failed: {e}")

with tab_logs:
    st.code("\n".join(st.session_state.logs), language="bash")
