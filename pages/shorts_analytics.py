"""
Shorts Analytics - 콘텐츠 생산 성과 분석 대시보드.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import streamlit as st

_MODULE_OK = False
_MODULE_ERR = ""
try:
    import plotly.express as px
    import plotly.graph_objects as go
    from execution.content_db import (
        get_channel_stats,
        get_daily_stats,
        get_hourly_stats,
        get_kpis,
        init_db,
    )
    _MODULE_OK = True
except ImportError as e:
    _MODULE_ERR = str(e)

st.set_page_config(page_title="Shorts Analytics", page_icon="📊", layout="wide")

if not _MODULE_OK:
    st.error(f"모듈 로드 실패: {_MODULE_ERR}")
    st.stop()

init_db()

# ---------------------------------------------------------------------------
# 상단 KPI
# ---------------------------------------------------------------------------
st.title("📊 Shorts Analytics")
st.caption("YouTube Shorts 콘텐츠 생산 성과 분석")

kpis = get_kpis()
total = kpis.get("total", 0)
success = kpis.get("success_count", 0)
failed = kpis.get("failed_count", 0)
pending = kpis.get("pending_count", 0)
total_cost = kpis.get("total_cost_usd", 0.0)
avg_cost = kpis.get("avg_cost_usd", 0.0)
rate = round(success / max(success + failed, 1) * 100, 1)

c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("총 콘텐츠", total)
c2.metric("생성 완료", success)
c3.metric("성공률", f"{rate}%")
c4.metric("총 비용", f"${total_cost:.2f}")
c5.metric("편당 평균", f"${avg_cost:.3f}")

st.divider()

# ---------------------------------------------------------------------------
# 일별 추이 (기간 선택)
# ---------------------------------------------------------------------------
days = st.slider("분석 기간 (일)", min_value=7, max_value=90, value=30)
daily = get_daily_stats(days)

CHART_LAYOUT = dict(
    plot_bgcolor="rgba(0,0,0,0)",
    paper_bgcolor="rgba(0,0,0,0)",
    font_color="#e0e0e0",
    margin=dict(l=20, r=20, t=40, b=20),
    height=320,
)

if daily:
    col_left, col_right = st.columns(2)

    with col_left:
        st.subheader("일별 생성 추이")
        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=[d["day"] for d in daily],
            y=[d["success"] for d in daily],
            name="성공",
            marker_color="#4ade80",
        ))
        fig.add_trace(go.Bar(
            x=[d["day"] for d in daily],
            y=[d["failed"] for d in daily],
            name="실패",
            marker_color="#f87171",
        ))
        fig.update_layout(barmode="stack", **CHART_LAYOUT)
        st.plotly_chart(fig, width="stretch")

    with col_right:
        st.subheader("일별 비용 추이")
        fig2 = go.Figure()
        fig2.add_trace(go.Scatter(
            x=[d["day"] for d in daily],
            y=[d["cost_usd"] for d in daily],
            mode="lines+markers",
            name="비용 ($)",
            line=dict(color="#7c3aed", width=2),
            fill="tozeroy",
            fillcolor="rgba(124,58,237,0.15)",
        ))
        fig2.update_layout(**CHART_LAYOUT)
        st.plotly_chart(fig2, width="stretch")
else:
    st.info("아직 완료된 콘텐츠가 없습니다.")

st.divider()

# ---------------------------------------------------------------------------
# 채널별 분석
# ---------------------------------------------------------------------------
channel_stats = get_channel_stats()

if channel_stats:
    st.subheader("채널별 분석")
    col_a, col_b = st.columns(2)

    with col_a:
        # 채널별 성공 분포 파이 차트
        ch_names = [c["channel"] for c in channel_stats]
        ch_success = [c["success"] for c in channel_stats]
        if any(v > 0 for v in ch_success):
            fig3 = px.pie(
                names=ch_names,
                values=ch_success,
                title="채널별 완료 비율",
                color_discrete_sequence=px.colors.qualitative.Set2,
            )
            fig3.update_layout(**CHART_LAYOUT)
            st.plotly_chart(fig3, width="stretch")
        else:
            st.info("완료된 영상이 없어 분포를 표시할 수 없습니다.")

    with col_b:
        # 채널별 상세 테이블
        st.markdown("**채널별 상세**")
        for cs in channel_stats:
            ch = cs["channel"]
            with st.container():
                m1, m2, m3, m4 = st.columns(4)
                m1.metric(ch, f"{cs['success']}편 완료")
                m2.metric("대기", cs["pending"])
                m3.metric("총 비용", f"${cs['total_cost']:.2f}")
                m4.metric("평균 길이", f"{cs['avg_duration']:.0f}초")

    # 채널별 평균 비용 비교 바 차트
    st.subheader("채널별 편당 비용 비교")
    ch_with_cost = [c for c in channel_stats if c["avg_cost"] > 0]
    if ch_with_cost:
        fig4 = go.Figure(go.Bar(
            x=[c["channel"] for c in ch_with_cost],
            y=[c["avg_cost"] for c in ch_with_cost],
            marker_color="#60a5fa",
            text=[f"${c['avg_cost']:.3f}" for c in ch_with_cost],
            textposition="outside",
        ))
        fig4.update_layout(
            yaxis_title="평균 비용 ($)",
            **CHART_LAYOUT,
        )
        st.plotly_chart(fig4, width="stretch")

st.divider()

# ---------------------------------------------------------------------------
# 비용 예측
# ---------------------------------------------------------------------------
st.subheader("월간 비용 예측")
if daily:
    recent_days = daily[-7:] if len(daily) >= 7 else daily
    avg_daily_cost = sum(d["cost_usd"] for d in recent_days) / max(len(recent_days), 1)
    avg_daily_count = sum(d["success"] for d in recent_days) / max(len(recent_days), 1)
    monthly_cost = avg_daily_cost * 30
    monthly_count = avg_daily_count * 30

    p1, p2, p3 = st.columns(3)
    p1.metric("일 평균 비용", f"${avg_daily_cost:.2f}")
    p2.metric("월 예상 비용", f"${monthly_cost:.1f}", delta=f"예산 $100 대비 {monthly_cost/100*100:.0f}%")
    p3.metric("월 예상 편수", f"{monthly_count:.0f}편")
else:
    st.info("데이터 축적 후 예측이 가능합니다.")

st.divider()

# ---------------------------------------------------------------------------
# 시간대별 분석
# ---------------------------------------------------------------------------
st.subheader("시간대별 생성 분석")
hourly = get_hourly_stats(days)

if hourly:
    fig_hourly = go.Figure(go.Bar(
        x=[h["hour"] for h in hourly],
        y=[h["success"] for h in hourly],
        marker_color="#34d399",
        text=[f"{h['success_rate']:.0f}%" for h in hourly],
        textposition="outside",
    ))
    fig_hourly.update_layout(
        xaxis_title="시간대 (시)",
        yaxis_title="성공 건수",
        **CHART_LAYOUT,
    )
    st.plotly_chart(fig_hourly, width="stretch")

    best_hour = max(hourly, key=lambda h: h["success_rate"])
    st.success(f"최적 생성 시간대: {best_hour['hour']}시 (성공률 {best_hour['success_rate']:.0f}%)")
else:
    st.info("시간대 분석을 위한 데이터가 아직 부족합니다.")
