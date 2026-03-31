"""
QA/QC status dashboard.

Usage:
    streamlit run workspace/execution/pages/qaqc_status.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

WORKSPACE_ROOT = Path(__file__).resolve().parents[2]
if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT))

from path_contract import resolve_project_dir

try:
    import streamlit as st
except ImportError:
    print("streamlit is not installed. Run: pip install streamlit")
    sys.exit(1)

st.set_page_config(page_title="QA/QC Status", page_icon="✅", layout="wide")
st.title("QA/QC Status Dashboard")
st.caption("Unified test, AST, security, and infrastructure status")


def load_latest_result() -> dict | None:
    result_path = resolve_project_dir("knowledge-dashboard", required_paths=("public",)) / "public" / "qaqc_result.json"
    if not result_path.exists():
        return None
    try:
        return json.loads(result_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def load_history() -> list[dict]:
    try:
        from execution.qaqc_history_db import QaQcHistoryDB

        db = QaQcHistoryDB()
        return db.get_trend_data(days=30)
    except Exception:
        return []


result = load_latest_result()
history = load_history()

if result is None:
    st.warning("No QA/QC result found yet. Run `python workspace/execution/qaqc_runner.py` first.")
    st.stop()

verdict = result.get("verdict", "UNKNOWN")
verdict_style = {
    "APPROVED": st.success,
    "CONDITIONALLY_APPROVED": st.warning,
    "REJECTED": st.error,
}.get(verdict, st.info)
verdict_style(f"Final verdict: {verdict}")

col_time, col_duration, col_total = st.columns(3)
with col_time:
    timestamp = result.get("timestamp", "")
    st.metric("Timestamp", timestamp[:19].replace("T", " ") if timestamp else "-")
with col_duration:
    st.metric("Elapsed", f"{result.get('elapsed_sec', 0)}s")
with col_total:
    totals = result.get("total", {})
    st.metric("Passed", totals.get("passed", 0))

st.divider()
st.subheader("Project Results")

projects = result.get("projects", {})
project_columns = st.columns(len(projects) if projects else 1)
for index, (name, data) in enumerate(projects.items()):
    with project_columns[index]:
        st.markdown(f"**{name}**")
        st.metric("Status", data.get("status", "-"))
        st.metric("Passed", data.get("passed", 0))
        st.metric("Failed", data.get("failed", 0))
        st.metric("Skipped", data.get("skipped", 0))

st.divider()
col_ast, col_security = st.columns(2)

with col_ast:
    st.subheader("AST Check")
    ast_data = result.get("ast_check", {})
    st.metric("Healthy Modules", f"{ast_data.get('ok', 0)}/{ast_data.get('total', 0)}")
    for failure in ast_data.get("failures", []):
        st.error(f"{failure['file']}: {failure['error']}")

with col_security:
    st.subheader("Security Scan")
    security_data = result.get("security_scan", {})
    st.metric("Status", security_data.get("status", "-"))
    detail = security_data.get("status_detail")
    if detail:
        st.caption(detail)
    for issue in security_data.get("issues", []):
        st.warning(f"{issue['file']}: {issue['pattern']}")

infra = result.get("infrastructure", {})
if infra:
    st.divider()
    st.subheader("Infrastructure")
    infra_columns = st.columns(4)
    infra_columns[0].metric("Docker", "Up" if infra.get("docker") else "Down")
    infra_columns[1].metric("Ollama", "Up" if infra.get("ollama") else "Down")
    scheduler = infra.get("scheduler", {})
    infra_columns[2].metric("Scheduler", f"{scheduler.get('ready', 0)}/{scheduler.get('total', 0)} Ready")
    infra_columns[3].metric("Disk Free", f"{infra.get('disk_gb_free', '?')} GB")

if history:
    st.divider()
    st.subheader("30 Day Trend")
    import pandas as pd

    frame = pd.DataFrame(history)
    if not frame.empty:
        st.line_chart(frame.set_index("date")[["passed", "failed"]])

totals = result.get("total", {})
st.divider()
st.caption(
    f"Totals: {totals.get('passed', 0)} passed, {totals.get('failed', 0)} failed, "
    f"{totals.get('errors', 0)} errors, {totals.get('skipped', 0)} skipped"
)
