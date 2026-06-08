import sys
from pathlib import Path

_WORKSPACE_ROOT = Path(__file__).resolve().parents[2]
if str(_WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(_WORKSPACE_ROOT))

import streamlit as st  # noqa: E402

try:
    import plotly.graph_objects as go
    from execution.roi_calculator import ROICalculator
    from execution.result_tracker_db import (
        get_all,
        get_channel_summary,
        init_db as init_result_db,
    )

    _MODULE_OK = True
except ImportError as e:
    _MODULE_OK = False
    _MODULE_ERR = str(e)

st.set_page_config(page_title="쇼츠 ROI 분석 - Joolife", page_icon="💰", layout="wide")

if not _MODULE_OK:
    st.error(f"ROI 모듈을 불러올 수 없습니다: {_MODULE_ERR}")
    st.stop()

init_result_db()

st.title("쇼츠 ROI", anchor=False)
st.caption("업로드 성과와 제작비를 연결해 채널별 수익성을 점검합니다.")

_PLOTLY_CHART_CONFIG = {"displayModeBar": False}


def _inject_roi_dashboard_mobile_css() -> None:
    st.markdown(
        """
<style>
@media (max-width: 640px) {
  div[data-testid='stNumberInput'] div[data-baseweb='input'],
  div[data-testid='stNumberInput'] input,
  div[data-testid='stNumberInput'] button,
  button[data-testid='stBaseButton-headerNoPadding'],
  button[data-testid='stBaseButton-header'],
  button[data-testid='stExpandSidebarButton'],
  button[data-testid='stMainMenuButton'] {
    min-height: 44px !important;
  }

  div[data-testid='stNumberInput'],
  div[data-testid='stNumberInputContainer'],
  div[data-testid='stNumberInput'] div[data-baseweb='input'],
  div[data-testid='stNumberInput'] div[data-baseweb='base-input'],
  div[data-testid='stNumberInput'] input,
  div[data-testid='stNumberInput'] button,
  button[data-testid='stBaseButton-headerNoPadding'],
  button[data-testid='stBaseButton-header'],
  button[data-testid='stExpandSidebarButton'],
  button[data-testid='stMainMenuButton'] {
    min-width: 44px !important;
  }
}
</style>
""",
        unsafe_allow_html=True,
    )


_inject_roi_dashboard_mobile_css()


def _render_plotly_chart(fig) -> None:
    st.plotly_chart(fig, width="stretch", config=_PLOTLY_CHART_CONFIG)


# ── RPM 설정 ──
rpm = st.sidebar.number_input(
    "Shorts RPM 추정값 ($)",
    value=1.5,
    min_value=0.1,
    step=0.1,
    help="YouTube Analytics 기준 Shorts RPM은 1,000 engaged views당 크리에이터 수익 지표입니다.",
)

calc = ROICalculator(rpm=rpm)

# ── 채널별 ROI 요약 ──
channel_data = get_channel_summary()

if channel_data:
    st.subheader("채널별 ROI 요약")

    summaries = []
    for ch_row in channel_data:
        channel_name = ch_row.get("channel", "unknown")
        contents = get_all(channel=channel_name)
        content_list = [
            {
                "title": c.get("title", ""),
                "channel": channel_name,
                "views": c.get("views", 0),
                "cost_usd": 0.10,  # 기본 추정 비용
            }
            for c in contents
        ]
        if content_list:
            summary = calc.generate_channel_summary(content_list)
            summaries.append(summary)

    if summaries:
        cols = st.columns(min(len(summaries), 4))
        for i, s in enumerate(summaries):
            with cols[i % len(cols)]:
                status_icon = {"profit": "📈", "loss": "📉", "breakeven": "⚖️"}.get(s.breakeven_status, "❓")
                st.metric(
                    f"{status_icon} {s.channel}",
                    f"ROI {s.avg_roi_percent:+.1f}%",
                    f"{s.total_content}건 · ${s.total_cost:.2f}",
                )
                st.caption(f"조회 {s.total_views:,} · 예상수익 ${s.total_estimated_revenue:.2f}")

        st.divider()

        # ── ROI 비교 차트 ──
        fig = go.Figure()
        fig.add_trace(
            go.Bar(
                x=[s.channel for s in summaries],
                y=[s.total_cost for s in summaries],
                name="총 비용 ($)",
                marker_color="#f87171",
            )
        )
        fig.add_trace(
            go.Bar(
                x=[s.channel for s in summaries],
                y=[s.total_estimated_revenue for s in summaries],
                name="예상 수익 ($)",
                marker_color="#4ade80",
            )
        )
        fig.update_layout(
            title="채널별 비용 vs 수익",
            barmode="group",
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            font_color="#e0e0e0",
        )
        _render_plotly_chart(fig)

    st.divider()

    # ── 손익분기점 계산기 ──
    st.subheader("📊 손익분기점 계산기")
    bep_col1, bep_col2 = st.columns(2)
    with bep_col1:
        bep_cost = st.number_input("콘텐츠당 비용 ($)", value=0.10, step=0.01, format="%.2f")
    with bep_col2:
        bep_views = calc.calculate_breakeven_views(bep_cost)
        st.metric("손익분기점 조회수", f"{bep_views:,} 조회")
        st.caption(f"RPM ${rpm} 기준, 이 조회수를 넘으면 수익 발생")

    # ── 비용 효율 제안 ──
    st.divider()
    st.subheader("💡 비용 효율 최적화 제안")
    suggestions = []
    avg_cost = sum(s.avg_cost_per_content for s in summaries) / max(len(summaries), 1)
    if avg_cost > 0.15:
        suggestions.append("⚡ 무료 TTS (Edge TTS) 비율 높이기 → TTS 비용 제거")
    if avg_cost > 0.20:
        suggestions.append("🖼️ DALL-E 대신 Pexels 스톡 이미지 비율 높이기 (stock_mix_ratio ↑)")
    if any(s.avg_roi_percent < -50 for s in summaries):
        suggestions.append("🎯 ROI < -50% 채널은 토픽 전략 재검토 필요")
    if not suggestions:
        suggestions.append("✅ 현재 비용 효율이 양호합니다!")
    for s in suggestions:
        st.info(s)

else:
    st.info("콘텐츠 데이터가 없습니다. 콘텐츠 결과 관리에서 먼저 등록하세요.")
