import sys
from datetime import datetime, timedelta
from pathlib import Path

WORKSPACE_ROOT = Path(__file__).resolve().parents[2]
if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT))

import streamlit as st

from path_contract import TMP_ROOT, resolve_project_dir

try:
    import plotly.express as px
    import plotly.graph_objects as go

    from execution.api_usage_tracker import (
        check_api_keys,
        get_blind_to_x_summary,
        get_bridge_daily_breakdown,
        get_bridge_provider_breakdown,
        get_bridge_reason_breakdown,
        get_daily_breakdown,
        get_provider_breakdown,
        get_usage_summary,
        init_db,
    )
    from execution.language_bridge import BridgePolicy
    from execution.scheduler_engine import get_scheduler_kpis

    _MODULE_OK = True
except ImportError as e:
    _MODULE_OK = False
    _MODULE_ERR = str(e)

st.set_page_config(page_title="API 사용 모니터 - Joolife", page_icon="📡", layout="wide")

if not _MODULE_OK:
    st.error(f"API 사용 모니터 모듈을 불러올 수 없습니다: {_MODULE_ERR}")
    st.stop()


_PLOTLY_CHART_CONFIG = {
    "displayModeBar": False,
    "displaylogo": False,
    "responsive": True,
}


def _inject_api_monitor_mobile_css() -> None:
    st.markdown(
        """
<style>
@media (max-width: 640px) {
  div[data-testid='stAppViewContainer'] h1 {
    font-size: 2rem !important;
    line-height: 1.15 !important;
    padding: 0.5rem 0 0.25rem !important;
  }

  button[kind='primary'],
  button[kind='secondary'],
  div[data-testid='stButton'] button,
  div[data-testid='stFormSubmitButton'] button,
  div[data-testid='stSlider'] [role='slider'],
  div[data-testid='stTextInput'] input,
  div[data-testid='stNumberInput'] input,
  div[data-testid='stNumberInput'] button,
  div[data-baseweb='select'],
  div[data-baseweb='select'] > div,
  div[data-baseweb='input'],
  div[data-baseweb='input'] > div,
  div[data-baseweb='input'] input {
    min-height: 44px !important;
  }

  div[data-testid='stSlider'] [role='slider'],
  div[data-testid='stNumberInput'] button,
  div[data-testid='stButton'] button,
  div[data-testid='stFormSubmitButton'] button,
  button[aria-label='Main menu'],
  button[data-testid='stBaseButton-header'] {
    min-width: 44px !important;
  }

  button[aria-label='Main menu'],
  button[data-testid='stBaseButton-header'] {
    min-height: 44px !important;
  }
}
</style>
""",
        unsafe_allow_html=True,
    )


def _render_plotly_chart(fig: object) -> None:
    st.plotly_chart(fig, width="stretch", config=_PLOTLY_CHART_CONFIG)


def _load_btx_cost_database() -> tuple[object | None, str | None]:
    try:
        import importlib.util as _ilu

        btx_project = resolve_project_dir("blind-to-x", required_paths=("pipeline",))
        btx_cost_db_path = btx_project / "pipeline" / "cost_db.py"
        if not btx_cost_db_path.exists():
            return None, f"CostDB 파일이 없습니다: {btx_cost_db_path}"

        btx_project_str = str(btx_project)
        inserted = False
        if btx_project_str not in sys.path:
            sys.path.insert(0, btx_project_str)
            inserted = True
        try:
            spec = _ilu.spec_from_file_location("btx_cost_db_for_api_monitor", btx_cost_db_path)
            if not spec or not spec.loader:
                return None, f"CostDB 로더를 만들 수 없습니다: {btx_cost_db_path}"
            module = _ilu.module_from_spec(spec)
            spec.loader.exec_module(module)
            return module.CostDatabase(), None
        finally:
            if inserted:
                try:
                    sys.path.remove(btx_project_str)
                except ValueError:
                    pass
    except Exception as exc:
        return None, str(exc)


_inject_api_monitor_mobile_css()
init_db()

st.title("📡 API 사용 모니터")
st.caption("워크스페이스 API 호출, 토큰, 비용, 언어 브리지 상태를 한 화면에서 점검합니다.")

# ── API 키 상태 ──
st.subheader("API 키 상태")
keys = check_api_keys()
cols = st.columns(len(keys))
for i, (provider, configured) in enumerate(keys.items()):
    with cols[i]:
        status = "✅" if configured else "❌"
        st.markdown(f"**{provider.upper()}**")
        st.markdown(f"{status} {'설정됨' if configured else '미설정'}")

st.divider()

# ── 사용 요약 ──
days = st.slider("조회 기간(일)", min_value=7, max_value=90, value=30)
summary = get_usage_summary(days)
daily = get_daily_breakdown(days)
bridge_daily = get_bridge_daily_breakdown(days)
bridge_reasons = get_bridge_reason_breakdown(days)
bridge_providers = get_bridge_provider_breakdown(days)
bridge_policy = BridgePolicy.from_env()
scheduler_kpi = get_scheduler_kpis(days=min(days, 30))


def _count_agent_startup_failures(lookback_days: int) -> int:
    log_dir = TMP_ROOT / "logs"
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
    st.metric("총 API 호출", f"{summary['total_calls']:,}")
with col2:
    st.metric("총 토큰", f"{summary['total_tokens']:,}")
with col3:
    st.metric("예상 비용", f"${summary['total_cost_usd']:.4f}")
with col4:
    st.metric("브리지 이벤트", f"{sum(item['calls'] for item in bridge_daily):,}")

st.divider()

# ── KPI 스냅샷 ──
st.subheader("운영 KPI")
k1, k2, k3, k4 = st.columns(4)
with k1:
    st.metric("스케줄러 성공률", f"{scheduler_kpi['scheduler_success_rate']:.2f}%")
with k2:
    st.metric("스케줄러 대기열", scheduler_kpi["scheduler_backlog"])
with k3:
    st.metric("일평균 API 호출", api_calls_per_day)
with k4:
    st.metric("에이전트 시작 실패", startup_failures)

st.divider()

# ── 차트 ──
chart_col1, chart_col2 = st.columns(2)

with chart_col1:
    st.subheader("일별 API 사용량")
    if daily:
        fig = go.Figure()
        fig.add_trace(
            go.Bar(
                x=[d["day"] for d in daily],
                y=[d["calls"] for d in daily],
                name="API 호출",
                marker_color="#7c3aed",
            )
        )
        fig.update_layout(
            xaxis_title="날짜",
            yaxis_title="호출 수",
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            font_color="#e0e0e0",
        )
        _render_plotly_chart(fig)
    else:
        st.info("아직 API 사용 기록이 없습니다.")
        st.caption("실행 스크립트가 `api_usage_tracker.log_api_call()`을 호출하면 자동으로 기록됩니다.")

with chart_col2:
    st.subheader("프로바이더별 사용량")
    providers = get_provider_breakdown(days)
    if providers:
        fig = px.pie(
            values=[p["calls"] for p in providers],
            names=[p["provider"] for p in providers],
            title="프로바이더별 API 호출",
        )
        fig.update_layout(
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            font_color="#e0e0e0",
        )
        _render_plotly_chart(fig)
    else:
        st.info("프로바이더별 사용 데이터가 아직 없습니다.")

# ── 토큰 상세 ──
st.divider()
st.subheader("토큰 사용 상세")
if daily:
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=[d["day"] for d in daily],
            y=[d.get("input_tokens", 0) for d in daily],
            name="입력 토큰",
            fill="tozeroy",
            line=dict(color="#4ade80"),
        )
    )
    fig.add_trace(
        go.Scatter(
            x=[d["day"] for d in daily],
            y=[d.get("output_tokens", 0) for d in daily],
            name="출력 토큰",
            fill="tozeroy",
            line=dict(color="#f87171"),
        )
    )
    fig.update_layout(
        xaxis_title="날짜",
        yaxis_title="토큰",
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font_color="#e0e0e0",
    )
    _render_plotly_chart(fig)
else:
    st.info(
        "API 호출을 기록하려면 실행 스크립트에서 아래 함수를 호출하세요.\n\n"
        "```python\n"
        "from execution.api_usage_tracker import log_api_call\n"
        "log_api_call(provider='anthropic', model='claude-sonnet-4', tokens_input=500, tokens_output=200)\n"
        "```"
    )

# ── 브리지 정책 ──
st.divider()
st.subheader("LLM 브리지 정책")
policy = bridge_policy.as_dict()
bp1, bp2, bp3, bp4, bp5 = st.columns(5)
with bp1:
    st.metric("모드", policy["mode"])
with bp2:
    st.metric("최소 한글 비율", policy["min_hangul_ratio"])
with bp3:
    st.metric("최대 CJK 비율", policy["max_cjk_ratio"])
with bp4:
    st.metric("최대 자모 비율", policy["max_jamo_ratio"])
with bp5:
    st.metric("복구 시도", policy["repair_attempts"])
st.caption("폴백: " + ", ".join(policy["fallback_providers"]) + " | 엄격한 한국어: " + str(policy["strict_korean"]))

# ── 브리지 차트 ──
st.divider()
bridge_col1, bridge_col2 = st.columns(2)

with bridge_col1:
    st.subheader("일별 브리지 활동")
    if bridge_daily:
        fig = go.Figure()
        fig.add_trace(
            go.Bar(
                x=[d["day"] for d in bridge_daily],
                y=[d["calls"] for d in bridge_daily],
                name="브리지 호출",
                marker_color="#0ea5e9",
            )
        )
        fig.add_trace(
            go.Scatter(
                x=[d["day"] for d in bridge_daily],
                y=[d.get("average_language_score", 0) or 0 for d in bridge_daily],
                name="평균 언어 점수",
                yaxis="y2",
                line=dict(color="#f59e0b"),
            )
        )
        fig.update_layout(
            xaxis_title="날짜",
            yaxis_title="브리지 호출",
            yaxis2=dict(title="언어 점수", overlaying="y", side="right", range=[0, 1]),
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            font_color="#e0e0e0",
        )
        _render_plotly_chart(fig)
    else:
        st.info("아직 브리지 활동 기록이 없습니다.")

with bridge_col2:
    st.subheader("브리지 사유 코드")
    if bridge_reasons:
        fig = px.bar(
            x=[item["reason_code"] for item in bridge_reasons[:10]],
            y=[item["count"] for item in bridge_reasons[:10]],
            labels={"x": "사유 코드", "y": "건수"},
            title="상위 브리지 검증 사유",
        )
        fig.update_layout(
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            font_color="#e0e0e0",
        )
        _render_plotly_chart(fig)
    else:
        st.info("아직 브리지 사유 코드가 없습니다.")

# ── 프로바이더 브리지 지표 ──
st.divider()
st.subheader("프로바이더 브리지 지표")
if bridge_providers:
    header = st.columns([2, 2, 2, 2, 2, 2])
    header[0].markdown("**프로바이더**")
    header[1].markdown("**브리지 호출**")
    header[2].markdown("**실패율**")
    header[3].markdown("**복구 성공률**")
    header[4].markdown("**폴백 호출**")
    header[5].markdown("**평균 점수**")
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
    st.info("아직 프로바이더별 브리지 지표가 없습니다.")

# ── 비용 표 ──
st.divider()
if providers:
    st.subheader("프로바이더별 비용")
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
st.caption("caller_script='projects/blind-to-x/*' 로 필터링된 API 사용량")

btx_summary = get_blind_to_x_summary(days)
btx_col1, btx_col2 = st.columns(2)
with btx_col1:
    st.metric("총 API 호출 (blind-to-x)", f"{btx_summary['total_calls']:,}")
with btx_col2:
    st.metric("총 예상 비용 (blind-to-x)", f"${btx_summary['total_cost_usd']:.5f}")

if btx_summary["providers"]:
    st.markdown("**프로바이더별 상세**")
    btx_header = st.columns([3, 2, 2, 2, 2])
    btx_header[0].markdown("**프로바이더**")
    btx_header[1].markdown("**호출**")
    btx_header[2].markdown("**입력 토큰**")
    btx_header[3].markdown("**출력 토큰**")
    btx_header[4].markdown("**비용(USD)**")
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
        _render_plotly_chart(fig_btx)
else:
    st.info("blind-to-x API 호출 기록이 없습니다. 파이프라인 실행 후 확인하세요.")

# ── blind-to-x SQLite 비용 DB (Phase 1-2/1-3) ────────────────────────
st.divider()
st.subheader("💰 blind-to-x 실시간 비용 추적")
st.caption("projects/blind-to-x/pipeline/cost_db.py → .tmp/btx_costs.db")

_BTX_COST_DB, _BTX_COST_DB_ERROR = _load_btx_cost_database()
if _BTX_COST_DB_ERROR:
    st.caption(f"⚠️ BTX CostDB 로드 실패: {_BTX_COST_DB_ERROR}")

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
        _fig_trend.add_trace(
            go.Bar(
                x=[r["date"] for r in _trend],
                y=[r["text_usd"] for r in _trend],
                name="텍스트 비용",
                marker_color="#7c3aed",
            )
        )
        _fig_trend.add_trace(
            go.Bar(
                x=[r["date"] for r in _trend],
                y=[r["image_usd"] for r in _trend],
                name="이미지 비용",
                marker_color="#f59e0b",
            )
        )
        _fig_trend.update_layout(
            barmode="stack",
            xaxis_title="날짜",
            yaxis_title="USD",
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            font_color="#e0e0e0",
        )
        _render_plotly_chart(_fig_trend)

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
