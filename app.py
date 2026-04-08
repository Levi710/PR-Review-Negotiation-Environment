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
    /* Sidebar Labels & Sections */
    .section-label {
        font-size: 0.8rem;
        font-weight: 800;
        color: #000000 !important;
        margin-top: 1rem;
        margin-bottom: 0.3rem;
        text-transform: uppercase;
        letter-spacing: 0.05rem;
    }
    
    /* Expander visibility fix */
    .stExpander details summary p {
        color: #000000 !important;
        font-weight: 700 !important;
    }
    .stExpander details div {
        color: #1a1a1a !important;
    }
    
    /* Sidebar captions and help text */
    [data-testid="stSidebar"] [data-testid="stCaptionContainer"] {
        color: #000000 !important;
        font-weight: 600 !important;
    }
    
    /* Links in sidebar */
    [data-testid="stSidebar"] a {
        color: #5533ff !important;
        text-decoration: underline !important;
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

/* Visibility Fixes — Ensures all text is high contrast */
[data-testid="stWidgetLabel"] p, [data-testid="stWidgetLabel"], .section-label { 
    color: #1e293b !important; 
    font-weight: 700 !important; 
    text-transform: uppercase !important;
}

/* Force high contrast for all alert/info boxes */
.stAlert, [data-testid="stNotification"], [data-testid="stNotificationContent"] {
    background-color: #ffffff !important; 
    border: 1px solid #004085 !important;
}

.stAlert p, .stAlert div, [data-testid="stNotification"] p, [data-testid="stNotification"] div {
    color: #004085 !important; 
    font-weight: 600 !important;
}

/* Primary Button Styling */
button[kind="primary"] {
    background-color: #1a7f3c !important;
    color: white !important;
    border: none !important;
    font-weight: 700 !important;
}
button[kind="secondary"] {
    background-color: #f6f8fa !important;
    color: #24292f !important;
    border: 1px solid #d0d7de !important;
    font-weight: 600 !important;
}

/* Form Field Colors */
.stTextArea textarea, .stTextInput input, .stSelectbox select {
    color: #1e293b !important;
    border: 1px solid #d0d7de !important;
}
</style>
""", unsafe_allow_html=True)

# ─── Constants ───────────────────────────────────────────────────────────────
ENV_BASE_URL = "http://localhost:8000"
TASKS = ["single-pass-review", "iterative-negotiation", "escalation-judgment", "custom-review"]

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
    filename = "unknown_file"
    for line in lines:
        if line.startswith("--- a/"): filename = line.replace("--- a/", "")
        elif line.startswith("+++ b/"): filename = line.replace("+++ b/", "")
    
    html_lines = ['<div class="diff-container">']
    html_lines.append(f'<div class="diff-header-bar"><span>{filename}</span><span>Active Hunks</span></div>')
    
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

# ─── Initialization ────────────────────────────────────────────────────────────
def init_state():
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "current_task" not in st.session_state:
        st.session_state.current_task = None
    if "api_url_override" not in st.session_state:
        st.session_state.api_url_override = os.getenv("API_BASE_URL", "https://router.huggingface.co/v1")
    if "hf_token_override" not in st.session_state:
        st.session_state.hf_token_override = os.getenv("HF_TOKEN", "")

init_state()

# ─── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    # Onboarding Guide
    with st.expander("❓ Need help finding your API key?", expanded=False):
        st.markdown(f"""
        **Working Models (Free):**
        - Select any model with **(Free - Ready)** to use our internal credits.
        
        **For Hugging Face:**
        1. [Create an API Token](https://huggingface.co/settings/tokens).
        2. Paste into 'Advanced Settings'.
        
        **For Groq:**
        1. [Create an API Key](https://console.groq.com/keys).
        """)

    # Health Check
    try:
        h = httpx.get(f"{ENV_BASE_URL}/health", timeout=1)
        if h.status_code == 200: st.sidebar.caption("🟢 API Engine Online")
        else: st.sidebar.caption("🔴 API Engine Error")
    except:
        st.sidebar.caption("⚪ API Engine Connecting...")

    st.markdown('<div class="section-label">Task Difficulty</div>', unsafe_allow_html=True)
    default_task_idx = TASKS.index(st.session_state.get("selected_task_override", "single-pass-review"))
    task_name = st.selectbox("Select Task", TASKS, index=default_task_idx, label_visibility="collapsed")
    
    # Model Selection with Presets
    MODEL_PRESETS = {}
    
    # Highlighting Internal Working Models (Secrets)
    if os.getenv("gemma4"):
        MODEL_PRESETS["Gemma 4 31B (Free - Ready)"] = {"id": "google/gemma-4-31b-it", "url": "https://integrate.api.nvidia.com/v1", "token": os.getenv("gemma4")}
    if os.getenv("nemotron3"):
        MODEL_PRESETS["Nemotron 3 120B (Free - Ready)"] = {"id": "nvidia/nemotron-3-super-120b-a12b", "url": "https://integrate.api.nvidia.com/v1", "token": os.getenv("nemotron3")}
    if os.getenv("qwen"):
        MODEL_PRESETS["Qwen 3.5 122B (Free - Ready)"] = {"id": "qwen/qwen3.5-122b-a10b", "url": "https://integrate.api.nvidia.com/v1", "token": os.getenv("qwen")}
    
    # Standard Presets
    MODEL_PRESETS.update({
        "Qwen 2.5 72B (HF)": {"id": "Qwen/Qwen2.5-72B-Instruct", "url": "https://router.huggingface.co/v1", "token": None},
        "Llama 3.1 8B (HF)": {"id": "meta-llama/Llama-3.1-8B-Instruct", "url": "https://router.huggingface.co/v1", "token": None},
        "Gemma 2 9B (HF)": {"id": "google/gemma-2-9b-it", "url": "https://router.huggingface.co/v1", "token": None},
        "Llama 3 70B (Groq)": {"id": "llama3-70b-8192", "url": "https://api.groq.com/openai/v1", "token": None},
        "Custom (Type ID Below)": {"id": "custom", "url": "", "token": None}
    })
    
    st.markdown('<div class="section-label">Select Model</div>', unsafe_allow_html=True)
    selected_preset = st.selectbox("Model Preset", list(MODEL_PRESETS.keys()), label_visibility="collapsed")
    
    preset_data = MODEL_PRESETS[selected_preset]
    
    # Logic to auto-fill tokens and URLs
    if preset_data["token"]:
        st.session_state["hf_token_override"] = preset_data["token"]
    if preset_data["url"]:
        st.session_state["api_url_override"] = preset_data["url"]
        
    if preset_data["id"] == "custom":
        model_id = st.text_input("Custom Model ID", value="Qwen/Qwen2.5-72B-Instruct")
    else:
        model_id = preset_data["id"]

    # Advanced Settings Expander
    with st.expander("⚙️ Advanced API Settings", expanded=False):
        st.markdown('<div class="section-label">API Base URL</div>', unsafe_allow_html=True)
        current_url = st.session_state.get("api_url_override", "https://router.huggingface.co/v1")
        api_url = st.text_input("URL", value=current_url, label_visibility="collapsed")
        
        st.markdown('<div class="section-label">API Token / Key</div>', unsafe_allow_html=True)
        hf_token = st.text_input("Token", type="password", value=os.getenv("HF_TOKEN", ""), label_visibility="collapsed")

    if "api_url_override" in st.session_state:
        api_url = st.session_state["api_url_override"]

    st.divider()
    st.markdown('<div class="section-label">Custom Review Config</div>', unsafe_allow_html=True)
    custom_title = st.text_input("PR Title", value="Custom Review", key="custom_title")
    custom_desc = st.text_area("PR Description", value="Reviewing custom code...", key="custom_desc")
    
    # Selection for local files
    all_files = []
    for root, _, files in os.walk("."):
        if ".git" in root or "__pycache__" in root: continue
        for f in files:
            all_files.append(os.path.join(root, f).replace(".\\", ""))
    
    selected_file = st.selectbox("Load from local file", ["-- Select --"] + sorted(all_files))
    loaded_code = ""
    if selected_file != "-- Select --":
        try:
            with open(selected_file, "r") as f:
                loaded_code = f.read()
        except Exception as e:
            st.error(f"Error loading file: {e}")

    custom_diff = st.text_area("Code to Review", value=loaded_code if loaded_code else "", height=200, key="custom_diff")
    
    if st.button("Update Custom Task", use_container_width=True):
        try:
            r = httpx.post(f"{ENV_BASE_URL}/config/custom", json={
                "diff": custom_diff,
                "pr_title": custom_title,
                "pr_description": custom_desc
            }, timeout=30)
            if r.status_code == 200:
                st.session_state["selected_task_override"] = "custom-review"
                st.success("Custom task updated! Click 'Initialize' below.")
                st.rerun()
            else:
                st.error(f"Failed to configure: {r.text}")
        except Exception as e:
            st.error(f"Connection error: {e}")

    st.divider()

    if st.button("Initialize environment", use_container_width=True, type="primary"):
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
