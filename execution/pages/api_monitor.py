import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import streamlit as st

try:
    import plotly.express as px
    import plotly.graph_objects as go
    from execution.api_usage_tracker import (
        get_bridge_daily_breakdown,
        get_bridge_provider_breakdown,
        get_bridge_reason_breakdown,
        check_api_keys,
        get_daily_breakdown,
        get_provider_breakdown,
        get_usage_summary,
        get_blind_to_x_summary,
        init_db,
    )
    from execution.language_bridge import BridgePolicy
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
bridge_daily = get_bridge_daily_breakdown(days)
bridge_reasons = get_bridge_reason_breakdown(days)
bridge_providers = get_bridge_provider_breakdown(days)
bridge_policy = BridgePolicy.from_env()
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

col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("Total API Calls", f"{summary['total_calls']:,}")
with col2:
    st.metric("Total Tokens", f"{summary['total_tokens']:,}")
with col3:
    st.metric("Estimated Cost", f"${summary['total_cost_usd']:.4f}")
with col4:
    st.metric("Bridge Events", f"{sum(item['calls'] for item in bridge_daily):,}")

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

# ── Bridge Policy ──
st.divider()
st.subheader("LLM Bridge Policy")
policy = bridge_policy.as_dict()
bp1, bp2, bp3, bp4, bp5 = st.columns(5)
with bp1:
    st.metric("Mode", policy["mode"])
with bp2:
    st.metric("Min Hangul Ratio", policy["min_hangul_ratio"])
with bp3:
    st.metric("Max CJK Ratio", policy["max_cjk_ratio"])
with bp4:
    st.metric("Max Jamo Ratio", policy["max_jamo_ratio"])
with bp5:
    st.metric("Repair Attempts", policy["repair_attempts"])
st.caption(
    "Fallbacks: " + ", ".join(policy["fallback_providers"])
    + " | Strict Korean: " + str(policy["strict_korean"])
)

# ── Bridge Charts ──
st.divider()
bridge_col1, bridge_col2 = st.columns(2)

with bridge_col1:
    st.subheader("Daily Bridge Activity")
    if bridge_daily:
        fig = go.Figure()
        fig.add_trace(
            go.Bar(
                x=[d["day"] for d in bridge_daily],
                y=[d["calls"] for d in bridge_daily],
                name="Bridge Calls",
                marker_color="#0ea5e9",
            )
        )
        fig.add_trace(
            go.Scatter(
                x=[d["day"] for d in bridge_daily],
                y=[d.get("average_language_score", 0) or 0 for d in bridge_daily],
                name="Avg Language Score",
                yaxis="y2",
                line=dict(color="#f59e0b"),
            )
        )
        fig.update_layout(
            xaxis_title="Date",
            yaxis_title="Bridge Calls",
            yaxis2=dict(title="Language Score", overlaying="y", side="right", range=[0, 1]),
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            font_color="#e0e0e0",
        )
        st.plotly_chart(fig, width="stretch")
    else:
        st.info("No bridge activity recorded yet.")

with bridge_col2:
    st.subheader("Bridge Reason Codes")
    if bridge_reasons:
        fig = px.bar(
            x=[item["reason_code"] for item in bridge_reasons[:10]],
            y=[item["count"] for item in bridge_reasons[:10]],
            labels={"x": "Reason Code", "y": "Count"},
            title="Top Bridge Validation Reasons",
        )
        fig.update_layout(
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            font_color="#e0e0e0",
        )
        st.plotly_chart(fig, width="stretch")
    else:
        st.info("No bridge reason codes yet.")

# ── Provider Bridge Metrics ──
st.divider()
st.subheader("Provider Bridge Metrics")
if bridge_providers:
    header = st.columns([2, 2, 2, 2, 2, 2])
    header[0].markdown("**Provider**")
    header[1].markdown("**Bridge Calls**")
    header[2].markdown("**Failure Rate**")
    header[3].markdown("**Repair Success**")
    header[4].markdown("**Fallback Calls**")
    header[5].markdown("**Avg Score**")
    for item in bridge_providers:
        row = st.columns([2, 2, 2, 2, 2, 2])
        row[0].markdown(f"`{item['provider']}`")
        row[1].markdown(str(item["bridge_calls"]))
        row[2].markdown(f"{item['bridge_failure_rate']:.2f}%")
        repair_success_rate = item.get("repair_success_rate")
        if repair_success_rate is None:
            row[3].markdown("-")
        else:
            row[3].markdown(f"{repair_success_rate:.2f}%")
        row[4].markdown(str(item["fallback_calls"]))
        avg_score = item.get("average_language_score")
        row[5].markdown("-" if avg_score is None else f"{avg_score:.4f}")
else:
    st.info("No provider-level bridge metrics yet.")

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

# ── blind-to-x 비용 대시보드 ──────────────────────────────────────────
st.divider()
st.subheader("📰 blind-to-x 파이프라인 비용")
st.caption("caller_script='blind-to-x/*' 로 필터링된 API 사용량")

btx_summary = get_blind_to_x_summary(days)
btx_col1, btx_col2 = st.columns(2)
with btx_col1:
    st.metric("총 API 호출 (blind-to-x)", f"{btx_summary['total_calls']:,}")
with btx_col2:
    st.metric("총 예상 비용 (blind-to-x)", f"${btx_summary['total_cost_usd']:.5f}")

if btx_summary["providers"]:
    st.markdown("**프로바이더별 상세**")
    btx_header = st.columns([3, 2, 2, 2, 2])
    btx_header[0].markdown("**Provider**")
    btx_header[1].markdown("**Calls**")
    btx_header[2].markdown("**Input Tokens**")
    btx_header[3].markdown("**Output Tokens**")
    btx_header[4].markdown("**Cost (USD)**")
    for row in btx_summary["providers"]:
        cols = st.columns([3, 2, 2, 2, 2])
        cols[0].markdown(f"`{row['provider']}`")
        cols[1].markdown(str(row.get("calls", 0)))
        cols[2].markdown(f"{row.get('input_tokens') or 0:,}")
        cols[3].markdown(f"{row.get('output_tokens') or 0:,}")
        cols[4].markdown(f"${row.get('cost') or 0:.5f}")

    # 프로바이더 파이 차트
    if len(btx_summary["providers"]) > 1:
        fig_btx = px.pie(
            values=[r["calls"] for r in btx_summary["providers"]],
            names=[r["provider"] for r in btx_summary["providers"]],
            title="blind-to-x LLM 호출 분포",
        )
        fig_btx.update_layout(
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            font_color="#e0e0e0",
        )
        st.plotly_chart(fig_btx, use_container_width=True)
else:
    st.info("blind-to-x API 호출 기록이 없습니다. 파이프라인 실행 후 확인하세요.")

# ── blind-to-x SQLite 비용 DB (Phase 1-2/1-3) ────────────────────────
st.divider()
st.subheader("💰 blind-to-x 실시간 비용 추적")
st.caption("blind-to-x/pipeline/cost_db.py → .tmp/btx_costs.db")

_BTX_COST_DB = None
try:
    import importlib.util as _ilu
    from pathlib import Path as _Path
    _btx_root = _Path(__file__).resolve().parent.parent / "blind-to-x" / "pipeline" / "cost_db.py"
    _spec = _ilu.spec_from_file_location("btx_cost_db", _btx_root)
    if _spec and _spec.loader:
        _mod = _ilu.module_from_spec(_spec)
        _spec.loader.exec_module(_mod)
        _BTX_COST_DB = _mod.CostDatabase()
except Exception as _e:
    st.caption(f"⚠️ BTX CostDB 로드 실패: {_e}")

if _BTX_COST_DB:
    _today_summary = _BTX_COST_DB.get_today_summary()
    _GEMINI_LIMIT = _today_summary.get("gemini_image_limit", 500)
    _gemini_count = _today_summary.get("gemini_image_count", 0)
    _gemini_pct = _today_summary.get("gemini_rpd_pct", 0.0)
    _total_usd = _today_summary.get("total_usd", 0.0)
    _daily_budget = 3.0

    # KPI 행
    kc1, kc2, kc3, kc4 = st.columns(4)
    with kc1:
        st.metric("오늘 텍스트 비용", f"${_today_summary.get('text_usd', 0):.4f}")
    with kc2:
        st.metric("오늘 이미지 비용", f"${_today_summary.get('image_usd', 0):.4f}")
    with kc3:
        st.metric("오늘 총 비용", f"${_total_usd:.4f}")
    with kc4:
        _budget_pct = round(_total_usd / _daily_budget * 100, 1)
        st.metric("예산 사용률", f"{_budget_pct}%", delta=None)

    # Gemini RPD 게이지
    st.markdown(f"**Gemini 이미지 RPD**: {_gemini_count} / {_GEMINI_LIMIT}장 ({_gemini_pct:.1f}%)")
    _gauge_color = "🟢" if _gemini_pct < 70 else ("🟡" if _gemini_pct < 90 else "🔴")
    st.progress(min(int(_gemini_pct), 100), text=f"{_gauge_color} {_gemini_pct:.1f}% 사용")

    # 예산 사용률 프로그레스
    _budget_bar_color = "🟢" if _budget_pct < 50 else ("🟡" if _budget_pct < 80 else "🔴")
    st.markdown(f"**일일 예산**: ${_total_usd:.4f} / ${_daily_budget:.2f}")
    st.progress(min(int(_budget_pct), 100), text=f"{_budget_bar_color} {_budget_pct:.1f}%")

    # 30일 비용 추세 차트
    _trend = _BTX_COST_DB.get_daily_trend(days)
    if _trend:
        st.markdown("**30일 비용 추세**")
        _fig_trend = go.Figure()
        _fig_trend.add_trace(go.Bar(
            x=[r["date"] for r in _trend],
            y=[r["text_usd"] for r in _trend],
            name="텍스트 비용",
            marker_color="#7c3aed",
        ))
        _fig_trend.add_trace(go.Bar(
            x=[r["date"] for r in _trend],
            y=[r["image_usd"] for r in _trend],
            name="이미지 비용",
            marker_color="#f59e0b",
        ))
        _fig_trend.update_layout(
            barmode="stack",
            xaxis_title="날짜",
            yaxis_title="USD",
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            font_color="#e0e0e0",
        )
        st.plotly_chart(_fig_trend, use_container_width=True)

    # 드래프트 스타일 A/B 분석
    _draft_perf = _BTX_COST_DB.get_draft_style_performance(days)
    if _draft_perf:
        st.markdown("**드래프트 스타일 A/B 성과**")
        _ab_cols = st.columns([3, 2, 2, 2])
        _ab_cols[0].markdown("**스타일**")
        _ab_cols[1].markdown("**생성 횟수**")
        _ab_cols[2].markdown("**평균 랭크 점수**")
        _ab_cols[3].markdown("**발행 건수**")
        for _row in _draft_perf:
            _rc = st.columns([3, 2, 2, 2])
            _rc[0].markdown(f"`{_row['draft_style']}`")
            _rc[1].markdown(str(_row["total"]))
            _rc[2].markdown(f"{_row['avg_score']:.1f}")
            _rc[3].markdown(str(_row["published_cnt"]))
    else:
        st.info("BTX 비용 데이터가 없습니다. 파이프라인을 실행하면 자동으로 기록됩니다.")
else:
    st.info("BTX CostDB를 로드할 수 없습니다. blind-to-x 파이프라인을 한 번 실행해 주세요.")
