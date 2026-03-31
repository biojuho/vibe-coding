import json
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import streamlit as st

try:
    from execution.daily_report import REPORT_DIR, generate_report

    _MODULE_OK = True
except ImportError as e:
    _MODULE_OK = False
    _MODULE_ERR = str(e)

st.set_page_config(page_title="Daily Report - Joolife", page_icon="📝", layout="wide")

if not _MODULE_OK:
    st.error(f"Daily Report 모듈을 불러올 수 없습니다: {_MODULE_ERR}")
    st.stop()

st.title("📝 Daily Report")
st.caption("Daily activity summary & insights")

# ── Date Picker ──
col_date, col_btn = st.columns([2, 1])
with col_date:
    target = st.date_input("Select Date", value=date.today())
with col_btn:
    st.markdown("")
    st.markdown("")
    generate_btn = st.button("Generate Report", type="primary")

# 기존 리포트 로드 또는 새로 생성
report_path = REPORT_DIR / f"daily_{target.isoformat()}.json"
report = None

if generate_btn:
    with st.spinner("Collecting activity data..."):
        report = generate_report(target)
    st.success("Report generated!")
elif report_path.exists():
    report = json.loads(report_path.read_text(encoding="utf-8"))

if report is None:
    st.info("No report for this date. Click 'Generate Report' to create one.")
    st.stop()

# ── Summary Metrics ──
st.divider()
s = report["summary"]
col1, col2, col3, col4, col5, col6, col7 = st.columns(7)
with col1:
    st.metric("Total Commits", s["total_commits"])
with col2:
    st.metric("Active Repos", s["active_repos"])
with col3:
    st.metric("Files Modified", s["files_modified"])
with col4:
    st.metric("Scheduled Tasks Run", s["scheduler_tasks_run"])
with col5:
    st.metric("LLM Bridge Calls", s.get("llm_bridge_calls", 0))
with col6:
    st.metric("Bridge Repairs", s.get("llm_bridge_repairs", 0))
with col7:
    st.metric("Bridge Fallbacks", s.get("llm_bridge_fallbacks", 0))

# ── Git Activity ──
st.divider()
st.subheader("Git Activity")

by_repo = report["git_activity"].get("by_repo", {})
if by_repo:
    import plotly.express as px

    fig = px.bar(
        x=list(by_repo.keys()),
        y=list(by_repo.values()),
        labels={"x": "Repository", "y": "Commits"},
        title="Commits by Repository",
    )
    fig.update_layout(
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font_color="#e0e0e0",
    )
    st.plotly_chart(fig, width="stretch")

commits = report["git_activity"].get("commits", [])
if commits:
    st.markdown("**Recent Commits:**")
    for c in commits[:20]:
        st.markdown(f"- `{c['repo']}` **{c['hash']}** {c['message']}")
else:
    st.info("No commits found for this date.")

# ── Scheduler Logs ──
sched_logs = report.get("scheduler_logs", [])
if sched_logs:
    st.divider()
    st.subheader("Scheduler Activity")
    for log in sched_logs:
        icon = "✅" if log.get("exit_code") == 0 else "❌"
        st.markdown(f"{icon} **{log['task_name']}** — {log['started_at']}")

bridge = report.get("llm_bridge", {})
if bridge.get("total_calls", 0):
    st.divider()
    st.subheader("LLM Bridge")
    bridge_col1, bridge_col2, bridge_col3, bridge_col4 = st.columns(4)
    with bridge_col1:
        st.metric("Shadow Calls", bridge.get("shadow_calls", 0))
    with bridge_col2:
        st.metric("Enforce Calls", bridge.get("enforce_calls", 0))
    with bridge_col3:
        st.metric("Avg Language Score", bridge.get("average_language_score") or 0)
    with bridge_col4:
        st.metric("Providers", len(bridge.get("by_provider", {})))

    reason_codes = bridge.get("top_reason_codes", [])
    if reason_codes:
        st.markdown("**Top Reason Codes:**")
        for item in reason_codes[:10]:
            st.markdown(f"- `{item['reason_code']}` {item['count']}회")
