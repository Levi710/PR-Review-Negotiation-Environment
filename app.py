"""
PR Review Command Center — Studio Grade Professional Dashboard
Theme: High-Contrast Premium (Inter & Fira Code)
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
    page_icon="🎨",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── Global Styles (Professional Studio Theme) ────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=Fira+Code:wght@400;500&display=swap');

/* Main App */
.stApp {
    background-color: #f8fafc;
    font-family: 'Inter', sans-serif;
}

/* Sidebar Glassmorphism */
[data-testid="stSidebar"] {
    background: rgba(255, 255, 255, 0.8) !important;
    backdrop-filter: blur(12px);
    border-right: 1px solid rgba(226, 232, 240, 0.8);
}

/* Section Labels */
.section-label {
    font-size: 0.65rem;
    font-weight: 800;
    color: #64748b;
    text-transform: uppercase;
    letter-spacing: 0.1rem;
    margin-top: 1.5rem;
    margin-bottom: 0.5rem;
}

/* Premium Cards */
.metric-card {
    background: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 12px;
    padding: 1.5rem;
    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 2px 4px -1px rgba(0, 0, 0, 0.03);
    transition: transform 0.2s ease, box-shadow 0.2s ease;
}
.metric-card:hover {
    transform: translateY(-2px);
    box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1);
}

/* Status Badges */
.badge {
    padding: 4px 12px;
    border-radius: 9999px;
    font-size: 0.75rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.025em;
}
.badge-approve  { background: #dcfce7; color: #166534; border: 1px solid #bbf7d0; }
.badge-request  { background: #fee2e2; color: #991b1b; border: 1px solid #fecaca; }
.badge-escalate { background: #fef9c3; color: #854d0e; border: 1px solid #fef08a; }
.badge-running  { background: #dbeafe; color: #1e40af; border: 1px solid #bfdbfe; }

/* Timeline Bubbles */
.bubble {
    padding: 1.25rem;
    border-radius: 12px;
    font-size: 0.925rem;
    line-height: 1.6;
    margin-bottom: 0.5rem;
    border: 1px solid #e2e8f0;
    position: relative;
}
.bubble-reviewer {
    background: #ffffff;
    border-left: 4px solid #3b82f6;
    margin-right: 3rem;
    box-shadow: 0 1px 2px rgba(0,0,0,0.05);
}
.bubble-author {
    background: #f8fafc;
    border-right: 4px solid #64748b;
    margin-left: 3rem;
}
.bubble-meta {
    font-size: 0.7rem;
    color: #94a3b8;
    margin-top: 0.5rem;
    font-weight: 500;
}

/* Connecter lines for timeline */
.timeline-container {
    border-left: 2px dashed #e2e8f0;
    margin-left: 1.5rem;
    padding-left: 2rem;
    margin-top: 1rem;
}

/* Diff Container Overhaul */
.diff-container {
    background: #0f172a;
    border-radius: 12px;
    font-family: 'Fira Code', monospace;
    font-size: 0.85rem;
    overflow: hidden;
    color: #cbd5e1;
    border: 1px solid #1e293b;
}
.diff-header {
    background: #1e293b;
    padding: 10px 20px;
    font-size: 0.75rem;
    font-weight: 600;
    color: #94a3b8;
    display: flex;
    justify-content: space-between;
}
.diff-line { padding: 2px 20px; border-left: 4px solid transparent; white-space: pre-wrap; }
.diff-line-add { background: rgba(16, 185, 129, 0.1); border-left-color: #10b981; color: #6ee7b7; }
.diff-line-del { background: rgba(239, 68, 68, 0.1); border-left-color: #ef4444; color: #fca5a5; }

/* Thinking Animation */
@keyframes pulse {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.5; }
}
.thinking {
    animation: pulse 1.5s cubic-bezier(0.4, 0, 0.6, 1) infinite;
    color: #3b82f6;
    font-weight: 600;
}

/* Hide standard Streamlit elements for cleaner look */
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

# ─── Constants ───────────────────────────────────────────────────────────────
ENV_BASE_URL = "http://localhost:8000"
TASKS = ["single-pass-review", "iterative-negotiation", "escalation-judgment", "custom-review"]

# ─── Helper Functions ─────────────────────────────────────────────────────────
def check_api_connectivity(model_name: str, api_base: str, token: str):
    """Proactively validate API credentials."""
    if not token or len(token) < 5:
        return False, "Missing or invalid token format."
    try:
        client = OpenAI(base_url=api_base, api_key=token)
        # Low-cost connectivity check
        client.models.list()
        return True, "Connection Successful"
    except Exception as e:
        return False, f"Auth Error: {str(e)}"

def get_agent_action(obs: dict, model_name: str, api_base: str, token: str) -> dict:
    client = OpenAI(base_url=api_base, api_key=token)
    
    system_prompt = """You are a senior software engineer performing a pull request code review.
You must respond with EXACTLY this JSON format and nothing else:
{
  "decision": "<approve|request_changes|escalate>",
  "comment": "<your detailed review comment>"
}"""

    # Better formatting for the review history context
    history_blocks = []
    for h in obs.get("review_history", []):
        role = "REVIEWER" if h["role"] == "reviewer" else "AUTHOR"
        history_blocks.append(f"--- {role} ---\n{h['content']}")
    
    context = "\n\n".join(history_blocks)
    prompt = f"""
PR Title: {obs.get('pr_title', 'No Title')}
Description: {obs.get('pr_description', 'No Description')}

FILE DIFF:
{obs.get('diff', 'No Diff Available')}

NEGOTIATION HISTORY:
{context if context else 'Initial Review Phase'}

LATEST AUTHOR RESPONSE:
{obs.get('author_response', 'Waiting for input')}

Provide your code review decision and clear feedback:"""

    try:
        resp = client.chat.completions.create(
            model=model_name,
            messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": prompt}],
            max_tokens=500,
            temperature=0.1, # Conservative for professional review
        )
        raw = resp.choices[0].message.content.strip()
        # Clean potential markdown wrappers
        if "```json" in raw: raw = raw.split("```json")[1].split("```")[0]
        elif "```" in raw: raw = raw.split("```")[1].split("```")[0]
        return json.loads(raw)
    except Exception as e:
        return {
            "decision": "request_changes", 
            "comment": f"⚠️ CONNECTION ERROR: {str(e)}\nPlease check your API Key and Model ID in the sidebar."
        }

def format_diff_html(diff_text: str):
    lines = diff_text.split("\n")
    filename = "unknown_file"
    for line in lines:
        if line.startswith("+++ b/"): filename = line.replace("+++ b/", "")
    
    html = [f'<div class="diff-container"><div class="diff-header"><span>{filename}</span><span>UTF-8</span></div>']
    for line in lines:
        cls = "diff-line-add" if line.startswith("+") and not line.startswith("+++") else ("diff-line-del" if line.startswith("-") and not line.startswith("---") else "")
        html.append(f'<div class="diff-line {cls}">{line}</div>')
    html.append("</div>")
    return "\n".join(html)

# ─── Session State ────────────────────────────────────────────────────────────
def init_state():
    defaults = {
        "initialized": False,
        "turn": 0,
        "score": 0.0,
        "decision": "IDLE",
        "observation": {},
        "reward_history": [],
        "logs": [],
        "done": False,
        "api_url_override": os.getenv("API_BASE_URL", "https://router.huggingface.co/v1"),
        "hf_token_override": os.getenv("HF_TOKEN", ""),
        "api_validated": None
    }
    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val

init_state()

# ─── Sidebar (Glassmorphism Config) ───────────────────────────────────────────
with st.sidebar:
    st.markdown('<div style="text-align:center; padding:1rem 0;"><h1 style="font-size:1.5rem; color:#1e293b; margin:0;">🛠️ COMMAND</h1><p style="font-size:0.7rem; color:#64748b; font-weight:700; text-transform:uppercase; letter-spacing:3px;">Review Environment</p></div>', unsafe_allow_html=True)
    
    # Connection Shield Section
    st.markdown('<div class="section-label">Pipeline Configuration</div>', unsafe_allow_html=True)
    
    # Model Selection
    MODEL_PRESETS = {}
    if os.getenv("gemma4"): MODEL_PRESETS["Gemma 4 (NVIDIA Credits)"] = {"id": "google/gemma-4-31b-it", "url": "https://integrate.api.nvidia.com/v1", "token": os.getenv("gemma4")}
    if os.getenv("nemotron3"): MODEL_PRESETS["Nemotron 3 (NVIDIA Credits)"] = {"id": "nvidia/nemotron-3-super-120b-a12b", "url": "https://integrate.api.nvidia.com/v1", "token": os.getenv("nemotron3")}
    
    MODEL_PRESETS.update({
        "Qwen 2.5 72B (HF Router)": {"id": "Qwen/Qwen2.5-72B-Instruct", "url": "https://router.huggingface.co/v1", "token": None},
        "Llama 3.1 70B (Groq)": {"id": "llama3-70b-8192", "url": "https://api.groq.com/openai/v1", "token": None},
        "Custom ID": {"id": "custom", "url": "", "token": None}
    })
    
    selected_preset = st.selectbox("Intelligence Engine", list(MODEL_PRESETS.keys()), label_visibility="collapsed")
    preset = MODEL_PRESETS[selected_preset]
    
    if preset["id"] == "custom":
        model_id = st.text_input("Model ID", value="Qwen/Qwen2.5-72B-Instruct")
    else:
        model_id = preset["id"]
        if preset["token"]: st.session_state.hf_token_override = preset["token"]
        if preset["url"]: st.session_state.api_url_override = preset["url"]

    # Advanced Settings Logic: Hide inputs if using internal secrets
    is_internal = "token" in preset and preset["token"] is not None
    
    with st.expander("⚙️ Advanced API Settings", expanded=False):
        if is_internal:
            st.info("🔒 Using Secure Internal Connection. Manual editing disabled for this model.")
            api_url = preset["url"]
            hf_token = preset["token"]
            st.markdown(f"**Endpoint:** `{api_url}`")
            st.markdown("**Token:** `••••••••••••••••` (Internal Secret)")
        else:
            st.markdown('<div class="section-label">API Base URL</div>', unsafe_allow_html=True)
            api_url = st.text_input("URL", value=st.session_state.get("api_url_override", "https://router.huggingface.co/v1"), key="api_url_input")
            st.session_state["api_url_override"] = api_url
            
            st.markdown('<div class="section-label">API Token / Key</div>', unsafe_allow_html=True)
            hf_token = st.text_input("Token", type="password", value=st.session_state.get("hf_token_override", ""), key="hf_token_input")
            st.session_state["hf_token_override"] = hf_token

    st.session_state["api_url_override"] = api_url
    st.session_state["hf_token_override"] = hf_token
    
    if st.button("Verify Connection", use_container_width=True):
        ok, msg = check_api_connectivity(model_id, api_url, hf_token)
        st.session_state.api_validated = (ok, msg)
        if ok: st.success(msg)
        else: st.error(msg)
            
    # Task Loader
    st.markdown('<div class="section-label">Active Scenario</div>', unsafe_allow_html=True)
    task_name = st.selectbox("Target Task", TASKS, label_visibility="collapsed")
    
    if st.button("🚀 Initialize Pipeline", use_container_width=True, type="primary"):
        try:
            r = httpx.post(f"{ENV_BASE_URL}/reset", json={"task_name": task_name}, timeout=30)
            st.session_state.update({
                "initialized": True,
                "turn": 1,
                "score": 0.0,
                "decision": "RUNNING",
                "observation": r.json(),
                "reward_history": [],
                "done": False,
                "logs": [f"Pipeline initialized with {model_id}"]
            })
            st.rerun()
        except: st.error("Backend Error: Ensure API engine is running.")

# ─── Main View ────────────────────────────────────────────────────────────────
if not st.session_state.initialized:
    st.markdown("""
    <div style="text-align:center; padding:5rem 2rem;">
        <h1 style="font-weight:800; font-size:3rem; color:#1e293b;">Review Command Center</h1>
        <p style="color:#64748b; font-size:1.1rem; max-width:600px; margin:1rem auto;">Configure your Intelligence Engine in the sidebar and initialize the pipeline to begin the PR negotiation sequence.</p>
    </div>
    """, unsafe_allow_html=True)
    st.stop()

# Header Area
col_h1, col_h2 = st.columns([3, 1])
obs = st.session_state.observation
with col_h1:
    st.markdown(f'<p style="color:#64748b; font-size:0.7rem; font-weight:700; margin:0;">ACTIVE PR / {task_name.upper()}</p>', unsafe_allow_html=True)
    st.markdown(f'<h2 style="margin:0; font-weight:800; color:#1e293b;">{obs.get("pr_title", "Custom Scenario")}</h2>', unsafe_allow_html=True)
with col_h2:
    d = st.session_state.decision
    badge_cls = {"APPROVE": "badge-approve", "REQUEST_CHANGES": "badge-request", "ESCALATE": "badge-escalate"}.get(d, "badge-running")
    st.markdown(f'<div style="text-align:right; margin-top:1rem;"><span class="badge {badge_cls}">{d}</span></div>', unsafe_allow_html=True)

st.divider()

# Metric Section
m1, m2, m3, m4 = st.columns(4)
with m1:
    st.markdown(f'<div class="metric-card"><div style="color:#64748b; font-size:0.7rem; font-weight:700;">ACCURACY REWARD</div><div style="font-size:1.8rem; font-weight:800; color:#1e293b;">{st.session_state.score:.2f}</div></div>', unsafe_allow_html=True)
with m2:
    st.markdown(f'<div class="metric-card"><div style="color:#64748b; font-size:0.7rem; font-weight:700;">CONVERSATION TURN</div><div style="font-size:1.8rem; font-weight:800; color:#1e293b;">{st.session_state.turn} / 3</div></div>', unsafe_allow_html=True)
with m3:
    st.markdown(f'<div class="metric-card"><div style="color:#64748b; font-size:0.7rem; font-weight:700;">EPISODE STATUS</div><div style="font-size:1.2rem; font-weight:700; color:#3b82f6;">{ "COMPLETED" if st.session_state.done else "ENGAGED" }</div></div>', unsafe_allow_html=True)
with m4:
    st.markdown(f'<div class="metric-card"><div style="color:#64748b; font-size:0.7rem; font-weight:700;">ENGINE</div><div style="font-size:0.75rem; font-weight:600; color:#64748b; overflow:hidden; text-overflow:ellipsis;">{model_id}</div></div>', unsafe_allow_html=True)

st.write("")

# Content Tabs
t_diff, t_nego, t_graph = st.tabs(["📄 Code Diff", "💬 Negotiation Pipeline", "📈 Analytics"])

with t_diff:
    st.markdown(format_diff_html(obs.get("diff", "")), unsafe_allow_html=True)

with t_nego:
    history = obs.get("review_history", [])
    if not history:
        st.info("Pipeline waiting for initial reviewer analysis.")
    else:
        for item in history:
            is_rev = item["role"] == "reviewer"
            cls = "bubble-reviewer" if is_rev else "bubble-author"
            label = "REVIEW COMMAND" if is_rev else "AUTHOR RESPONSE"
            st.markdown(f'<div class="bubble {cls}"><strong>{label}</strong><br>{item["content"]}</div>', unsafe_allow_html=True)

    if not st.session_state.done:
        st.divider()
        if st.button("⚡ EXECUTE AI REVIEW STEP", use_container_width=True, type="primary"):
            st.markdown('<div class="thinking">AI Intelligence Engine is analyzing proposed changes...</div>', unsafe_allow_html=True)
            action = get_agent_action(obs, model_id, st.session_state.api_url_override, st.session_state.hf_token_override)
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
                st.error(f"Execution Error: {e}")

with t_graph:
    if st.session_state.reward_history:
        import pandas as pd
        df = pd.DataFrame({"Turn": [f"T{i+1}" for i in range(len(st.session_state.reward_history))], "Reward": st.session_state.reward_history})
        st.line_chart(df.set_index("Turn"), color="#3b82f6")
    else:
        st.caption("Insufficient data for analytics.")