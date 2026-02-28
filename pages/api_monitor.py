import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import streamlit as st

try:
    import plotly.express as px
    import plotly.graph_objects as go
    from execution.api_usage_tracker import (
        check_api_keys,
        get_daily_breakdown,
        get_provider_breakdown,
        get_usage_summary,
        init_db,
    )
    from execution.scheduler_engine import get_scheduler_kpis
    _MODULE_OK = True
except ImportError as e:
    _MODULE_OK = False
    _MODULE_ERR = str(e)

st.set_page_config(page_title="API Monitor - Joolife", page_icon="📡", layout="wide")

if not _MODULE_OK:
    st.error(f"API Monitor 모듈을 불러올 수 없습니다: {_MODULE_ERR}")
    st.stop()

init_db()

st.title("📡 API Monitor")
st.caption("API usage tracking & credit monitoring")

# ── API Key Status ──
st.subheader("API Key Status")
keys = check_api_keys()
cols = st.columns(len(keys))
for i, (provider, configured) in enumerate(keys.items()):
    with cols[i]:
        status = "✅" if configured else "❌"
        st.markdown(f"**{provider.upper()}**")
        st.markdown(f"{status} {'Configured' if configured else 'Not set'}")

st.divider()

# ── Usage Summary ──
days = st.slider("Time range (days)", min_value=7, max_value=90, value=30)
summary = get_usage_summary(days)
daily = get_daily_breakdown(days)
scheduler_kpi = get_scheduler_kpis(days=min(days, 30))


def _count_agent_startup_failures(lookback_days: int) -> int:
    log_dir = Path("projects/personal-agent/logs")
    if not log_dir.exists():
        return 0
    cutoff = datetime.now() - timedelta(days=lookback_days)
    count = 0
    for fp in log_dir.glob("*.log"):
        try:
            if datetime.fromtimestamp(fp.stat().st_mtime) < cutoff:
                continue
            text = fp.read_text(encoding="utf-8", errors="ignore")
            count += text.count("Critical System Failure")
            count += text.count("Module Load Error")
            count += text.count("Scheduler Init Error")
        except OSError:
            continue
    return count


api_calls_per_day = round(summary["total_calls"] / max(days, 1), 2)
startup_failures = _count_agent_startup_failures(days)

col1, col2, col3 = st.columns(3)
with col1:
    st.metric("Total API Calls", f"{summary['total_calls']:,}")
with col2:
    st.metric("Total Tokens", f"{summary['total_tokens']:,}")
with col3:
    st.metric("Estimated Cost", f"${summary['total_cost_usd']:.4f}")

st.divider()

# ── KPI Snapshot ──
st.subheader("Operational KPIs")
k1, k2, k3, k4 = st.columns(4)
with k1:
    st.metric("scheduler_success_rate", f"{scheduler_kpi['scheduler_success_rate']:.2f}%")
with k2:
    st.metric("scheduler_backlog", scheduler_kpi["scheduler_backlog"])
with k3:
    st.metric("api_calls_per_day", api_calls_per_day)
with k4:
    st.metric("agent_startup_failures", startup_failures)

st.divider()

# ── Charts ──
chart_col1, chart_col2 = st.columns(2)

with chart_col1:
    st.subheader("Daily API Usage")
    if daily:
        fig = go.Figure()
        fig.add_trace(
            go.Bar(
                x=[d["day"] for d in daily],
                y=[d["calls"] for d in daily],
                name="API Calls",
                marker_color="#7c3aed",
            )
        )
        fig.update_layout(
            xaxis_title="Date",
            yaxis_title="Calls",
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            font_color="#e0e0e0",
        )
        st.plotly_chart(fig, width="stretch")
    else:
        st.info("No API usage data recorded yet.")
        st.caption(
            "Usage is logged when execution scripts call `log_api_call()` from `api_usage_tracker`."
        )

with chart_col2:
    st.subheader("Usage by Provider")
    providers = get_provider_breakdown(days)
    if providers:
        fig = px.pie(
            values=[p["calls"] for p in providers],
            names=[p["provider"] for p in providers],
            title="API Calls by Provider",
        )
        fig.update_layout(
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            font_color="#e0e0e0",
        )
        st.plotly_chart(fig, width="stretch")
    else:
        st.info("No provider data yet.")

# ── Token Breakdown ──
st.divider()
st.subheader("Token Usage Detail")
if daily:
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=[d["day"] for d in daily],
            y=[d.get("input_tokens", 0) for d in daily],
            name="Input Tokens",
            fill="tozeroy",
            line=dict(color="#4ade80"),
        )
    )
    fig.add_trace(
        go.Scatter(
            x=[d["day"] for d in daily],
            y=[d.get("output_tokens", 0) for d in daily],
            name="Output Tokens",
            fill="tozeroy",
            line=dict(color="#f87171"),
        )
    )
    fig.update_layout(
        xaxis_title="Date",
        yaxis_title="Tokens",
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font_color="#e0e0e0",
    )
    st.plotly_chart(fig, width="stretch")
else:
    st.info(
        "Start logging API calls using:\n\n"
        "```python\n"
        "from execution.api_usage_tracker import log_api_call\n"
        "log_api_call(provider='anthropic', model='claude-sonnet-4', tokens_input=500, tokens_output=200)\n"
        "```"
    )

# ── Cost Table ──
st.divider()
if providers:
    st.subheader("Cost by Provider")
    for p in providers:
        pc1, pc2, pc3 = st.columns([3, 2, 2])
        with pc1:
            st.markdown(f"**{p['provider'].upper()}**")
        with pc2:
            st.markdown(f"{p['calls']:,} calls | {p.get('tokens', 0):,} tokens")
        with pc3:
            st.markdown(f"${p.get('cost', 0):.4f}")
