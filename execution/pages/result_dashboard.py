"""
📊 콘텐츠 결과 관리 대시보드

철학: "수동 업로드 + 자동 결과 관리"
- 사용자가 직접 YouTube/X에 업로드
- 이 대시보드에서 URL만 등록
- YouTube: API Key로 공개 통계 자동 수집 (계정 리스크 0%)
- X/Threads: 수동 성과 입력

실행: streamlit run execution/pages/result_dashboard.py
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
    from execution.result_tracker_db import (
        PLATFORMS,
        add_content,
        collect_youtube_stats,
        delete_content,
        get_all,
        get_channel_summary,
        get_daily_trend,
        get_platform_summary,
        get_stats_history,
        get_top_content,
        init_db,
        update_manual_stats,
    )
    _MODULE_OK = True
except ImportError as e:
    _MODULE_ERR = str(e)

st.set_page_config(page_title="콘텐츠 결과 관리", page_icon="📊", layout="wide")

if not _MODULE_OK:
    st.error(f"모듈 로드 실패: {_MODULE_ERR}")
    st.stop()

init_db()

# ── 공통 스타일 ──────────────────────────────────────────────
CHART_LAYOUT = dict(
    plot_bgcolor="rgba(0,0,0,0)",
    paper_bgcolor="rgba(0,0,0,0)",
    font=dict(color="#e0e0e0", family="Pretendard, sans-serif"),
    margin=dict(l=20, r=20, t=40, b=20),
    height=320,
)

COLORS = {
    "youtube":  "#ff0000",
    "x":        "#1da1f2",
    "threads":  "#000000",
    "blog":     "#03c75a",
    "success":  "#4ade80",
    "danger":   "#f87171",
    "warning":  "#fbbf24",
    "info":     "#60a5fa",
    "primary":  "#7c3aed",
    "channels": ["#f472b6", "#38bdf8", "#facc15", "#4ade80", "#fb923c"],
}

# ===========================================================================
# 사이드바: 통계 수집 + 요약
# ===========================================================================
with st.sidebar:
    st.header("⚙️ 도구")

    if st.button("🔄 YouTube 통계 수집", use_container_width=True, type="primary"):
        with st.spinner("YouTube API에서 통계 수집 중..."):
            result = collect_youtube_stats()
        if "error" in result:
            st.error(result["error"])
        else:
            st.success(f"✅ {result.get('updated', 0)}개 업데이트 완료")

    st.divider()
    st.caption(
        "📌 **수동 업로드 + 자동 결과 관리**\n\n"
        "YouTube/X에 직접 업로드 후\n"
        "이 대시보드에서 URL만 등록하세요.\n\n"
        "YouTube 통계는 API Key로\n"
        "자동 수집됩니다. (계정 리스크 0%)"
    )

    # 간단 요약
    all_items = get_all()
    if all_items:
        st.divider()
        st.metric("총 등록 콘텐츠", len(all_items))
        total_views = sum(it.get("views", 0) or 0 for it in all_items)
        st.metric("총 조회수", f"{total_views:,}")

# ===========================================================================
# 탭 구성
# ===========================================================================
tab_register, tab_overview, tab_detail, tab_trend = st.tabs([
    "➕ 콘텐츠 등록", "📊 성과 개요", "📋 상세 관리", "📈 추이 분석"
])


# ===========================================================================
# TAB 1: 콘텐츠 등록
# ===========================================================================
with tab_register:
    st.header("➕ 콘텐츠 등록")
    st.caption("YouTube/X에 업로드한 콘텐츠의 URL을 등록하세요")

    with st.form("add_content_form", clear_on_submit=True):
        col1, col2 = st.columns(2)

        with col1:
            platform = st.selectbox(
                "플랫폼",
                options=list(PLATFORMS.keys()),
                format_func=lambda x: f"{PLATFORMS[x]['emoji']} {PLATFORMS[x]['display']}",
            )
            url = st.text_input(
                "URL",
                placeholder="https://youtu.be/... 또는 https://x.com/...",
            )
            title = st.text_input(
                "제목",
                placeholder="영상/게시물 제목",
            )

        with col2:
            channel_options = ["AI/기술", "심리학", "역사/고고학", "우주/천문학", "의학/건강", "기타"]
            channel = st.selectbox("채널", options=[""] + channel_options)
            tags = st.text_input("태그 (쉼표 구분)", placeholder="AI, GPT, 기술")
            published_at = st.date_input("게시일")
            memo = st.text_area("메모", placeholder="선택 사항", height=68)

        submitted = st.form_submit_button("📝 등록", type="primary", use_container_width=True)

        if submitted:
            if not url or not title:
                st.error("URL과 제목은 필수입니다.")
            else:
                row_id = add_content(
                    platform=platform,
                    url=url,
                    title=title,
                    channel=channel,
                    tags=tags,
                    memo=memo,
                    published_at=str(published_at),
                )
                st.success(f"✅ 등록 완료! (ID: {row_id})")
                st.rerun()

    # 최근 등록 목록
    st.divider()
    st.subheader("최근 등록 콘텐츠")
    recent = get_all()[:10]
    if recent:
        for item in recent:
            emoji = PLATFORMS.get(item["platform"], {}).get("emoji", "📄")
            views = item.get("views", 0) or 0
            likes = item.get("likes", 0) or 0

            with st.container():
                cols = st.columns([0.5, 3, 1, 1, 1])
                cols[0].markdown(f"### {emoji}")
                link = f"[{item['title'][:45]}]({item['url']})" if item["url"] else item["title"][:45]
                cols[1].markdown(f"**{link}**\n\n`{item.get('channel', '')}` · {item.get('published_at', '')}")
                cols[2].metric("조회수", f"{views:,}")
                cols[3].metric("좋아요", f"{likes:,}")
                stats_label = "자동" if PLATFORMS.get(item["platform"], {}).get("auto_stats") else "수동"
                cols[4].caption(f"수집: {stats_label}\n\n{item.get('stats_updated', '미수집')[:10]}")
    else:
        st.info("아직 등록된 콘텐츠가 없습니다. 위 폼에서 첫 콘텐츠를 등록하세요! 🎉")


# ===========================================================================
# TAB 2: 성과 개요
# ===========================================================================
with tab_overview:
    st.header("📊 성과 개요")

    all_items = get_all()

    if not all_items:
        st.info("콘텐츠를 등록하면 이 대시보드가 활성화됩니다.")
    else:
        # ── 전체 KPI ─────────────────────────────────────────
        total_count = len(all_items)
        total_views = sum(it.get("views", 0) or 0 for it in all_items)
        total_likes = sum(it.get("likes", 0) or 0 for it in all_items)
        total_comments = sum(it.get("comments", 0) or 0 for it in all_items)
        avg_views = total_views / max(total_count, 1)
        like_rate = total_likes / max(total_views, 1) * 100
        engagement = (total_likes + total_comments) / max(total_views, 1) * 100

        k1, k2, k3, k4, k5, k6 = st.columns(6)
        k1.metric("총 콘텐츠", total_count)
        k2.metric("총 조회수", f"{total_views:,}")
        k3.metric("평균 조회수", f"{avg_views:,.0f}")
        k4.metric("총 좋아요", f"{total_likes:,}")
        k5.metric("좋아요율", f"{like_rate:.1f}%")
        k6.metric("참여율", f"{engagement:.2f}%")

        st.divider()

        # ── 플랫폼별 성과 ────────────────────────────────────
        platform_data = get_platform_summary()
        if platform_data:
            st.subheader("플랫폼별 성과")
            col_pie, col_bar = st.columns(2)

            with col_pie:
                fig_pie = px.pie(
                    names=[PLATFORMS.get(p["platform"], {}).get("display", p["platform"]) for p in platform_data],
                    values=[p["count"] for p in platform_data],
                    title="플랫폼별 콘텐츠 분포",
                    color_discrete_sequence=[
                        COLORS.get(p["platform"], "#888") for p in platform_data
                    ],
                )
                fig_pie.update_layout(**CHART_LAYOUT)
                st.plotly_chart(fig_pie, use_container_width=True)

            with col_bar:
                fig_bar = go.Figure()
                fig_bar.add_trace(go.Bar(
                    x=[PLATFORMS.get(p["platform"], {}).get("display", p["platform"]) for p in platform_data],
                    y=[p["total_views"] for p in platform_data],
                    marker_color=[COLORS.get(p["platform"], "#888") for p in platform_data],
                    text=[f"{p['total_views']:,}" for p in platform_data],
                    textposition="outside",
                ))
                fig_bar.update_layout(title="플랫폼별 총 조회수", yaxis_title="조회수", **CHART_LAYOUT)
                st.plotly_chart(fig_bar, use_container_width=True)

        st.divider()

        # ── 채널별 성과 ──────────────────────────────────────
        channel_data = get_channel_summary()
        if channel_data:
            st.subheader("채널별 성과")

            fig_ch = go.Figure()
            fig_ch.add_trace(go.Bar(
                x=[c["channel"] for c in channel_data],
                y=[c["avg_views"] for c in channel_data],
                marker_color=COLORS["channels"][:len(channel_data)],
                text=[f"{c['avg_views']:,.0f}" for c in channel_data],
                textposition="outside",
            ))
            fig_ch.update_layout(title="채널별 평균 조회수", yaxis_title="평균 조회수", **CHART_LAYOUT)
            st.plotly_chart(fig_ch, use_container_width=True)

            # 채널 테이블
            ch_table = []
            for c in channel_data:
                ch_table.append({
                    "채널": c["channel"],
                    "플랫폼": PLATFORMS.get(c["platform"], {}).get("display", c["platform"]),
                    "콘텐츠 수": c["count"],
                    "총 조회수": f"{c['total_views']:,}",
                    "평균 조회수": f"{c['avg_views']:,.0f}",
                    "총 좋아요": f"{c['total_likes']:,}",
                })
            st.dataframe(ch_table, use_container_width=True)

        st.divider()

        # ── TOP 10 콘텐츠 ────────────────────────────────────
        top = get_top_content(10)
        if top:
            st.subheader("🏆 조회수 TOP 10")
            for i, item in enumerate(top, 1):
                emoji = PLATFORMS.get(item["platform"], {}).get("emoji", "📄")
                views = item.get("views", 0) or 0
                likes = item.get("likes", 0) or 0
                comments = item.get("comments", 0) or 0

                with st.container():
                    cols = st.columns([0.4, 0.4, 3, 1, 1, 1])
                    cols[0].markdown(f"**#{i}**")
                    cols[1].markdown(emoji)
                    link = f"[{item['title'][:35]}]({item['url']})" if item["url"] else item["title"][:35]
                    cols[2].markdown(f"**{link}**\n\n`{item.get('channel', '')}`")
                    cols[3].metric("조회수", f"{views:,}")
                    cols[4].metric("좋아요", f"{likes:,}")
                    cols[5].metric("댓글", f"{comments:,}")


# ===========================================================================
# TAB 3: 상세 관리
# ===========================================================================
with tab_detail:
    st.header("📋 콘텐츠 상세 관리")
    st.caption("X/Threads 통계 수동 입력 및 개별 콘텐츠 관리")

    all_items = get_all()

    if not all_items:
        st.info("등록된 콘텐츠가 없습니다.")
    else:
        # 플랫폼 필터
        filter_platform = st.selectbox(
            "플랫폼 필터",
            ["전체"] + list(PLATFORMS.keys()),
            format_func=lambda x: "전체" if x == "전체" else f"{PLATFORMS[x]['emoji']} {PLATFORMS[x]['display']}",
            key="detail_filter",
        )

        filtered = all_items
        if filter_platform != "전체":
            filtered = [it for it in all_items if it["platform"] == filter_platform]

        for item in filtered:
            emoji = PLATFORMS.get(item["platform"], {}).get("emoji", "📄")
            auto_stats = PLATFORMS.get(item["platform"], {}).get("auto_stats", False)

            with st.expander(
                f"{emoji} [{item['id']}] {item['title'][:50]} — "
                f"{item.get('views', 0) or 0:,}회 조회",
                expanded=False,
            ):
                # 기본 정보
                info_cols = st.columns(3)
                info_cols[0].markdown(f"**플랫폼**: {PLATFORMS.get(item['platform'], {}).get('display', item['platform'])}")
                info_cols[1].markdown(f"**채널**: {item.get('channel', '-')}")
                info_cols[2].markdown(f"**게시일**: {item.get('published_at', '-')}")

                if item.get("url"):
                    st.markdown(f"🔗 [원본 링크]({item['url']})")

                st.divider()

                if auto_stats:
                    # YouTube — 자동 수집 결과 표시
                    st.caption("✅ YouTube 통계는 사이드바의 '통계 수집' 버튼으로 자동 업데이트됩니다")
                    mc = st.columns(4)
                    mc[0].metric("조회수", f"{item.get('views', 0) or 0:,}")
                    mc[1].metric("좋아요", f"{item.get('likes', 0) or 0:,}")
                    mc[2].metric("댓글", f"{item.get('comments', 0) or 0:,}")
                    mc[3].metric("마지막 수집", item.get("stats_updated", "미수집")[:16])
                else:
                    # X/Threads/Blog — 수동 입력 폼
                    st.caption("📝 수동 입력: 플랫폼 앱에서 확인한 통계를 입력하세요")

                    with st.form(f"manual_stats_{item['id']}"):
                        sc = st.columns(3)
                        new_views = sc[0].number_input("조회수/노출", value=item.get("impressions", 0) or 0, min_value=0, key=f"v_{item['id']}")
                        new_likes = sc[1].number_input("좋아요", value=item.get("likes", 0) or 0, min_value=0, key=f"l_{item['id']}")
                        new_comments = sc[2].number_input("댓글", value=item.get("comments", 0) or 0, min_value=0, key=f"c_{item['id']}")

                        sc2 = st.columns(3)
                        new_rt = sc2[0].number_input("리트윗/공유", value=item.get("retweets", 0) or 0, min_value=0, key=f"rt_{item['id']}")
                        new_bm = sc2[1].number_input("북마크/저장", value=item.get("bookmarks", 0) or 0, min_value=0, key=f"bm_{item['id']}")

                        if st.form_submit_button("💾 통계 저장"):
                            update_manual_stats(
                                item["id"],
                                impressions=new_views,
                                likes=new_likes,
                                comments=new_comments,
                                retweets=new_rt,
                                bookmarks=new_bm,
                            )
                            st.success("저장 완료!")
                            st.rerun()

                # 통계 히스토리
                history = get_stats_history(item["id"])
                if history and len(history) > 1:
                    st.divider()
                    st.caption("📈 통계 변화 추이")
                    fig_h = go.Figure()
                    fig_h.add_trace(go.Scatter(
                        x=[h["collected_at"] for h in history],
                        y=[h["views"] for h in history],
                        mode="lines+markers",
                        name="조회수",
                        line=dict(color=COLORS["youtube"]),
                    ))
                    fig_h.add_trace(go.Scatter(
                        x=[h["collected_at"] for h in history],
                        y=[h["likes"] for h in history],
                        mode="lines+markers",
                        name="좋아요",
                        line=dict(color=COLORS["info"]),
                    ))
                    fig_h.update_layout(**CHART_LAYOUT, height=200)
                    st.plotly_chart(fig_h, use_container_width=True)

                # [QA 수정] 삭제 확인 절차 추가
                confirm = st.checkbox(f"삭제 확인", key=f"confirm_del_{item['id']}")
                if confirm:
                    if st.button(f"🗑️ 정말 삭제", key=f"del_{item['id']}", type="secondary"):
                        delete_content(item["id"])
                        st.success("삭제 완료")
                        st.rerun()


# ===========================================================================
# TAB 4: 추이 분석
# ===========================================================================
with tab_trend:
    st.header("📈 추이 분석")

    days = st.slider("분석 기간 (일)", 7, 90, 30, key="trend_days")
    trend = get_daily_trend(days)

    if not trend:
        st.info("데이터가 축적되면 추이 분석이 활성화됩니다.")
    else:
        # ── 일별 등록 + 조회수 ────────────────────────────────
        col_count, col_views = st.columns(2)

        with col_count:
            st.subheader("일별 콘텐츠 등록")
            fig_cnt = go.Figure()
            fig_cnt.add_trace(go.Bar(
                x=[t["day"] for t in trend],
                y=[t["count"] for t in trend],
                marker_color=COLORS["primary"],
            ))
            fig_cnt.update_layout(**CHART_LAYOUT)
            st.plotly_chart(fig_cnt, use_container_width=True)

        with col_views:
            st.subheader("일별 조회수")
            fig_views = go.Figure()
            fig_views.add_trace(go.Scatter(
                x=[t["day"] for t in trend],
                y=[t["total_views"] for t in trend],
                mode="lines+markers",
                fill="tozeroy",
                line=dict(color=COLORS["youtube"], width=2),
                fillcolor="rgba(255,0,0,0.1)",
            ))
            fig_views.update_layout(**CHART_LAYOUT)
            st.plotly_chart(fig_views, use_container_width=True)

        st.divider()

        # ── 누적 추이 ────────────────────────────────────────
        st.subheader("누적 조회수 추이")
        cumulative = []
        running_total = 0
        for t in trend:
            running_total += t["total_views"]
            cumulative.append({"day": t["day"], "cumulative": running_total})

        fig_cum = go.Figure()
        fig_cum.add_trace(go.Scatter(
            x=[c["day"] for c in cumulative],
            y=[c["cumulative"] for c in cumulative],
            mode="lines",
            fill="tozeroy",
            line=dict(color=COLORS["success"], width=3),
            fillcolor="rgba(74,222,128,0.15)",
        ))
        fig_cum.update_layout(**CHART_LAYOUT, height=280)
        st.plotly_chart(fig_cum, use_container_width=True)

        # ── 성장률 ───────────────────────────────────────────
        if len(trend) >= 2:
            recent_week = trend[-7:] if len(trend) >= 7 else trend
            prev_week = trend[-14:-7] if len(trend) >= 14 else trend[:len(trend)//2]

            recent_views = sum(t["total_views"] for t in recent_week)
            prev_views = sum(t["total_views"] for t in prev_week) if prev_week else 0

            if prev_views > 0:
                growth = (recent_views - prev_views) / prev_views * 100
                st.metric(
                    "주간 성장률",
                    f"{growth:+.1f}%",
                    delta=f"이번 주 {recent_views:,}회 vs 지난 주 {prev_views:,}회",
                )
