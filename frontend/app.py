import streamlit as st
import requests

# Page configuration
st.set_page_config(
    page_title="SupplyChain.AI | Enterprise Intelligence Platform",
    page_icon="🌐",
    layout="wide"
)

# --- Enterprise Custom CSS Styling ---
st.markdown("""
<style>
    /* Main Background & Font Color */
    .main {
        background-color: #f8fafc;
        color: #0f172a;
    }
    
    /* Professional Header Banner */
    .enterprise-header {
        background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
        padding: 28px 32px;
        border-radius: 10px;
        color: white;
        margin-bottom: 24px;
        border-left: 5px solid #0d9488;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
    }
    .enterprise-header h1 {
        margin: 0;
        font-size: 26px;
        font-weight: 700;
        letter-spacing: -0.5px;
    }
    .enterprise-header p {
        margin: 6px 0 0 0;
        font-size: 14px;
        color: #94a3b8;
    }

    /* Sidebar Professional Theme */
    section[data-testid="stSidebar"] {
        background-color: #0f172a;
        color: #f8fafc;
        border-right: 1px solid #1e293b;
    }
    section[data-testid="stSidebar"] .stMarkdown h3, 
    section[data-testid="stSidebar"] .stMarkdown h2 {
        color: #f8fafc;
        font-size: 15px;
        font-weight: 600;
        letter-spacing: 0.5px;
        text-transform: uppercase;
    }

    /* Chat Message Cards */
    .stChatMessage {
        background-color: #ffffff;
        border-radius: 8px;
        padding: 16px;
        margin-bottom: 12px;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04);
        border: 1px solid #e2e8f0;
    }

    /* Quick Prompt Buttons */
    .stButton button {
        width: 100%;
        background-color: #1e293b;
        color: #ffffff;
        border: 1px solid #334155;
        border-radius: 6px;
        font-size: 13px;
        font-weight: 500;
        transition: all 0.2s ease;
    }
    .stButton button:hover {
        background-color: #0d9488;
        border-color: #0d9488;
        color: #ffffff;
    }

    /* Expander Styling for Trace */
    .streamlit-expanderHeader {
        background-color: #f1f5f9;
        border-radius: 6px;
        font-size: 13px;
        font-weight: 600;
        color: #334155;
    }
</style>
""", unsafe_allow_html=True)

# --- Header Banner ---
st.markdown("""
<div class="enterprise-header">
    <h1>🌐 Enterprise Supply Chain Control Tower</h1>
    <p>Autonomous Multi-Agent Intelligence Platform &bull; Powered by Qwen2.5:7b, LangGraph Supervisor & SQLite</p>
</div>
""", unsafe_allow_html=True)

API_URL = "http://127.0.0.1:8000/api/v1/query"
HEALTH_URL = "http://127.0.0.1:8000/"

# --- Sidebar Configuration ---
with st.sidebar:
    st.markdown("### System Telemetry")
    try:
        health_res = requests.get(HEALTH_URL, timeout=3)
        if health_res.status_code == 200:
            st.markdown("🟢 **Backend Status:** `Operational`")
            health_data = health_res.json()
            st.markdown(f"🤖 **Active Model:** `{health_data.get('model', 'Unknown')}`")
            st.markdown("🗄️ **Schema:** `7-Table Normalized Enterprise`")
        else:
            st.markdown("🔴 **Backend Status:** `Degraded`")
    except Exception:
        st.markdown("⚠️ **Backend Status:** `Offline`")
        st.caption("Start FastAPI server via terminal:\n`.venv/bin/python -m src.api.server`")
        
    st.divider()
    st.markdown("### Quick Diagnostic Queries")
    
    if st.button("Lowest Price for SKU123"):
        st.session_state["preset_prompt"] = "Which supplier offers SKU123 at the lowest unit price, and what warehouse is it stored in?"
    if st.button("Beta Logistics Risk Audit"):
        st.session_state["preset_prompt"] = "Can you analyze the operational risk and delivery delay metrics for Beta Logistics?"
    if st.button("Total Stock Across Hubs"):
        st.session_state["preset_prompt"] = "What is the total stock quantity of SKU123 across all warehouses?"

# --- Chat Session State ---
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display chat history
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        if "trace" in message and message["trace"]:
            with st.expander("🔍 Agent Routing & Execution Trace"):
                for step in message["trace"]:
                    st.markdown(f"- {step}")
        st.markdown(message["content"])

# Handle preset prompt from sidebar buttons or chat input
prompt = st.chat_input("Enter query regarding inventory, suppliers, warehouses, or vendor risk...")

if "preset_prompt" in st.session_state and st.session_state["preset_prompt"]:
    prompt = st.session_state["preset_prompt"]
    st.session_state["preset_prompt"] = None # Reset after reading

if prompt:
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Supervisor routing to specialist agents..."):
            try:
                response = requests.post(API_URL, json={"prompt": prompt}, timeout=60)
                if response.status_code == 200:
                    data = response.json()
                    answer = data.get("response", "No response generated.")
                    trace = data.get("trace", [])
                    
                    if trace:
                        with st.expander("🔍 Agent Routing & Execution Trace", expanded=False):
                            for step in trace:
                                st.markdown(f"- {step}")
                                
                    st.markdown(answer)
                    st.session_state.messages.append({
                        "role": "assistant", 
                        "content": answer, 
                        "trace": trace
                    })
                else:
                    error_detail = response.json().get("detail", response.text)
                    st.error(f"API Error: {error_detail}")
            except requests.exceptions.ConnectionError:
                st.error("Connection failed. Please ensure the FastAPI backend is running.")
            except Exception as e:
                st.error(f"An unexpected error occurred: {str(e)}")