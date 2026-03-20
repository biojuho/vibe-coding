import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import streamlit as st

try:
    import plotly.express as px
    import plotly.graph_objects as go
    from execution.channel_growth_tracker import (
        add_channel,
        calculate_growth_rate,
        collect_channel_stats,
        get_channel_comparison,
        get_channels,
        get_growth_history,
        init_db,
    )

    _MODULE_OK = True
except ImportError as e:
    _MODULE_OK = False
    _MODULE_ERR = str(e)

st.set_page_config(page_title="Channel Growth - Joolife", page_icon="📈", layout="wide")

if not _MODULE_OK:
    st.error(f"Channel Growth 모듈을 불러올 수 없습니다: {_MODULE_ERR}")
    st.stop()

init_db()

st.title("📈 YouTube Channel Growth Tracker")
st.caption("5채널 독립 성장 추적 · 구독자/조회수/영상 수 · 7일/30일/90일 추이")

# ── 채널 비교 요약 ──
comparison = get_channel_comparison()

if comparison:
    st.subheader("채널 비교 (최신)")
    cols = st.columns(min(len(comparison), 5))
    for i, ch in enumerate(comparison):
        with cols[i % len(cols)]:
            st.metric(
                ch["name"] or ch["channel_id"][:10],
                f"{ch['subscribers']:,} 구독",
                f"{ch['sub_growth_7d']:+.1f}% (7d)",
            )
            st.caption(f"조회수 {ch['total_views']:,} · 영상 {ch['video_count']}")

    st.divider()

    # ── 성장 추이 차트 ──
    st.subheader("구독자 성장 추이")
    period = st.selectbox("기간", [30, 60, 90], index=0, format_func=lambda x: f"{x}일")

    chart_col1, chart_col2 = st.columns(2)

    channels = get_channels()

    with chart_col1:
        fig_sub = go.Figure()
        for ch in channels:
            history = get_growth_history(ch["id"], days=period)
            if history:
                fig_sub.add_trace(
                    go.Scatter(
                        x=[h["collected_at"] for h in history],
                        y=[h["subscribers"] for h in history],
                        name=ch["name"] or ch["channel_id"][:10],
                        mode="lines+markers",
                    )
                )
        fig_sub.update_layout(
            title="구독자 수 추이",
            xaxis_title="날짜",
            yaxis_title="구독자",
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            font_color="#e0e0e0",
        )
        st.plotly_chart(fig_sub, use_container_width=True)

    with chart_col2:
        fig_views = go.Figure()
        for ch in channels:
            history = get_growth_history(ch["id"], days=period)
            if history:
                fig_views.add_trace(
                    go.Scatter(
                        x=[h["collected_at"] for h in history],
                        y=[h["total_views"] for h in history],
                        name=ch["name"] or ch["channel_id"][:10],
                        mode="lines+markers",
                    )
                )
        fig_views.update_layout(
            title="조회수 추이",
            xaxis_title="날짜",
            yaxis_title="총 조회수",
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            font_color="#e0e0e0",
        )
        st.plotly_chart(fig_views, use_container_width=True)

    st.divider()

    # ── 성장률 비교 바 차트 ──
    st.subheader("7일 성장률 비교")
    fig_bar = go.Figure(
        data=[
            go.Bar(
                x=[ch["name"] or ch["channel_id"][:10] for ch in comparison],
                y=[ch["sub_growth_7d"] for ch in comparison],
                name="구독자 성장률 (%)",
                marker_color="#4ade80",
            ),
            go.Bar(
                x=[ch["name"] or ch["channel_id"][:10] for ch in comparison],
                y=[ch["view_growth_7d"] for ch in comparison],
                name="조회수 성장률 (%)",
                marker_color="#60a5fa",
            ),
        ]
    )
    fig_bar.update_layout(
        barmode="group",
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font_color="#e0e0e0",
    )
    st.plotly_chart(fig_bar, use_container_width=True)

else:
    st.info("등록된 채널이 없습니다. 아래에서 채널을 추가하세요.")

st.divider()

# ── 채널 추가 ──
st.subheader("채널 관리")
with st.form("add_channel"):
    c1, c2 = st.columns(2)
    with c1:
        new_channel_id = st.text_input("YouTube Channel ID", placeholder="UCxxxxxxxxxxxxxxxx")
    with c2:
        new_name = st.text_input("채널 별칭", placeholder="AI/기술")
    if st.form_submit_button("채널 추가", type="primary"):
        if new_channel_id.strip():
            add_channel(new_channel_id.strip(), new_name.strip())
            st.success(f"채널 등록: {new_name or new_channel_id}")
            st.rerun()

# ── 통계 수집 ──
st.divider()
if st.button("📊 통계 수집 (YouTube API)", type="secondary"):
    with st.spinner("YouTube API에서 채널 통계를 수집 중..."):
        result = collect_channel_stats()
    if "error" in result:
        st.error(result["error"])
    else:
        st.success(f"수집 완료: {result.get('updated', 0)}개 채널 업데이트")
        st.rerun()
