"""
PR Review Command Center — Studio Grade Professional Dashboard
Theme: High-Contrast Premium (Inter & Fira Code)
Revision: Restored Custom Task Config & Visibility Fixes
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
    background: rgba(255, 255, 255, 0.9) !important;
    backdrop-filter: blur(12px);
    border-right: 1px solid rgba(226, 232, 240, 1.0);
}

/* Section Labels — DEEP CONTRAST */
.section-label {
    font-size: 0.7rem;
    font-weight: 800;
    color: #0f172a !important; /* Deep Black/Blue */
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
    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
}

/* Status Badges */
.badge {
    padding: 6px 16px;
    border-radius: 9999px;
    font-size: 0.8rem;
    font-weight: 800;
}
.badge-approve  { background: #dcfce7; color: #166534; border: 1px solid #bbf7d0; }
.badge-request  { background: #fee2e2; color: #991b1b; border: 1px solid #fecaca; }
.badge-escalate { background: #fef9c3; color: #854d0e; border: 1px solid #fef08a; }
.badge-running  { background: #dbeafe; color: #1e40af; border: 1px solid #bfdbfe; }

/* Timeline Bubbles — HIGH VISIBILITY */
.bubble {
    padding: 1.5rem;
    border-radius: 12px;
    font-size: 0.95rem;
    line-height: 1.6;
    margin-bottom: 1rem;
    border: 1px solid #e2e8f0;
    color: #1e293b;
}
.bubble-reviewer {
    background: #ffffff;
    border-left: 6px solid #3b82f6;
    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
}
.bubble-author {
    background: #f1f5f9;
    border-right: 6px solid #64748b;
}
.bubble-header {
    font-size: 0.75rem;
    font-weight: 800;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    margin-bottom: 0.5rem;
    color: #0f172a;
}

/* Diff Container */
.diff-container {
    background: #0f172a;
    border-radius: 12px;
    font-family: 'Fira Code', monospace;
    font-size: 0.85rem;
    color: #f8fafc;
    border: 1px solid #1e293b;
}
.diff-header { background: #1e293b; padding: 12px 20px; color: #94a3b8; font-weight: 700; }

/* Visibility Fix for Streamlit text */
[data-testid="stMarkdownContainer"] p, [data-testid="stCaptionContainer"] {
    color: #1e293b !important;
    font-weight: 500;
}
[data-testid="stExpander"] p { color: #0f172a !important; font-weight: 700; }

#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

# ─── Constants ───────────────────────────────────────────────────────────────
ENV_BASE_URL = "http://localhost:8000"
TASKS = ["single-pass-review", "iterative-negotiation", "escalation-judgment", "custom-review"]

# ─── Helper Functions ─────────────────────────────────────────────────────────
def check_api_connectivity(model_name: str, api_base: str, token: str):
    if not token or len(token) < 5: return False, "Invalid token format."
    try:
        client = OpenAI(base_url=api_base, api_key=token)
        client.models.list()
        return True, "Authorized"
    except Exception as e: return False, f"Error: {str(e)}"

def get_agent_action(obs: dict, model_name: str, api_base: str, token: str) -> dict:
    client = OpenAI(base_url=api_base, api_key=token)
    system_prompt = "You are a senior engineer. Respond ONLY with JSON: {\"decision\": \"...\", \"comment\": \"...\"}"
    history = "\n".join([f"{h['role'].upper()}: {h['content']}" for h in obs.get("review_history", [])])
    prompt = f"Title: {obs.get('pr_title')}\nDiff:\n{obs.get('diff')}\nHistory:\n{history}\nDecision JSON:"
    try:
        resp = client.chat.completions.create(model=model_name, messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": prompt}], max_tokens=500, temperature=0.1)
        raw = resp.choices[0].message.content.strip()
        if "```json" in raw: raw = raw.split("```json")[1].split("```")[0]
        elif "```" in raw: raw = raw.split("```")[1].split("```")[0]
        return json.loads(raw)
    except Exception as e: return {"decision": "request_changes", "comment": f"⚠️ Connection Error: {str(e)}"}

def format_diff_html(diff_text: str):
    lines = diff_text.split("\n")
    filename = "unknown_file"
    for line in lines:
        if line.startswith("+++ b/"): filename = line.replace("+++ b/", "")
    html = [f'<div class="diff-container"><div class="diff-header"><span>{filename}</span></div>']
    for line in lines:
        cls = "diff-line-add" if line.startswith("+") and not line.startswith("+++") else ("diff-line-del" if line.startswith("-") and not line.startswith("---") else "")
        html.append(f'<div class="diff-line {cls}" style="padding:2px 20px; white-space:pre-wrap;">{line}</div>')
    html.append("</div>")
    return "\n".join(html)

# ─── Session State ────────────────────────────────────────────────────────────
def init_state():
    defaults = {
        "initialized": False, "turn": 0, "score": 0.0, "decision": "IDLE",
        "observation": {}, "reward_history": [], "done": False,
        "api_url_override": os.getenv("API_BASE_URL", "https://router.huggingface.co/v1"),
        "hf_token_override": os.getenv("HF_TOKEN", "")
    }
    for key, val in defaults.items():
        if key not in st.session_state: st.session_state[key] = val

init_state()

# ─── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown('<h2 style="color:#0f172a; margin-bottom:0;">🛠️ COMMAND CENTER</h2>', unsafe_allow_html=True)
    
    st.markdown('<div class="section-label">1. Engine Config</div>', unsafe_allow_html=True)
    MODEL_PRESETS = {}
    if os.getenv("gemma4"): MODEL_PRESETS["Gemma 4 (Secure)"] = {"id": "google/gemma-4-31b-it", "url": "https://integrate.api.nvidia.com/v1", "token": os.getenv("gemma4")}
    if os.getenv("nemotron3"): MODEL_PRESETS["Nemotron 3 (Secure)"] = {"id": "nvidia/nemotron-3-super-120b-a12b", "url": "https://integrate.api.nvidia.com/v1", "token": os.getenv("nemotron3")}
    MODEL_PRESETS.update({
        "Qwen 2.5 72B (HF)": {"id": "Qwen/Qwen2.5-72B-Instruct", "url": "https://router.huggingface.co/v1", "token": None},
        "Llama 3.1 70B (Groq)": {"id": "llama3-70b-8192", "url": "https://api.groq.com/openai/v1", "token": None},
        "Custom Engine": {"id": "custom", "url": "", "token": None}
    })
    
    selected_preset = st.selectbox("Intelligence Engine", list(MODEL_PRESETS.keys()), label_visibility="collapsed")
    preset = MODEL_PRESETS[selected_preset]
    model_id = st.text_input("Model ID", value=preset["id"]) if preset["id"] == "custom" else preset["id"]
    
    if preset["token"]: st.session_state.hf_token_override = preset["token"]
    if preset["url"]: st.session_state.api_url_override = preset["url"]

    with st.expander("🔑 Access Settings"):
        is_internal = preset["token"] is not None
        if is_internal:
            st.info("🔒 Internal credentials active.")
            api_url, hf_token = preset["url"], preset["token"]
        else:
            api_url = st.text_input("API URL", value=st.session_state.api_url_override)
            hf_token = st.text_input("API Token", type="password", value=st.session_state.hf_token_override)
            st.session_state.api_url_override, st.session_state.hf_token_override = api_url, hf_token
        
        if st.button("Test Connection", use_container_width=True):
            ok, msg = check_api_connectivity(model_id, api_url, hf_token)
            if ok: st.success(msg)
            else: st.error(msg)

    st.markdown('<div class="section-label">2. Custom Review Config</div>', unsafe_allow_html=True)
    c_title = st.text_input("PR Title", value="Enhancement Request", key="c_title")
    c_desc = st.text_area("PR Description", value="Proposed architectural changes.", key="c_desc")
    
    # File Loader
    files = [os.path.join(r, f).replace("./", "") for r, _, fs in os.walk(".") for f in fs if ".git" not in r and "__pycache__" not in r]
    sel_f = st.selectbox("Load from local file", ["-- Select File --"] + sorted(files))
    loaded = ""
    if sel_f != "-- Select File --":
        try:
            with open(sel_f, "r") as f: loaded = f.read()
        except: pass
    c_diff = st.text_area("Code to Review", value=loaded if loaded else "", height=150, key="c_diff")
    
    if st.button("💾 Apply Custom Config", use_container_width=True):
        try:
            httpx.post(f"{ENV_BASE_URL}/config/custom", json={"diff": c_diff, "pr_title": c_title, "pr_description": c_desc}, timeout=30)
            st.success("Configured! Select 'custom-review' below.")
        except: st.error("Sync failed.")

    st.markdown('<div class="section-label">3. Scenario & Launch</div>', unsafe_allow_html=True)
    task_name = st.selectbox("Scenario", TASKS, label_visibility="collapsed")
    
    if st.button("🚀 START ENVIRONMENT", use_container_width=True, type="primary"):
        try:
            r = httpx.post(f"{ENV_BASE_URL}/reset", json={"task_name": task_name}, timeout=30)
            st.session_state.update({"initialized": True, "turn": 1, "score": 0.0, "decision": "RUNNING", "observation": r.json(), "reward_history": [], "done": False})
            st.rerun()
        except: st.error("Engine Offline.")

# ─── Main View ────────────────────────────────────────────────────────────────
if not st.session_state.initialized:
    st.markdown('<div style="text-align:center; padding-top:10rem;"><h1 style="color:#0f172a; font-size:3rem; font-weight:800;">Review Command Center</h1><p style="color:#475569; font-size:1.2rem;">Select and initialize a scenario from the sidebar to begin.</p></div>', unsafe_allow_html=True)
    st.stop()

# Header
h1, h2 = st.columns([3, 1])
obs = st.session_state.observation
with h1:
    st.markdown(f'<p style="color:#475569; font-size:0.8rem; font-weight:700; margin:0;">SCENARIO: {task_name.upper()}</p><h2 style="color:#0f172a; font-weight:800;">{obs.get("pr_title")}</h2>', unsafe_allow_html=True)
with h2:
    d = st.session_state.decision
    b = {"APPROVE":"badge-approve", "REQUEST_CHANGES":"badge-request", "ESCALATE":"badge-escalate"}.get(d, "badge-running")
    st.markdown(f'<div style="text-align:right; margin-top:1.5rem;"><span class="badge {b}">{d}</span></div>', unsafe_allow_html=True)

st.divider()

# Metrics
m1, m2, m3, m4 = st.columns(4)
for col, label, val, sub in zip([m1, m2, m3, m4], ["REWARD", "TURN", "STATUS", "ENGINE"], [f"{st.session_state.score:.2f}", f"{st.session_state.turn}/3", "ENGAGED" if not st.session_state.done else "FINISHED", model_id[:15]], ["Cumulative", "Progress", "Episode", "Current AI"]):
    with col: st.markdown(f'<div class="metric-card"><div style="color:#64748b; font-size:0.75rem; font-weight:800;">{label}</div><div style="font-size:1.8rem; font-weight:800; color:#0f172a;">{val}</div><div style="color:#94a3b8; font-size:0.65rem;">{sub}</div></div>', unsafe_allow_html=True)

st.write("")
t_diff, t_nego = st.tabs(["📄 Code View", "💬 Timeline"])

with t_diff: st.markdown(format_diff_html(obs.get("diff", "")), unsafe_allow_html=True)

with t_nego:
    for item in obs.get("review_history", []):
        is_rev = item["role"] == "reviewer"
        cls, lbl = ("bubble-reviewer", "REVIEWER COMMAND") if is_rev else ("bubble-author", "AUTHOR RESPONSE")
        st.markdown(f'<div class="bubble {cls}"><div class="bubble-header">{lbl}</div>{item["content"]}</div>', unsafe_allow_html=True)

    if not st.session_state.done:
        if st.button("▶ EXECUTE NEXT ROUND", use_container_width=True, type="primary"):
            with st.spinner("AI Engine Processing..."):
                action = get_agent_action(obs, model_id, st.session_state.api_url_override, st.session_state.hf_token_override)
                try:
                    r = httpx.post(f"{ENV_BASE_URL}/step", json={"action": action}, timeout=30).json()
                    st.session_state.update({"observation":r["observation"], "score":st.session_state.score+r["reward"], "reward_history":st.session_state.reward_history+[r["reward"]], "done":r["done"], "decision":action["decision"].upper()})
                    if not st.session_state.done: st.session_state.turn += 1
                    st.rerun()
                except: st.error("Processing failed.")