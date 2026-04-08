"""
PR Review Command Center — Final Studio Grade Revision
Theme: Ultra-Clean, High-Contrast & Secure
"""

import streamlit as st
import json
import os
import httpx
from openai import OpenAI

# ─── Page Config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="PR Command Center",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── Professional CSS Core ────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800&family=Fira+Code:wght@400;500&display=swap');

.stApp { background-color: #f8fafc; font-family: 'Inter', sans-serif; }

/* Sidebar: Professional Deep Blue */
[data-testid="stSidebar"] {
    background-color: #ffffff !important;
    border-right: 1px solid #e2e8f0;
}

/* Deep High Contrast Text */
h1, h2, h3, p, span, label { color: #0f172a !important; }
.section-label {
    font-size: 0.75rem; font-weight: 800; color: #1e293b !important;
    text-transform: uppercase; letter-spacing: 0.05rem;
    margin-top: 2rem; border-bottom: 2px solid #f1f5f9; padding-bottom: 4px;
}

/* Glass Metric Cards */
.metric-card {
    background: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 12px;
    padding: 1.5rem;
    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
}

/* Badge System */
.badge { padding: 6px 14px; border-radius: 20px; font-size: 0.85rem; font-weight: 800; border: 1px solid transparent; }
.badge-approve  { background: #dcfce7; color: #166534 !important; border-color: #bbf7d0; }
.badge-request  { background: #fee2e2; color: #991b1b !important; border-color: #fecaca; }
.badge-escalate { background: #fef9c3; color: #854d0e !important; border-color: #fef08a; }
.badge-running  { background: #dbeafe; color: #1e40af !important; border-color: #bfdbfe; }

/* Timeline Bubbles */
.bubble { padding: 1.5rem; border-radius: 12px; font-size: 0.95rem; line-height: 1.6; margin-bottom: 1.5rem; border: 1px solid #e2e8f0; }
.bubble-reviewer { background: #ffffff; border-left: 6px solid #3b82f6; }
.bubble-author { background: #f1f5f9; border-right: 6px solid #94a3b8; }
.bubble-header { font-size: 0.75rem; font-weight: 800; margin-bottom: 0.75rem; color: #334155; display: flex; align-items: center; gap: 8px; }

/* Clearer Buttons */
button[kind="primary"] { background-color: #0f172a !important; color: white !important; font-weight: 700 !important; }
button[kind="secondary"] { background-color: #ffffff !important; border: 1px solid #d0d7de !important; }

/* Diff Container */
.diff-container { background: #0f172a; border-radius: 12px; font-family: 'Fira Code', monospace; color: #f8fafc; border: 1px solid #1e293b; }
.diff-header { background: #1e293b; padding: 12px 20px; font-weight: 700; border-bottom: 1px solid #334155; }

/* Visibility Fix for Inputs */
.stTextInput input, .stTextArea textarea, .stSelectbox select {
    background-color: #ffffff !important;
    color: #0f172a !important;
    border: 1px solid #cbd5e1 !important;
}
</style>
""", unsafe_allow_html=True)

# ─── Constants ───────────────────────────────────────────────────────────────
ENV_BASE_URL = "http://localhost:8000"
TASKS = ["single-pass-review", "iterative-negotiation", "escalation-judgment", "custom-review"]

# ─── Helper Functions ─────────────────────────────────────────────────────────
def get_agent_action(obs, model_id, url, token):
    try:
        client = OpenAI(base_url=url, api_key=token)
        sys_p = "Senior Engineer. Respond ONLY JSON: {\"decision\":\"approve|request_changes|escalate\", \"comment\":\"...\"}"
        hist = "\n".join([f"{h['role'].upper()}: {h['content']}" for h in obs.get("review_history", [])])
        prompt = f"PR: {obs.get('pr_title')}\nDiff:\n{obs.get('diff')}\nHistory:\n{hist}\nDecision JSON:"
        
        resp = client.chat.completions.create(model=model_id, messages=[{"role":"system","content":sys_p},{"role":"user","content":prompt}], temperature=0.1)
        raw = resp.choices[0].message.content.strip()
        if "```json" in raw: raw = raw.split("```json")[1].split("```")[0]
        elif "```" in raw: raw = raw.split("```")[1].split("```")[0]
        return json.loads(raw)
    except Exception as e:
        return {"decision": "error", "comment": f"⚠️ CONNECTION ERROR: {str(e)}"}

def format_diff_html(diff_text):
    lines = diff_text.split("\n")
    filename = "unknown_file"
    for line in lines:
        if line.startswith("+++ b/"): filename = line.replace("+++ b/", "")
    html = [f'<div class="diff-container"><div class="diff-header">{filename}</div>']
    for line in lines:
        cls = "background:rgba(16,185,129,0.1); border-left:4px solid #10b981;" if line.startswith("+") and not line.startswith("+++") else ("background:rgba(239,68,68,0.1); border-left:4px solid #ef4444;" if line.startswith("-") and not line.startswith("---") else "border-left:4px solid transparent;")
        html.append(f'<div style="{cls} padding:2px 20px; white-space:pre-wrap;">{line}</div>')
    html.append("</div>")
    return "\n".join(html)

# ─── Session State ────────────────────────────────────────────────────────────
if "initialized" not in st.session_state:
    st.session_state.update({
        "initialized": False, "turn": 0, "score": 0.0, "decision": "IDLE",
        "observation": {}, "done": False, "reward_history": [],
        "api_url": os.getenv("API_BASE_URL", "https://router.huggingface.co/v1"),
        "api_token": os.getenv("HF_TOKEN", "")
    })

# ─── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### 🔍 PR Command Center")
    
    st.markdown('<div class="section-label">1. Engine Selection</div>', unsafe_allow_html=True)
    PRESETS = {}
    if os.getenv("gemma4"): PRESETS["Gemma 4 IT (Secure Internal)"] = {"id":"google/gemma-4-31b-it", "url":"https://integrate.api.nvidia.com/v1", "token":os.getenv("gemma4")}
    if os.getenv("nemotron3"): PRESETS["Nemotron 3 (Secure Internal)"] = {"id":"nvidia/nemotron-3-super-120b-a12b", "url":"https://integrate.api.nvidia.com/v1", "token":os.getenv("nemotron3")}
    PRESETS.update({
        "Qwen 2.5 72B (Hugging Face)": {"id":"Qwen/Qwen2.5-72B-Instruct", "url":"https://router.huggingface.co/v1", "token":None},
        "Llama 3 70B (Groq)": {"id":"llama3-70b-8192", "url":"https://api.groq.com/openai/v1", "token":None},
        "Custom Endpoint": {"id":"custom", "url":"", "token":None}
    })
    
    selected_p = st.selectbox("Intelligence Engine", list(PRESETS.keys()), label_visibility="collapsed")
    conf = PRESETS[selected_p]
    
    m_id = st.text_input("Model ID", value=conf["id"]) if conf["id"] == "custom" else conf["id"]
    
    with st.expander("🔑 Credentials", expanded=(conf["token"] is None)):
        if conf["token"]:
            st.info("🔒 Secure Internal Key Active")
            t_url, t_key = conf["url"], conf["token"]
        else:
            t_url = st.text_input("API URL", value=st.session_state.api_url)
            t_key = st.text_input("API Key", type="password", value=st.session_state.api_token)
            st.session_state.update({"api_url":t_url, "api_token":t_key})

    st.markdown('<div class="section-label">2. Task Configuration</div>', unsafe_allow_html=True)
    c_title = st.text_input("Scenario Title", value="Feature Implementation")
    c_desc = st.text_area("Context", value="Refactoring the user service.")
    
    # Simple File Picker
    all_files = [os.path.join(r, f).replace("./", "") for r, _, fs in os.walk(".") for f in fs if ".git" not in r and "__pycache__" not in r]
    sel_f = st.selectbox("Load Code From File", ["-- Select File --"] + sorted(all_files))
    loaded_c = ""
    if sel_f != "-- Select File --":
        with open(sel_f, "r") as f: loaded_c = f.read()
    c_diff = st.text_area("Diff Content", value=loaded_c, height=120)

    if st.button("Apply Custom Context", use_container_width=True):
        try:
            httpx.post(f"{ENV_BASE_URL}/config/custom", json={"diff":c_diff, "pr_title":c_title, "pr_description":c_desc}, timeout=30)
            st.success("Custom Context Applied.")
        except: st.error("Sync Error.")

    st.divider()
    scen = st.selectbox("Select Scenario", TASKS)
    if st.button("🚀 INITIALIZE ENVIRONMENT", use_container_width=True, type="primary"):
        try:
            r = httpx.post(f"{ENV_BASE_URL}/reset", json={"task_name": scen}, timeout=30).json()
            st.session_state.update({"initialized":True, "turn":1, "score":0.0, "decision":"IDLE", "observation":r, "reward_history":[], "done":False})
            st.rerun()
        except: st.error("Engine Connection Failed.")

# ─── Main View ────────────────────────────────────────────────────────────────
if not st.session_state.initialized:
    st.markdown('<div style="text-align:center; padding-top:10rem;"><h1>PR Review Negotiation Arena</h1><p>Configure Engine & Task in the sidebar to start.</p></div>', unsafe_allow_html=True)
    st.stop()

# Header
obs = st.session_state.observation
h1, h2 = st.columns([4, 1])
with h1: st.markdown(f"### {obs.get('pr_title')}")
with h2:
    d = st.session_state.decision
    badge = {"APPROVE":"badge-approve", "REQUEST_CHANGES":"badge-request", "ESCALATE":"badge-escalate"}.get(d, "badge-running")
    st.markdown(f'<div style="text-align:right;"><span class="badge {badge}">{d}</span></div>', unsafe_allow_html=True)

st.write("")
m1, m2, m3 = st.columns(3)
with m1: st.markdown(f'<div class="metric-card"><div style="font-weight:800; font-size:0.7rem; color:#64748b;">TOTAL REWARD</div><div style="font-size:1.8rem; font-weight:800;">{st.session_state.score:.2f}</div></div>', unsafe_allow_html=True)
with m2: st.markdown(f'<div class="metric-card"><div style="font-weight:800; font-size:0.7rem; color:#64748b;">TURN</div><div style="font-size:1.8rem; font-weight:800;">{st.session_state.turn} / 3</div></div>', unsafe_allow_html=True)
with m3: st.markdown(f'<div class="metric-card"><div style="font-weight:800; font-size:0.7rem; color:#64748b;">ENGINE</div><div style="font-size:1.2rem; font-weight:700; color:#3b82f6;">{m_id[:20]}...</div></div>', unsafe_allow_html=True)

st.write("")
t1, t2 = st.tabs(["📄 Code", "💬 Negotiation"])

with t1: st.markdown(format_diff_html(obs.get("diff", "")), unsafe_allow_html=True)

with t2:
    for item in obs.get("review_history", []):
        r = item["role"] == "reviewer"
        cl, h = ("bubble-reviewer", "🤖 AI REVIEWER") if r else ("bubble-author", "👨‍💻 AUTHOR")
        st.markdown(f'<div class="bubble {cl}"><div class="bubble-header">{h}</div>{item["content"]}</div>', unsafe_allow_html=True)
    
    if not st.session_state.done:
        if st.button("▶ EXECUTE NEXT ROUND", use_container_width=True, type="primary"):
            with st.spinner("AI analyzing code..."):
                action = get_agent_action(obs, m_id, t_url, t_key)
                if action["decision"] == "error":
                    st.error(action["comment"])
                else:
                    try:
                        r = httpx.post(f"{ENV_BASE_URL}/step", json={"action": action}, timeout=30).json()
                        st.session_state.update({"observation":r["observation"], "score":st.session_state.score+r["reward"], "reward_history":st.session_state.reward_history+[r["reward"]], "done":r["done"], "decision":action["decision"].upper()})
                        if not st.session_state.done: st.session_state.turn += 1
                        st.rerun()
                    except: st.error("Backend Step Failed.")