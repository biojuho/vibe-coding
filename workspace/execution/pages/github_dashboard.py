import re
import subprocess
import sys
from pathlib import Path

WORKSPACE_ROOT = Path(__file__).resolve().parents[2]
REPO_ROOT = WORKSPACE_ROOT.parent
if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT))

import streamlit as st  # noqa: E402

try:
    import plotly.express as px
    import plotly.graph_objects as go

    from execution.github_stats import (
        get_commit_heatmap_data,
        get_commits,
        get_language_stats,
        get_pr_stats,
        get_repos,
        get_user,
        is_configured,
    )

    _MODULE_OK = True
except ImportError as e:
    _MODULE_OK = False
    _MODULE_ERR = str(e)

PLOTLY_CHART_CONFIG = {"displayModeBar": False, "displaylogo": False, "responsive": True}
REQUIRED_ACTIONS = ("root-quality-gate", "active-project-matrix")


def _inject_mobile_touch_target_styles() -> None:
    st.markdown(
        """
        <style>
        @media (max-width: 640px) {
            div[data-testid="stToolbar"] button,
            div[data-testid="stToolbar"] a,
            div[data-testid="stToolbar"] [role="button"],
            button[data-testid="stBaseButton-headerNoPadding"],
            div[data-testid="stButton"] button,
            div[data-testid="stSelectbox"] [role="combobox"],
            div[data-testid="stSlider"] [role="slider"],
            div[data-testid="stExpander"] summary,
            a[data-testid="stPageLink-NavLink"],
            a[data-testid="stSidebarNavLink"],
            a[href],
            section[data-testid="stSidebar"] button {
                min-height: 44px !important;
                min-width: 44px !important;
            }
            div[data-testid="stSelectbox"] [role="combobox"],
            div[data-testid="stSlider"] [role="slider"] {
                align-items: center !important;
            }
            div[data-testid="stMarkdownContainer"],
            div[data-testid="stCaptionContainer"],
            div[data-testid="stAlert"] {
                overflow-wrap: anywhere;
                word-break: keep-all;
            }
            h1 {
                font-size: 2rem !important;
                line-height: 1.15 !important;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _render_plotly_chart(fig) -> None:
    st.plotly_chart(fig, width="stretch", config=PLOTLY_CHART_CONFIG)


def _run_git(args: list[str]) -> str:
    try:
        completed = subprocess.run(
            ["git", *args],
            cwd=REPO_ROOT,
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=10,
        )
    except (OSError, subprocess.SubprocessError):
        return ""
    return completed.stdout.strip() if completed.returncode == 0 else ""


def _parse_ahead_count(status_line: str) -> int:
    match = re.search(r"\bahead\s+(\d+)", status_line)
    return int(match.group(1)) if match else 0


def _local_release_status() -> dict[str, str | int]:
    status_line = _run_git(["status", "-sb"])
    head = _run_git(["rev-parse", "--short", "HEAD"]) or "unknown"
    branch = _run_git(["branch", "--show-current"]) or "unknown"
    ahead = _parse_ahead_count(status_line)
    return {"branch": branch, "head": head, "ahead": ahead, "status_line": status_line}


def _render_release_boundary() -> None:
    status = _local_release_status()
    st.subheader("릴리스 경계", anchor=False)
    rel_col1, rel_col2, rel_col3 = st.columns(3)
    with rel_col1:
        st.metric("현재 브랜치", status["branch"])
    with rel_col2:
        st.metric("현재 HEAD", status["head"])
    with rel_col3:
        st.metric("원격보다 앞선 커밋", status["ahead"])

    if int(status["ahead"] or 0) > 0:
        st.warning(
            "현재 HEAD는 origin에 아직 없어서 필수 GitHub Actions를 증명할 수 없습니다. "
            "명시적 승인 전 push하지 말고, 승인 후 root-quality-gate와 active-project-matrix를 확인하세요."
        )
    else:
        st.success("로컬 브랜치가 원격과 동기화되어 있습니다. 최신 Actions 결과를 확인하세요.")

    st.caption("필수 Actions: " + ", ".join(REQUIRED_ACTIONS))


st.set_page_config(page_title="GitHub 운영 - Joolife", page_icon="🔧", layout="wide")
_inject_mobile_touch_target_styles()

if not _MODULE_OK:
    st.error(f"GitHub 모듈을 불러올 수 없습니다: {_MODULE_ERR}")
    st.stop()

st.title("GitHub 운영 현황", anchor=False)
st.caption("현재 릴리스 경계, PR 흐름, 저장소 활동을 한 화면에서 확인합니다.")

_render_release_boundary()
st.divider()

if not is_configured():
    st.warning(
        "`GITHUB_PERSONAL_ACCESS_TOKEN`이 없어 원격 GitHub 활동을 불러올 수 없습니다. "
        "`infrastructure/.env`에 토큰을 추가하면 PR/커밋/저장소 지표가 표시됩니다."
    )
    st.stop()

user = get_user()
if user:
    col_avatar, col_info = st.columns([1, 3])
    with col_avatar:
        if user.get("avatar_url"):
            st.image(user["avatar_url"], width=120)
    with col_info:
        st.subheader(user.get("name") or user.get("login", ""))
        st.caption(f"@{user.get('login', '')}")
        if user.get("bio"):
            st.markdown(user["bio"])
        mc1, mc2, mc3 = st.columns(3)
        with mc1:
            st.metric("공개 저장소", user.get("public_repos", 0))
        with mc2:
            st.metric("팔로워", user.get("followers", 0))
        with mc3:
            st.metric("팔로잉", user.get("following", 0))

st.divider()

st.subheader("Pull Request 흐름")
pr_opt1, pr_opt2 = st.columns(2)
state_labels = {"all": "전체", "open": "열림", "closed": "닫힘"}
with pr_opt1:
    pr_state = st.selectbox(
        "PR 상태 범위",
        ["all", "open", "closed"],
        index=0,
        format_func=lambda value: state_labels[value],
    )
with pr_opt2:
    pr_days = st.slider("PR 조회 기간(일)", min_value=7, max_value=180, value=30)
with st.spinner("PR 데이터를 불러오는 중..."):
    prs = get_pr_stats(state=pr_state, days=pr_days)

pr_col1, pr_col2, pr_col3, pr_col4 = st.columns(4)
with pr_col1:
    st.metric("전체 PR", prs["total"])
with pr_col2:
    st.metric("열림", prs["open"])
with pr_col3:
    st.metric("머지됨", prs["merged"])
with pr_col4:
    st.metric("닫힘", prs["closed"])

st.divider()

col_lang, col_heatmap = st.columns(2)

with col_lang:
    st.subheader("저장소 언어 분포")
    with st.spinner("언어 지표를 불러오는 중..."):
        langs = get_language_stats()
    if langs:
        fig = px.pie(
            values=list(langs.values()),
            names=list(langs.keys()),
            title="언어별 저장소",
        )
        fig.update_layout(
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            font_color="#1f2933",
        )
        _render_plotly_chart(fig)
    else:
        st.info("표시할 언어 지표가 없습니다.")

with col_heatmap:
    st.subheader("커밋 활동(30일)")
    with st.spinner("커밋 활동을 불러오는 중..."):
        heatmap = get_commit_heatmap_data(days=30)
    if heatmap:
        dates = sorted(heatmap.keys())
        counts = [heatmap[d] for d in dates]
        fig = go.Figure(go.Bar(x=dates, y=counts, marker_color="#2563eb"))
        fig.update_layout(
            title="일별 커밋",
            xaxis_title="날짜",
            yaxis_title="커밋",
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            font_color="#1f2933",
        )
        _render_plotly_chart(fig)
    else:
        st.info("이 기간에 표시할 커밋 데이터가 없습니다.")

st.divider()

st.subheader("최근 커밋")
days = st.slider("커밋 조회 기간(일)", min_value=7, max_value=90, value=30)
with st.spinner("최근 커밋을 불러오는 중..."):
    commits = get_commits(days)

if commits:
    for c in commits[:30]:
        cc1, cc2 = st.columns([1, 5])
        with cc1:
            st.code(c["sha"])
        with cc2:
            st.markdown(f"**{c['repo']}** - {c['message']}")
            st.caption(c["date"][:10] if c["date"] else "")
else:
    st.info("표시할 최근 커밋이 없습니다.")

st.divider()
with st.expander("전체 저장소"):
    repos = get_repos()
    for r in repos:
        rc1, rc2, rc3 = st.columns([4, 1, 1])
        with rc1:
            private_badge = "[private]" if r["private"] else "[public]"
            st.markdown(f"{private_badge} **{r['name']}**")
            if r.get("description"):
                st.caption(r["description"])
        with rc2:
            st.caption(r.get("language") or "미지정")
        with rc3:
            st.caption(f"stars {r.get('stars', 0)}")
