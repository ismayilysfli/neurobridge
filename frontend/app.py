import json
import os
import glob
import requests
import pandas as pd
import streamlit as st

# Direct import of core agent explorer and test harness
try:
    from agent.explorer import AIExplorer
    from agent.replay import ReplayEngine
except ImportError:
    AIExplorer = None
    ReplayEngine = None

st.set_page_config(
    page_title="NeuroBridge: AI Game Economy Exploit Tester",
    page_icon="🎮",
    layout="wide"
)

# --- CSS STYLING ---
st.markdown("""
    <style>
    .metric-card {
        background-color: #1e293b;
        border: 1px solid #334155;
        border-radius: 10px;
        padding: 16px;
        text-align: center;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
    }
    .metric-value {
        font-size: 26px;
        font-weight: bold;
        color: #38bdf8;
    }
    .metric-label {
        font-size: 13px;
        color: #94a3b8;
        margin-top: 4px;
    }
    .badge-success {
        background-color: #065f46;
        color: #34d399;
        padding: 4px 12px;
        border-radius: 12px;
        font-weight: bold;
    }
    .badge-danger {
        background-color: #881337;
        color: #f87171;
        padding: 4px 12px;
        border-radius: 12px;
        font-weight: bold;
    }
    </style>
""", unsafe_allow_html=True)

st.title("🎮 NeuroBridge: AI-Powered Game Economy Exploit Tester")

tab1, tab2, tab3 = st.tabs([
    "🚀 Live Discovery & Replay", 
    "📊 Observability & Analytics", 
    "📜 System Spec & Invariants"
])

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

# ==========================================
# TAB 1: REAL BACKEND SESSIONS & EXPLORATION
# ==========================================
with tab1:
    st.header("Exploit Discovery Execution")
    st.caption("Interact directly with live backend sessions (/api/sessions) or trigger direct AI exploration.")
    
    mode = st.radio("Execution Mode", ["Live Session API Interaction", "Direct AI Exploration Agent"], horizontal=True)
    
    if mode == "Live Session API Interaction":
        col1, col2 = st.columns(2)
        with col1:
            scenario = st.selectbox("Scenario Variant", ["reward_reset", "upgrade_resale", "secure"])
            if st.button("Create New Session"):
                try:
                    res = requests.post(f"{BACKEND_URL}/api/sessions", json={"scenario": scenario}, timeout=10)
                    if res.status_code in [200, 201]:
                        data = res.json()
                        st.session_state["session_id"] = data.get("session_id") or data.get("id")
                        st.session_state["session_state"] = data
                        st.success(f"Session Created: {st.session_state['session_id']}")
                    else:
                        st.error(f"Failed to create session: {res.status_code} - {res.text}")
                except Exception as e:
                    st.error(f"Backend API offline: {e}")
                    
        with col2:
            if "session_id" in st.session_state:
                st.subheader(f"Session: {st.session_state['session_id']}")
                action_type = st.selectbox("Execute Action", ["claim_reward", "buy_item", "upgrade_item", "sell_item", "reset_profile"])
                if st.button("Send Action"):
                    sess_id = st.session_state["session_id"]
                    try:
                        res = requests.post(
                            f"{BACKEND_URL}/api/sessions/{sess_id}/actions", 
                            json={"action": action_type}, 
                            timeout=10
                        )
                        if res.status_code == 200:
                            st.session_state["session_state"] = res.json()
                            st.success("Action Executed!")
                        else:
                            st.error(f"Action Failed: {res.status_code} - {res.text}")
                    except Exception as e:
                        st.error(f"API Error: {e}")
                        
        if "session_state" in st.session_state:
            st.write("---")
            st.subheader("Current State")
            st.json(st.session_state["session_state"])

    else:
        # Direct AI Explorer Execution
        col_sel, col_btn = st.columns([3, 1])
        with col_sel:
            agent_scenario = st.selectbox("Select Scenario for AI Agent", ["reward_reset", "upgrade_resale", "secure"], key="agent_sc")
        with col_btn:
            st.write("")
            st.write("")
            run_agent = st.button("🚀 Run AI Explorer", use_container_width=True)
            
        if run_agent:
            if AIExplorer is not None:
                with st.spinner("AI Explorer actively finding exploits..."):
                    try:
                        explorer = AIExplorer(scenario=agent_scenario, backend_url=BACKEND_URL)
                        results = explorer.run()
                        
                        st.success("Exploration Finished!")
                        
                        # Real Metrics
                        c1, c2, c3 = st.columns(3)
                        with c1:
                            st.markdown(f'<div class="metric-card"><div class="metric-value">{len(results.get("history", []))}</div><div class="metric-label">Steps Taken</div></div>', unsafe_allow_html=True)
                        with c2:
                            violation = results.get("violation_found", False)
                            status_html = '<span class="badge-danger">VIOLATION</span>' if violation else '<span class="badge-success">SECURE</span>'
                            st.markdown(f'<div class="metric-card"><div class="metric-value">{status_html}</div><div class="metric-label">Result</div></div>', unsafe_allow_html=True)
                        with c3:
                            st.markdown(f'<div class="metric-card"><div class="metric-value">{results.get("violation_type", "None")}</div><div class="metric-label">Triggered Rule</div></div>', unsafe_allow_html=True)
                            
                        if results.get("history"):
                            st.subheader("Action History Replay")
                            df_hist = pd.DataFrame(results["history"])
                            st.dataframe(df_hist, use_container_width=True)
                    except Exception as e:
                        st.error(f"Explorer execution error: {e}")
            else:
                st.error("Agent package not imported. Verify `agent/explorer.py` exists.")

# ==========================================
# TAB 2: DYNAMIC OBSERVABILITY FROM REAL LOGS
# ==========================================
with tab2:
    st.header("Observability & Benchmark Telemetry")
    st.caption("Metrics dynamically calculated directly from saved evaluation files in `reports/`.")
    
    report_files = glob.glob("reports/evaluation_*.json")
    
    if report_files:
        parsed_reports = []
        for rf in report_files:
            try:
                with open(rf, "r") as f:
                    content = json.load(f)
                    content["_file"] = os.path.basename(rf)
                    parsed_reports.append(content)
            except Exception:
                pass
                
        if parsed_reports:
            # Dynamically compute metrics from actual files
            total_runs = len(parsed_reports)
            violations_found = sum(1 for r in parsed_reports if r.get("metrics", {}).get("violations_found", 0) > 0 or r.get("violation_found"))
            discovery_rate = (violations_found / total_runs * 100) if total_runs > 0 else 0.0
            
            # Dynamic Summary Metrics
            m1, m2, m3, m4 = st.columns(4)
            with m1:
                st.markdown(f'<div class="metric-card"><div class="metric-value">{total_runs}</div><div class="metric-label">Total Evaluated Runs</div></div>', unsafe_allow_html=True)
            with m2:
                st.markdown(f'<div class="metric-card"><div class="metric-value">{violations_found}</div><div class="metric-label">Exploits Discovered</div></div>', unsafe_allow_html=True)
            with m3:
                st.markdown(f'<div class="metric-card"><div class="metric-value">{discovery_rate:.1f}%</div><div class="metric-label">Calculated Discovery Rate</div></div>', unsafe_allow_html=True)
            with m4:
                st.markdown(f'<div class="metric-card"><div class="metric-value">{len(report_files)}</div><div class="metric-label">Report Log Files</div></div>', unsafe_allow_html=True)
                
            st.write("")
            st.divider()
            
            # Formatted Data Table of Real Evaluation Files
            st.subheader("Evaluated Report Logs")
            table_rows = []
            for r in parsed_reports:
                metrics = r.get("metrics", {})
                table_rows.append({
                    "Report File": r.get("_file"),
                    "Evaluation ID": r.get("evaluation_id", "N/A"),
                    "Total Steps": r.get("total_steps") or metrics.get("total_steps") or len(r.get("history", [])),
                    "Violation Discovered": "YES" if (r.get("violation_found") or metrics.get("violations_found", 0) > 0) else "NO",
                    "Rule Triggered": r.get("violation_type") or r.get("rule_violated") or "None"
                })
            
            df_reports = pd.DataFrame(table_rows)
            st.dataframe(df_reports, use_container_width=True)
            
            # Dynamic Steps Chart
            st.subheader("Execution Steps per Evaluation Run")
            chart_df = df_reports.set_index("Report File")[["Total Steps"]]
            st.bar_chart(chart_df)
    else:
        st.warning("No evaluation logs found in `reports/`. Run your test campaigns to generate dynamic reports.")

# ==========================================
# TAB 3: SYSTEM SPECIFICATIONS & INVARIANTS
# ==========================================
with tab3:
    st.header("Formal Invariant Specifications")
    st.markdown("""
    ### Enforced System Rules
    * **Rule R1 (Reward Uniqueness):** Welcome reward must be claimed strictly once per account. Profile title resets or state re-initializations must never reset reward eligibility.
    * **Rule R2 (Non-Profitable Resale):** Item buy (`BUY_PRICE = 40`), upgrade (`UPGRADE_PRICE = 10`), and sell loops must enforce non-positive net yield ($\le 0$).
    
    ### System Economy Parameters
    * **`START_COINS`**: `100`
    * **`BUY_PRICE`**: `40`
    * **`UPGRADE_PRICE`**: `10`
    * **`SELL_PRICE`**: `20`
    """)