"""
VibeDebt Dashboard - Technical debt monitoring and trend tracking.

Usage:
    streamlit run workspace/execution/pages/debt_dashboard.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

WORKSPACE_ROOT = Path(__file__).resolve().parents[2]
if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT))

from path_contract import TMP_ROOT

try:
    import streamlit as st
except ImportError:
    print("streamlit is not installed. Run: pip install streamlit")
    sys.exit(1)

st.set_page_config(page_title="VibeDebt Auditor", page_icon="📊", layout="wide")
st.title("VibeDebt Auditor")
st.caption("Technical debt quantification and trend tracking for vibe-coded projects")


# ---------------------------------------------------------------------------
# Data loaders
# ---------------------------------------------------------------------------


def load_latest_result() -> dict | None:
    result_path = TMP_ROOT / "debt_audit_result.json"
    if not result_path.exists():
        return None
    try:
        return json.loads(result_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def load_trend_data() -> list[dict]:
    try:
        from execution.debt_history_db import DebtHistoryDB

        db = DebtHistoryDB()
        return db.get_trend_data(days=90)
    except Exception:
        return []


def load_project_trend(project_name: str) -> list[dict]:
    try:
        from execution.debt_history_db import DebtHistoryDB

        db = DebtHistoryDB()
        return db.get_project_trend(project_name, days=90)
    except Exception:
        return []


# ---------------------------------------------------------------------------
# Main layout
# ---------------------------------------------------------------------------

result = load_latest_result()
trend = load_trend_data()

if result is None:
    st.warning("No debt audit result found. Run `python workspace/execution/vibe_debt_auditor.py` first.")
    st.stop()

# --- Overall KPIs ---
grade = result.get("overall_grade", "UNKNOWN")
grade_colors = {"GREEN": "normal", "YELLOW": "off", "RED": "inverse"}
grade_labels = {"GREEN": "Healthy", "YELLOW": "Caution", "RED": "Critical"}

col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("Overall TDR", f"{result.get('overall_tdr', 0):.1f}%", help="Technical Debt Ratio (< 5% = healthy)")
with col2:
    st.metric("Grade", grade_labels.get(grade, grade))
with col3:
    st.metric("Fix Cost (Principal)", f"{result.get('total_principal_hours', 0):.1f}h")
with col4:
    st.metric("Monthly Interest", f"{result.get('total_interest_monthly_hours', 0):.1f}h/mo")

# --- TDR Trend ---
if trend:
    st.divider()
    st.subheader("TDR Trend (90 days)")

    try:
        import pandas as pd

        df = pd.DataFrame(trend)
        if not df.empty:
            df["date"] = pd.to_datetime(df["timestamp"]).dt.date
            chart_df = df[["date", "overall_tdr"]].set_index("date")
            st.line_chart(chart_df, use_container_width=True)
    except ImportError:
        st.info("Install pandas for trend charts: pip install pandas")

# --- Per-Project Breakdown ---
st.divider()
st.subheader("Project Breakdown")

projects = result.get("projects", [])
if projects:
    proj_cols = st.columns(len(projects))
    for i, proj in enumerate(projects):
        with proj_cols[i]:
            p_grade = proj.get("tdr_grade", "?")
            st.markdown(f"### {proj['name']}")
            st.metric("TDR", f"{proj.get('tdr_percent', 0):.1f}%")
            st.metric("Avg Debt Score", f"{proj.get('avg_score', 0):.1f} / 100")
            st.metric("Files", proj.get("file_count", 0))
            st.metric("Code Lines", f"{proj.get('total_code_lines', 0):,}")
            st.metric("Principal", f"{proj.get('total_principal_minutes', 0):.0f} min")

            # Dimension radar (text-based)
            dims = proj.get("dimension_averages", {})
            if dims:
                st.markdown("**Dimension Scores**")
                for dim, score in dims.items():
                    label = dim.replace("_", " ").title()
                    bar_len = int(score / 5)
                    bar = "█" * bar_len + "░" * (20 - bar_len)
                    st.text(f"{label:15s} {bar} {score:.0f}")

# --- Top Debtors Table ---
st.divider()
st.subheader("Top Debtor Files")

file_scores = result.get("file_scores", [])
if file_scores:
    # Project filter
    all_projects = sorted(set(f.get("project", "") for f in file_scores))
    selected_proj = st.selectbox("Filter by project", ["All"] + all_projects)

    filtered = file_scores
    if selected_proj != "All":
        filtered = [f for f in file_scores if f.get("project") == selected_proj]

    # Score threshold filter
    min_score = st.slider("Minimum debt score", 0, 100, 20)
    filtered = [f for f in filtered if f.get("total_score", 0) >= min_score]

    st.caption(f"Showing {len(filtered)} files with score >= {min_score}")

    for f in filtered[:30]:
        with st.expander(f"{f.get('total_score', 0):.1f} | {f.get('relative_path', '')}"):
            mcol1, mcol2, mcol3 = st.columns(3)
            with mcol1:
                st.metric("Lines", f.get("code_lines", 0))
                st.metric("Functions", f.get("function_count", 0))
            with mcol2:
                st.metric("Max Complexity", f.get("max_complexity", 0))
                st.metric("Max Func Length", f.get("max_function_length", 0))
            with mcol3:
                st.metric("Debt Markers", f.get("debt_marker_count", 0))
                st.metric("Duplicates", f.get("duplicate_block_count", 0))

            st.markdown("**Dimension Scores**")
            dim_cols = st.columns(6)
            for j, dim in enumerate(
                ["complexity", "duplication", "test_gap", "debt_markers", "modularity", "doc_sync"]
            ):
                with dim_cols[j]:
                    st.metric(dim.replace("_", " ").title(), f"{f.get(f'{dim}_score', 0):.0f}")

            # Top functions
            top_funcs = f.get("top_functions", [])
            if top_funcs:
                st.markdown("**Most Complex Functions**")
                for tf in top_funcs[:5]:
                    st.text(f"  {tf['name']}() L{tf['line']} - CC:{tf['complexity']} Len:{tf['length']}")

            # Debt markers
            markers = f.get("debt_markers", [])
            if markers:
                st.markdown("**Debt Markers**")
                for m in markers[:5]:
                    st.text(f"  L{m['line']} [{m['type']}] {m['text'][:80]}")

            st.metric("Fix Cost", f"{f.get('principal_minutes', 0):.0f} min")

# --- Per-Project Trend Detail ---
if projects:
    st.divider()
    st.subheader("Project Trend Detail")
    proj_name = st.selectbox("Select project", [p["name"] for p in projects], key="proj_trend")
    proj_trend = load_project_trend(proj_name)

    if proj_trend:
        try:
            import pandas as pd

            df = pd.DataFrame(proj_trend)
            if not df.empty:
                df["date"] = pd.to_datetime(df["timestamp"]).dt.date
                chart_cols = st.columns(2)
                with chart_cols[0]:
                    st.markdown("**TDR %**")
                    st.line_chart(df[["date", "tdr_percent"]].set_index("date"))
                with chart_cols[1]:
                    st.markdown("**Avg Debt Score**")
                    st.line_chart(df[["date", "avg_score"]].set_index("date"))
        except ImportError:
            pass
    else:
        st.info("No historical data yet. Run the auditor multiple times to build trend data.")

# --- Footer ---
st.divider()
ts = result.get("timestamp", "")
st.caption(
    f"Last scan: {ts[:19].replace('T', ' ') if ts else '-'} | "
    f"{result.get('total_files', 0)} files in {result.get('scan_duration_seconds', 0)}s"
)
