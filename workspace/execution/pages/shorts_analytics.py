"""
Shorts Analytics - YouTube 콘텐츠 성과 분석 대시보드.

생산 현황 + YouTube 성과 KPI + 채널별 ROI + 훅 패턴 분석을 통합.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import streamlit as st

_MODULE_OK = False
_MODULE_ERR = ""
try:
    import plotly.express as px
    import plotly.graph_objects as go
    from execution.content_db import (
        get_channel_performance_summary,
        get_channel_stats,
        get_daily_stats,
        get_hook_pattern_performance,
        get_hourly_stats,
        get_kpis,
        get_performance_stats,
        get_youtube_stats,
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

# ── 공통 차트 레이아웃 ───────────────────────────────────────────
CHART_LAYOUT = dict(
    plot_bgcolor="rgba(0,0,0,0)",
    paper_bgcolor="rgba(0,0,0,0)",
    font=dict(color="#e0e0e0", family="Pretendard, sans-serif"),
    margin=dict(l=20, r=20, t=40, b=20),
    height=320,
)

COLORS = {
    "primary": "#7c3aed",
    "success": "#4ade80",
    "danger": "#f87171",
    "warning": "#fbbf24",
    "info": "#60a5fa",
    "youtube": "#ff0000",
    "gradient": ["#7c3aed", "#a78bfa", "#c4b5fd", "#ddd6fe"],
    "channels": ["#f472b6", "#38bdf8", "#facc15", "#4ade80", "#fb923c"],
}

# ===========================================================================
# 탭 구성
# ===========================================================================
tab_prod, tab_youtube, tab_roi, tab_hooks = st.tabs(["📦 생산 현황", "📈 YouTube 성과", "💰 ROI 분석", "🎣 훅 패턴"])

# ===========================================================================
# TAB 1: 생산 현황
# ===========================================================================
with tab_prod:
    st.header("📦 Shorts 콘텐츠 생산 현황")
    st.caption("YouTube Shorts 콘텐츠 생산 파이프라인 KPI")

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

    # ── 일별 추이 ─────────────────────────────────────────────
    days = st.slider("분석 기간 (일)", min_value=7, max_value=90, value=30, key="prod_days")
    daily = get_daily_stats(days)

    if daily:
        col_left, col_right = st.columns(2)

        with col_left:
            st.subheader("일별 생성 추이")
            fig = go.Figure()
            fig.add_trace(
                go.Bar(
                    x=[d["day"] for d in daily],
                    y=[d["success"] for d in daily],
                    name="성공",
                    marker_color=COLORS["success"],
                )
            )
            fig.add_trace(
                go.Bar(
                    x=[d["day"] for d in daily],
                    y=[d["failed"] for d in daily],
                    name="실패",
                    marker_color=COLORS["danger"],
                )
            )
            fig.update_layout(barmode="stack", **CHART_LAYOUT)
            st.plotly_chart(fig, use_container_width=True)

        with col_right:
            st.subheader("일별 비용 추이")
            fig2 = go.Figure()
            fig2.add_trace(
                go.Scatter(
                    x=[d["day"] for d in daily],
                    y=[d["cost_usd"] for d in daily],
                    mode="lines+markers",
                    name="비용 ($)",
                    line=dict(color=COLORS["primary"], width=2),
                    fill="tozeroy",
                    fillcolor="rgba(124,58,237,0.15)",
                )
            )
            fig2.update_layout(**CHART_LAYOUT)
            st.plotly_chart(fig2, use_container_width=True)

        st.divider()

        # ── 월간 비용 예측 ────────────────────────────────────
        st.subheader("월간 비용 예측")
        recent_days = daily[-7:] if len(daily) >= 7 else daily
        avg_daily_cost = sum(d["cost_usd"] for d in recent_days) / max(len(recent_days), 1)
        avg_daily_count = sum(d["success"] for d in recent_days) / max(len(recent_days), 1)
        monthly_cost = avg_daily_cost * 30
        monthly_count = avg_daily_count * 30

        p1, p2, p3 = st.columns(3)
        p1.metric("일 평균 비용", f"${avg_daily_cost:.2f}")
        p2.metric("월 예상 비용", f"${monthly_cost:.1f}")
        p3.metric("월 예상 편수", f"{monthly_count:.0f}편")
    else:
        st.info("🎬 아직 완료된 콘텐츠가 없습니다. 영상 생성 후 이 대시보드에서 추이를 확인하세요.")

    st.divider()

    # ── 채널별 분석 ───────────────────────────────────────────
    channel_stats = get_channel_stats()
    if channel_stats:
        st.subheader("채널별 분석")
        col_a, col_b = st.columns(2)

        with col_a:
            ch_names = [c["channel"] for c in channel_stats]
            ch_success = [c["success"] for c in channel_stats]
            if any(v > 0 for v in ch_success):
                fig3 = px.pie(
                    names=ch_names,
                    values=ch_success,
                    title="채널별 완료 비율",
                    color_discrete_sequence=COLORS["channels"],
                )
                fig3.update_layout(**CHART_LAYOUT)
                st.plotly_chart(fig3, use_container_width=True)
            else:
                st.info("완료된 영상이 없어 분포를 표시할 수 없습니다.")

        with col_b:
            st.markdown("**채널별 상세**")
            for cs in channel_stats:
                ch = cs["channel"]
                with st.container():
                    m1, m2, m3, m4 = st.columns(4)
                    m1.metric(ch, f"{cs['success']}편 완료")
                    m2.metric("대기", cs["pending"])
                    m3.metric("총 비용", f"${cs['total_cost']:.2f}")
                    m4.metric("평균 길이", f"{cs['avg_duration']:.0f}초")

        # 편당 비용 비교
        ch_with_cost = [c for c in channel_stats if c["avg_cost"] > 0]
        if ch_with_cost:
            st.subheader("채널별 편당 비용 비교")
            fig4 = go.Figure(
                go.Bar(
                    x=[c["channel"] for c in ch_with_cost],
                    y=[c["avg_cost"] for c in ch_with_cost],
                    marker_color=COLORS["info"],
                    text=[f"${c['avg_cost']:.3f}" for c in ch_with_cost],
                    textposition="outside",
                )
            )
            fig4.update_layout(yaxis_title="평균 비용 ($)", **CHART_LAYOUT)
            st.plotly_chart(fig4, use_container_width=True)

    st.divider()

    # ── 시간대별 분석 ─────────────────────────────────────────
    st.subheader("시간대별 생성 분석")
    hourly = get_hourly_stats(days)
    if hourly:
        fig_hourly = go.Figure(
            go.Bar(
                x=[h["hour"] for h in hourly],
                y=[h["success"] for h in hourly],
                marker_color="#34d399",
                text=[f"{h['success_rate']:.0f}%" for h in hourly],
                textposition="outside",
            )
        )
        fig_hourly.update_layout(
            xaxis_title="시간대 (시)",
            yaxis_title="성공 건수",
            **CHART_LAYOUT,
        )
        st.plotly_chart(fig_hourly, use_container_width=True)
        best_hour = max(hourly, key=lambda h: h["success_rate"])
        st.success(f"최적 생성 시간대: {best_hour['hour']}시 (성공률 {best_hour['success_rate']:.0f}%)")
    else:
        st.info("시간대 분석을 위한 데이터가 아직 부족합니다.")

    st.divider()

    # ── YouTube 업로드 현황 ───────────────────────────────────
    st.subheader("YouTube 업로드 현황")
    yt_stats = get_youtube_stats()
    yt_total = yt_stats["uploaded"] + yt_stats["failed"] + yt_stats["awaiting"]

    yt1, yt2, yt3 = st.columns(3)
    yt1.metric("업로드 완료", yt_stats["uploaded"])
    yt2.metric("업로드 실패", yt_stats["failed"])
    yt3.metric("업로드 대기", yt_stats["awaiting"])

    if yt_total > 0:
        fig_yt = px.pie(
            names=["업로드 완료", "업로드 실패", "업로드 대기"],
            values=[yt_stats["uploaded"], yt_stats["failed"], yt_stats["awaiting"]],
            title="YouTube 업로드 상태 분포",
            color_discrete_sequence=[COLORS["youtube"], "#6c757d", COLORS["warning"]],
        )
        fig_yt.update_layout(**CHART_LAYOUT)
        st.plotly_chart(fig_yt, use_container_width=True)
    else:
        st.info("업로드 데이터가 아직 없습니다.")


# ===========================================================================
# TAB 2: YouTube 성과
# ===========================================================================
with tab_youtube:
    st.header("📈 YouTube 성과 대시보드")
    st.caption("업로드된 영상의 조회수/좋아요/댓글 성과 분석 (YouTube Data API v3)")

    perf_data = get_performance_stats()

    if not perf_data:
        st.info(
            "🎯 **아직 YouTube 성과 데이터가 없습니다.**\n\n"
            "다음 단계를 완료하면 이 대시보드가 활성화됩니다:\n"
            "1. `shorts-maker-v2`로 영상 생성\n"
            "2. `youtube_uploader.py`로 YouTube 업로드\n"
            "3. `yt_analytics_to_notion.py`로 성과 수집\n\n"
            "```bash\n"
            "python workspace/execution/yt_analytics_to_notion.py --dry-run\n"
            "```"
        )
    else:
        # ── 전체 성과 KPI ─────────────────────────────────────
        total_views = sum(d.get("yt_views", 0) or 0 for d in perf_data)
        total_likes = sum(d.get("yt_likes", 0) or 0 for d in perf_data)
        total_comments = sum(d.get("yt_comments", 0) or 0 for d in perf_data)
        avg_views = total_views / max(len(perf_data), 1)
        like_rate = total_likes / max(total_views, 1) * 100
        engagement_rate = (total_likes + total_comments) / max(total_views, 1) * 100

        k1, k2, k3, k4, k5, k6 = st.columns(6)
        k1.metric("총 영상", len(perf_data))
        k2.metric("총 조회수", f"{total_views:,}")
        k3.metric("평균 조회수", f"{avg_views:,.0f}")
        k4.metric("총 좋아요", f"{total_likes:,}")
        k5.metric("좋아요율", f"{like_rate:.1f}%")
        k6.metric("참여율", f"{engagement_rate:.2f}%")

        st.divider()

        # ── 채널별 성과 비교 ──────────────────────────────────
        ch_perf = get_channel_performance_summary()
        if ch_perf:
            st.subheader("채널별 YouTube 성과 비교")

            col_views, col_engage = st.columns(2)

            with col_views:
                fig_cv = go.Figure()
                fig_cv.add_trace(
                    go.Bar(
                        x=[c["channel"] for c in ch_perf],
                        y=[c["total_views"] for c in ch_perf],
                        name="총 조회수",
                        marker_color=COLORS["youtube"],
                        text=[f"{c['total_views']:,}" for c in ch_perf],
                        textposition="outside",
                    )
                )
                fig_cv.update_layout(
                    title="채널별 총 조회수",
                    yaxis_title="조회수",
                    **CHART_LAYOUT,
                )
                st.plotly_chart(fig_cv, use_container_width=True)

            with col_engage:
                fig_ce = go.Figure()
                fig_ce.add_trace(
                    go.Bar(
                        x=[c["channel"] for c in ch_perf],
                        y=[c["avg_views"] for c in ch_perf],
                        name="평균 조회수",
                        marker_color=COLORS["info"],
                        text=[f"{c['avg_views']:,.0f}" for c in ch_perf],
                        textposition="outside",
                    )
                )
                fig_ce.update_layout(
                    title="채널별 평균 조회수",
                    yaxis_title="평균 조회수",
                    **CHART_LAYOUT,
                )
                st.plotly_chart(fig_ce, use_container_width=True)

            # 채널 성과 테이블
            st.markdown("**채널별 상세 성과**")
            table_data = []
            for c in ch_perf:
                table_data.append(
                    {
                        "채널": c["channel"],
                        "영상 수": c["video_count"],
                        "총 조회수": f"{c['total_views']:,}",
                        "평균 조회수": f"{c['avg_views']:,.0f}",
                        "총 비용": f"${c['total_cost']:.2f}",
                        "CPV (원/조회)": f"${c['total_cost'] / max(c['total_views'], 1) * 1000:.2f}/1K"
                        if c["total_views"] > 0
                        else "-",
                    }
                )
            st.dataframe(table_data, use_container_width=True)

        st.divider()

        # ── 개별 영상 성과 랭킹 ───────────────────────────────
        st.subheader("🏆 성과 TOP 10")
        sorted_perf = sorted(perf_data, key=lambda x: x.get("yt_views") or 0, reverse=True)[:10]

        for i, item in enumerate(sorted_perf, 1):
            views = item.get("yt_views") or 0
            likes = item.get("yt_likes") or 0
            comments = item.get("yt_comments") or 0
            channel = item.get("channel", "")
            title = item.get("title") or item.get("topic", "")
            yt_url = item.get("youtube_url", "")

            with st.container():
                cols = st.columns([0.5, 3, 1, 1, 1, 1])
                cols[0].markdown(f"**#{i}**")
                link_text = f"[{title[:40]}]({yt_url})" if yt_url else title[:40]
                cols[1].markdown(f"**{link_text}**\n\n`{channel}`")
                cols[2].metric("조회수", f"{views:,}")
                cols[3].metric("좋아요", f"{likes:,}")
                cols[4].metric("댓글", f"{comments:,}")
                cols[5].metric("좋아요율", f"{likes / max(views, 1) * 100:.1f}%")


# ===========================================================================
# TAB 3: ROI 분석
# ===========================================================================
with tab_roi:
    st.header("💰 ROI / 비용 효율성 분석")
    st.caption("비용 대비 성과를 측정하여 최적 투자 전략 도출")

    ch_perf = get_channel_performance_summary()

    if not ch_perf or all(c["total_views"] == 0 for c in ch_perf):
        st.info(
            "🎯 **ROI 분석에 필요한 YouTube 성과 데이터가 부족합니다.**\n\n"
            "영상 업로드 → 통계 수집 후 이 섹션이 활성화됩니다."
        )
    else:
        # ── CPV (Cost per View) 분석 ──────────────────────────
        st.subheader("CPV (Cost per 1K Views) 비교")

        cpv_data = []
        for c in ch_perf:
            if c["total_views"] > 0 and c["total_cost"] > 0:
                cpv_data.append(
                    {
                        "channel": c["channel"],
                        "cpv_1k": c["total_cost"] / c["total_views"] * 1000,
                        "total_views": c["total_views"],
                        "total_cost": c["total_cost"],
                        "video_count": c["video_count"],
                    }
                )

        if cpv_data:
            cpv_sorted = sorted(cpv_data, key=lambda x: x["cpv_1k"])

            fig_cpv = go.Figure()
            fig_cpv.add_trace(
                go.Bar(
                    x=[c["channel"] for c in cpv_sorted],
                    y=[c["cpv_1k"] for c in cpv_sorted],
                    marker_color=[
                        COLORS["success"]
                        if c["cpv_1k"] < 0.5
                        else COLORS["warning"]
                        if c["cpv_1k"] < 2.0
                        else COLORS["danger"]
                        for c in cpv_sorted
                    ],
                    text=[f"${c['cpv_1k']:.2f}" for c in cpv_sorted],
                    textposition="outside",
                )
            )
            fig_cpv.update_layout(
                yaxis_title="CPV ($/1K views)",
                **CHART_LAYOUT,
            )
            st.plotly_chart(fig_cpv, use_container_width=True)

            # 효율성 등급
            best = cpv_sorted[0]
            st.success(
                f"🏆 **최고 효율 채널**: {best['channel']} "
                f"— CPV ${best['cpv_1k']:.2f}/1K views "
                f"({best['video_count']}편으로 {best['total_views']:,}회 조회)"
            )

        st.divider()

        # ── 채널별 수익 잠재력 ────────────────────────────────
        st.subheader("채널별 수익 잠재력 (AdSense 추정)")
        st.caption("Shorts CPM $0.04~0.10 기준 추정 (국가/카테고리별 차이 있음)")

        for c in ch_perf:
            if c["total_views"] > 0:
                low_rpm = 0.04
                high_rpm = 0.10
                est_low = c["total_views"] / 1000 * low_rpm
                est_high = c["total_views"] / 1000 * high_rpm
                roi_low = (est_low - c["total_cost"]) / max(c["total_cost"], 0.01) * 100
                roi_high = (est_high - c["total_cost"]) / max(c["total_cost"], 0.01) * 100

                with st.expander(f"📊 {c['channel']} — {c['video_count']}편, {c['total_views']:,}회"):
                    r1, r2, r3, r4 = st.columns(4)
                    r1.metric("투입 비용", f"${c['total_cost']:.2f}")
                    r2.metric("추정 수익 (하)", f"${est_low:.2f}")
                    r3.metric("추정 수익 (상)", f"${est_high:.2f}")
                    r4.metric("ROI 범위", f"{roi_low:.0f}%~{roi_high:.0f}%")


# ===========================================================================
# TAB 4: 훅 패턴 분석
# ===========================================================================
with tab_hooks:
    st.header("🎣 훅 패턴 성과 분석")
    st.caption("어떤 오프닝 패턴이 가장 효과적인지 분석합니다")

    hook_data = get_hook_pattern_performance()

    if not hook_data:
        st.info(
            "🎯 **훅 패턴 분석에 필요한 데이터가 부족합니다.**\n\n"
            "채널별 훅 패턴이 자동 기록됩니다:\n"
            '- `shocking_stat` — 충격 통계 ("성인 3명 중 1명이...")\n'
            '- `relatable_frustration` — 공감 고통 ("혹시 이런 경험...")\n'
            '- `myth_busting` — 통념 파괴 ("사실 이게 아니에요")\n'
            '- `counterintuitive_question` — 역발상 질문 ("만약 ~한다면?")\n\n'
            "영상 생성 시 `hook_pattern` 필드에 자동 기록됩니다."
        )
    else:
        # ── 훅 패턴별 평균 조회수 ─────────────────────────────
        st.subheader("훅 패턴별 평균 조회수")

        fig_hook = go.Figure()
        hook_sorted = sorted(hook_data, key=lambda x: x["avg_views"], reverse=True)

        fig_hook.add_trace(
            go.Bar(
                x=[h["hook_pattern"] for h in hook_sorted],
                y=[h["avg_views"] for h in hook_sorted],
                marker_color=[COLORS["channels"][i % len(COLORS["channels"])] for i in range(len(hook_sorted))],
                text=[f"{h['avg_views']:,.0f}" for h in hook_sorted],
                textposition="outside",
            )
        )
        fig_hook.update_layout(
            yaxis_title="평균 조회수",
            **CHART_LAYOUT,
        )
        st.plotly_chart(fig_hook, use_container_width=True)

        # ── 레이더 차트 ──────────────────────────────────────
        if len(hook_sorted) >= 3:
            st.subheader("훅 패턴 다차원 비교")

            categories = ["조회수", "좋아요", "CTR", "시청시간"]

            fig_radar = go.Figure()
            for i, h in enumerate(hook_sorted[:5]):
                max_views = max(d["avg_views"] for d in hook_sorted) or 1
                max_likes = max(d["avg_likes"] for d in hook_sorted) or 1
                max_ctr = max(d["avg_ctr"] for d in hook_sorted) or 1
                max_watch = max(d["avg_watch_sec"] for d in hook_sorted) or 1

                fig_radar.add_trace(
                    go.Scatterpolar(
                        r=[
                            h["avg_views"] / max_views * 100,
                            h["avg_likes"] / max_likes * 100,
                            h["avg_ctr"] / max_ctr * 100,
                            h["avg_watch_sec"] / max_watch * 100,
                        ],
                        theta=categories,
                        fill="toself",
                        name=h["hook_pattern"],
                        line_color=COLORS["channels"][i % len(COLORS["channels"])],
                    )
                )

            fig_radar.update_layout(
                polar=dict(
                    bgcolor="rgba(0,0,0,0)",
                    radialaxis=dict(visible=True, range=[0, 100]),
                ),
                showlegend=True,
                **{k: v for k, v in CHART_LAYOUT.items() if k != "height"},
                height=400,
            )
            st.plotly_chart(fig_radar, use_container_width=True)

        # ── 훅 패턴 상세 테이블 ──────────────────────────────
        st.subheader("훅 패턴 상세 데이터")
        hook_table = []
        for h in hook_sorted:
            hook_table.append(
                {
                    "훅 패턴": h["hook_pattern"],
                    "사용 횟수": h["count"],
                    "평균 조회수": f"{h['avg_views']:,.0f}",
                    "평균 좋아요": f"{h['avg_likes']:,.0f}",
                    "평균 CTR": f"{h['avg_ctr']:.1f}%",
                    "평균 시청시간": f"{h['avg_watch_sec']:.1f}초",
                }
            )
        st.dataframe(hook_table, use_container_width=True)

        # 추천
        best_hook = hook_sorted[0]
        st.success(
            f"🎯 **최고 성과 훅 패턴**: `{best_hook['hook_pattern']}` "
            f"— 평균 {best_hook['avg_views']:,.0f}회 조회, "
            f"{best_hook['count']}회 사용"
        )
