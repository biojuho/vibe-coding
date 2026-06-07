"""Operator-facing AI cost dashboard for Joolife Hub."""

import importlib.util
import json
import sys
from datetime import datetime
from pathlib import Path

WORKSPACE_ROOT = Path(__file__).resolve().parents[2]
if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT))

from path_contract import resolve_project_dir

import streamlit as st

try:
    import plotly.express as px
    import plotly.graph_objects as go
    from execution.api_usage_tracker import (
        MONTHLY_BUDGET_USD,
        get_daily_breakdown,
        get_fallback_analysis,
        get_model_breakdown,
        get_monthly_summary,
        get_provider_breakdown,
        get_savings_estimate,
        get_task_breakdown,
        get_usage_summary,
        init_db,
    )

    _MODULE_OK = True
except ImportError as e:
    _MODULE_OK = False
    _MODULE_ERR = str(e)

st.set_page_config(page_title="비용 관리 - Joolife", page_icon="💰", layout="wide")

if not _MODULE_OK:
    st.error(f"비용 대시보드 모듈을 불러오지 못했습니다: {_MODULE_ERR}")
    st.stop()

init_db()

# ── Theme ──
_CHART_LAYOUT = dict(
    plot_bgcolor="rgba(0,0,0,0)",
    paper_bgcolor="rgba(0,0,0,0)",
    font_color="#e0e0e0",
)
_COLORS = ["#7c3aed", "#0ea5e9", "#f59e0b", "#10b981", "#f43f5e", "#8b5cf6", "#06b6d4"]
_PLOTLY_CHART_CONFIG = {"displayModeBar": False, "responsive": True}


def _inject_cost_dashboard_mobile_css() -> None:
    st.markdown(
        """
        <style>
        @media (max-width: 640px) {
            div[data-testid="stToolbar"] button,
            div[data-testid="stHeaderActionElements"] button,
            button[kind="header"] {
                min-height: 44px !important;
                min-width: 44px !important;
            }
            div[data-testid="stSlider"] {
                padding-bottom: 0.75rem;
            }
            div[data-baseweb="slider"] [role="slider"] {
                width: 44px !important;
                height: 44px !important;
                min-width: 44px !important;
                min-height: 44px !important;
                margin-top: -16px !important;
            }
            div[data-testid="stMetric"] {
                min-width: 0 !important;
                overflow-wrap: anywhere;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _render_plotly_chart(fig: object) -> None:
    st.plotly_chart(fig, width="stretch", config=_PLOTLY_CHART_CONFIG)


def _format_count(value: int | float, unit: str) -> str:
    return f"{value:,.0f}{unit}"


def _format_unit_cost(total_cost: float, calls: int | float) -> str:
    if calls <= 0:
        return "$0.000000"
    return f"${total_cost / calls:.6f}"


def _build_budget_action_message(budget_pct: float, savings_pct: float) -> tuple[str, str]:
    if budget_pct >= 95:
        return (
            "예산 초과 위험",
            "오늘 바로 고비용 모델과 자동 생성 작업을 확인하고, 불필요한 반복 실행을 중지하세요.",
        )
    if budget_pct >= 80:
        return (
            "예산 주의",
            "이번 주 안에 모델별 비용과 폴백 사용률을 확인해 다음 실행의 기본 모델을 조정하세요.",
        )
    if savings_pct >= 20:
        return (
            "절감 효과 유지",
            "현재 라우팅은 비용을 줄이고 있습니다. 다만 모델별 품질 이슈가 없는지 최근 결과물을 함께 확인하세요.",
        )
    return (
        "정상 운영",
        "예산은 안정적입니다. 호출당 비용과 프로젝트별 비용 추이를 주 1회만 점검해도 충분합니다.",
    )


_inject_cost_dashboard_mobile_css()

st.title("💰 비용 관리")
st.caption("프로젝트별 AI 비용, 예산 사용률, 절감 효과를 바로 판단할 수 있게 모았습니다.")

# ── Controls ──
days = st.slider("조회 기간 (일)", min_value=7, max_value=90, value=30, key="cost_days")

# ── Load Data ──
summary = get_usage_summary(days)
daily = get_daily_breakdown(days)
providers = get_provider_breakdown(days)
models = get_model_breakdown(days)
monthly = get_monthly_summary(months=6)
tasks = get_task_breakdown(days)
fallback = get_fallback_analysis(days)
savings = get_savings_estimate(days)
avg_cost_per_call = _format_unit_cost(summary["total_cost_usd"], summary["total_calls"])

# ──────────────────────────────────────────────────────────────────────────────
# Section 1: KPI Cards
# ──────────────────────────────────────────────────────────────────────────────
st.subheader("핵심 지표")

current_month_cost = 0.0
for m in monthly:
    if m["month"] == datetime.now().strftime("%Y-%m"):
        current_month_cost = m.get("cost") or 0.0

budget_pct = round(current_month_cost / MONTHLY_BUDGET_USD * 100, 1) if MONTHLY_BUDGET_USD > 0 else 0.0

k1, k2, k3, k4, k5, k6 = st.columns(6)
with k1:
    st.metric("기간 내 총 비용", f"${summary['total_cost_usd']:.4f}")
with k2:
    st.metric("이번달 비용", f"${current_month_cost:.4f}")
with k3:
    st.metric("총 호출 수", _format_count(summary["total_calls"], "회"))
with k4:
    st.metric("총 토큰", _format_count(summary["total_tokens"], "개"))
with k5:
    st.metric(f"월 예산 ({MONTHLY_BUDGET_USD:.0f}$)", f"{budget_pct:.1f}%")
with k6:
    st.metric("호출당 비용", avg_cost_per_call)

# ── Budget Alert Bar ──
if budget_pct >= 95:
    st.error(f"🔴 예산 경고: 월 예산의 {budget_pct:.1f}% 사용 — 즉시 확인 필요!")
elif budget_pct >= 80:
    st.warning(f"🟡 예산 주의: 월 예산의 {budget_pct:.1f}% 사용")
elif budget_pct >= 50:
    st.info(f"🟢 예산 정상: 월 예산의 {budget_pct:.1f}% 사용")

st.progress(min(int(budget_pct), 100), text=f"월 예산 사용률 {budget_pct:.1f}%")

action_title, action_body = _build_budget_action_message(budget_pct, savings["savings_pct"])
st.markdown(f"**다음 조치: {action_title}**")
st.info(action_body)
st.caption("판단 기준: 월 예산 대비 사용률, 최근 30일 절감률, 호출당 비용, 모델별 비용 분포")

st.divider()

# ──────────────────────────────────────────────────────────────────────────────
# Section 2: Savings Estimate (MiMo / Free-tier 절감 효과)
# ──────────────────────────────────────────────────────────────────────────────
st.subheader("절감 효과 (최근 30일)")
st.caption("프리미엄 모델 기준 대비 실제 라우팅 비용을 비교합니다.")

s1, s2, s3 = st.columns(3)
with s1:
    st.metric("실제 비용", f"${savings['actual_cost_usd']:.4f}")
with s2:
    st.metric("프리미엄 기준 비용", f"${savings['premium_baseline_usd']:.4f}")
with s3:
    delta_color = "normal" if savings["savings_usd"] >= 0 else "inverse"
    st.metric(
        "절감액",
        f"${savings['savings_usd']:.4f}",
        delta=f"{savings['savings_pct']:.1f}%",
        delta_color=delta_color,
    )

st.divider()

# ──────────────────────────────────────────────────────────────────────────────
# Section 3: Monthly Trend + Daily Breakdown
# ──────────────────────────────────────────────────────────────────────────────
chart_col1, chart_col2 = st.columns(2)

with chart_col1:
    st.subheader("월간 비용 추이")
    if monthly:
        fig = go.Figure()
        fig.add_trace(
            go.Bar(
                x=[m["month"] for m in monthly],
                y=[m.get("cost") or 0 for m in monthly],
                name="비용 (USD)",
                marker_color="#7c3aed",
            )
        )
        fig.add_hline(
            y=MONTHLY_BUDGET_USD,
            line_dash="dash",
            line_color="#f43f5e",
            annotation_text=f"예산 ${MONTHLY_BUDGET_USD:.0f}",
        )
        fig.update_layout(
            xaxis_title="월",
            yaxis_title="USD",
            **_CHART_LAYOUT,
        )
        _render_plotly_chart(fig)
    else:
        st.info("월간 데이터가 아직 없습니다.")

with chart_col2:
    st.subheader("일일 비용 추이")
    if daily:
        fig = go.Figure()
        fig.add_trace(
            go.Bar(
                x=[d["day"] for d in daily],
                y=[d.get("cost") or 0 for d in daily],
                name="비용 (USD)",
                marker_color="#0ea5e9",
            )
        )
        fig.add_trace(
            go.Scatter(
                x=[d["day"] for d in daily],
                y=[d["calls"] for d in daily],
                name="호출 수",
                yaxis="y2",
                line=dict(color="#f59e0b"),
            )
        )
        fig.update_layout(
            xaxis_title="날짜",
            yaxis_title="USD",
            yaxis2=dict(title="호출 수", overlaying="y", side="right"),
            **_CHART_LAYOUT,
        )
        _render_plotly_chart(fig)
    else:
        st.info("일일 데이터가 아직 없습니다.")

st.divider()

# ──────────────────────────────────────────────────────────────────────────────
# Section 4: Provider & Model Breakdown
# ──────────────────────────────────────────────────────────────────────────────
prov_col, model_col = st.columns(2)

with prov_col:
    st.subheader("프로바이더별 사용량")
    if providers:
        fig = px.pie(
            values=[p["calls"] for p in providers],
            names=[p["provider"] for p in providers],
            color_discrete_sequence=_COLORS,
        )
        fig.update_layout(**_CHART_LAYOUT)
        _render_plotly_chart(fig)

        for p in providers:
            c1, c2, c3 = st.columns([3, 2, 2])
            c1.markdown(f"**{p['provider']}**")
            c2.markdown(f"{p['calls']:,}회 | 토큰 {p.get('tokens') or 0:,}개")
            c3.markdown(f"${p.get('cost') or 0:.4f}")
    else:
        st.info("프로바이더 데이터 없음")

with model_col:
    st.subheader("모델별 비용")
    if models:
        fig = px.bar(
            x=[m["model"] or "(unknown)" for m in models],
            y=[m.get("cost") or 0 for m in models],
            color=[m["provider"] for m in models],
            labels={"x": "모델", "y": "USD", "color": "프로바이더"},
            color_discrete_sequence=_COLORS,
        )
        fig.update_layout(**_CHART_LAYOUT)
        _render_plotly_chart(fig)

        for m in models:
            c1, c2, c3 = st.columns([3, 2, 2])
            c1.markdown(f"`{m['model'] or '(unknown)'}`")
            c2.markdown(f"{m['calls']:,}회")
            c3.markdown(f"${m.get('cost') or 0:.4f}")
    else:
        st.info("모델 데이터 없음")

st.divider()

# ──────────────────────────────────────────────────────────────────────────────
# Section 5: Task / Project Breakdown
# ──────────────────────────────────────────────────────────────────────────────
st.subheader("태스크(프로젝트)별 비용")
if tasks:
    fig = px.bar(
        x=[t["caller_script"] or "(unknown)" for t in tasks],
        y=[t.get("cost") or 0 for t in tasks],
        labels={"x": "스크립트", "y": "USD"},
        color_discrete_sequence=_COLORS,
    )
    fig.update_layout(xaxis_tickangle=-30, **_CHART_LAYOUT)
    _render_plotly_chart(fig)

    header = st.columns([4, 2, 2, 2])
    header[0].markdown("**스크립트**")
    header[1].markdown("**호출 수**")
    header[2].markdown("**토큰**")
    header[3].markdown("**비용 (USD)**")
    for t in tasks:
        row = st.columns([4, 2, 2, 2])
        row[0].markdown(f"`{t['caller_script'] or '(unknown)'}`")
        row[1].markdown(f"{t['calls']:,}")
        row[2].markdown(f"{t.get('tokens') or 0:,}")
        row[3].markdown(f"${t.get('cost') or 0:.4f}")
else:
    st.info("태스크 데이터 없음")

st.divider()

# ──────────────────────────────────────────────────────────────────────────────
# Section 6: Fallback Chain Analysis
# ──────────────────────────────────────────────────────────────────────────────
st.subheader("LLM 폴백 체인 분석")

f1, f2, f3 = st.columns(3)
with f1:
    st.metric("총 호출", f"{fallback['total_calls']:,}")
with f2:
    st.metric("폴백 사용", f"{fallback['fallback_calls']:,}")
with f3:
    st.metric("폴백 비율", f"{fallback['fallback_rate']:.1f}%")

if fallback["by_provider"]:
    st.markdown("**폴백 시 사용된 프로바이더**")
    for fp in fallback["by_provider"]:
        c1, c2, c3 = st.columns([3, 2, 2])
        c1.markdown(f"`{fp['provider_used']}`")
        c2.markdown(f"{fp['calls']:,}회")
        c3.markdown(f"${fp.get('cost') or 0:.4f}")

st.divider()

# ──────────────────────────────────────────────────────────────────────────────
# Section 7: BTX Cost DB (optional)
# ──────────────────────────────────────────────────────────────────────────────
st.subheader("blind-to-x 실시간 비용")

_BTX_COST_DB = None
try:
    _btx_path = resolve_project_dir("blind-to-x", required_paths=("pipeline",)) / "pipeline" / "cost_db.py"
    _spec = importlib.util.spec_from_file_location("btx_cost_db", _btx_path)
    if _spec and _spec.loader:
        _mod = importlib.util.module_from_spec(_spec)
        _spec.loader.exec_module(_mod)
        _BTX_COST_DB = _mod.CostDatabase()
except Exception:
    pass

if _BTX_COST_DB:
    _today = _BTX_COST_DB.get_today_summary()
    _daily_budget = 3.0
    _total_usd = _today.get("total_usd", 0.0)
    _budget_pct = round(_total_usd / _daily_budget * 100, 1)

    bc1, bc2, bc3, bc4 = st.columns(4)
    with bc1:
        st.metric("텍스트 비용 (오늘)", f"${_today.get('text_usd', 0):.4f}")
    with bc2:
        st.metric("이미지 비용 (오늘)", f"${_today.get('image_usd', 0):.4f}")
    with bc3:
        st.metric("총 비용 (오늘)", f"${_total_usd:.4f}")
    with bc4:
        st.metric("일일 예산 사용률", f"{_budget_pct:.1f}%")

    # Gemini RPD gauge
    _gemini_count = _today.get("gemini_image_count", 0)
    _gemini_limit = _today.get("gemini_image_limit", 500)
    _gemini_pct = _today.get("gemini_rpd_pct", 0.0)
    st.markdown(f"**Gemini RPD**: {_gemini_count} / {_gemini_limit} ({_gemini_pct:.1f}%)")
    st.progress(min(int(_gemini_pct), 100), text=f"Gemini RPD {_gemini_pct:.1f}%")

    # 30-day trend
    _trend = _BTX_COST_DB.get_daily_trend(days)
    if _trend:
        fig_btx = go.Figure()
        fig_btx.add_trace(
            go.Bar(
                x=[r["date"] for r in _trend],
                y=[r["text_usd"] for r in _trend],
                name="텍스트",
                marker_color="#7c3aed",
            )
        )
        fig_btx.add_trace(
            go.Bar(
                x=[r["date"] for r in _trend],
                y=[r["image_usd"] for r in _trend],
                name="이미지",
                marker_color="#f59e0b",
            )
        )
        fig_btx.update_layout(barmode="stack", xaxis_title="날짜", yaxis_title="USD", **_CHART_LAYOUT)
        _render_plotly_chart(fig_btx)
else:
    st.info("BTX CostDB 로드 불가 — blind-to-x 파이프라인 실행 후 자동 연동됩니다.")

st.divider()

# ──────────────────────────────────────────────────────────────────────────────
# Section 8: shorts-maker-v2 Cost (optional)
# ──────────────────────────────────────────────────────────────────────────────
st.subheader("shorts-maker-v2 비용")

_shorts_costs_file = resolve_project_dir("shorts-maker-v2", required_paths=("logs",)) / "logs" / "costs.jsonl"
_shorts_records: list[dict] = []
if _shorts_costs_file.exists():
    try:
        with _shorts_costs_file.open("r", encoding="utf-8") as _f:
            for _line in _f:
                _line = _line.strip()
                if _line:
                    try:
                        _shorts_records.append(json.loads(_line))
                    except json.JSONDecodeError:
                        continue
    except OSError:
        pass

if _shorts_records:
    _shorts_total = sum(r.get("cost_usd", 0) for r in _shorts_records)
    _shorts_jobs = len(_shorts_records)
    _shorts_avg = _shorts_total / _shorts_jobs if _shorts_jobs else 0

    sc1, sc2, sc3 = st.columns(3)
    with sc1:
        st.metric("총 영상 수", f"{_shorts_jobs}")
    with sc2:
        st.metric("총 비용", f"${_shorts_total:.4f}")
    with sc3:
        st.metric("건당 평균", f"${_shorts_avg:.4f}")

    # Daily aggregation
    _shorts_by_day: dict[str, float] = {}
    for r in _shorts_records:
        ts = r.get("timestamp", "")
        try:
            day = ts[:10]
            if day:
                _shorts_by_day[day] = _shorts_by_day.get(day, 0.0) + r.get("cost_usd", 0)
        except (ValueError, TypeError):
            continue

    if _shorts_by_day:
        _sorted_days = sorted(_shorts_by_day.items())
        fig_shorts = go.Figure()
        fig_shorts.add_trace(
            go.Bar(
                x=[d[0] for d in _sorted_days],
                y=[d[1] for d in _sorted_days],
                name="영상 비용",
                marker_color="#10b981",
            )
        )
        fig_shorts.update_layout(xaxis_title="날짜", yaxis_title="USD", **_CHART_LAYOUT)
        _render_plotly_chart(fig_shorts)
else:
    st.info("shorts-maker-v2 비용 데이터 없음 — 영상 생성 후 자동 기록됩니다.")

# ── Footer ──
st.divider()
_now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
st.caption(f"마지막 갱신: {_now} | 데이터 소스: workspace.db, btx_costs.db, shorts costs.jsonl")
