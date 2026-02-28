import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import streamlit as st

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

st.set_page_config(page_title="GitHub - Joolife", page_icon="🐙", layout="wide")

if not _MODULE_OK:
    st.error(f"GitHub 모듈을 불러올 수 없습니다: {_MODULE_ERR}")
    st.stop()

st.title("🐙 GitHub Dashboard")
st.caption("GitHub activity & repository stats")

if not is_configured():
    st.warning(
        "GitHub token not configured. Add `GITHUB_PERSONAL_ACCESS_TOKEN` to `infrastructure/.env`."
    )
    st.stop()

# ── Profile ──
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
            st.metric("Repos", user.get("public_repos", 0))
        with mc2:
            st.metric("Followers", user.get("followers", 0))
        with mc3:
            st.metric("Following", user.get("following", 0))

st.divider()

# ── PR Stats ──
st.subheader("Pull Request Stats")
pr_opt1, pr_opt2 = st.columns(2)
with pr_opt1:
    pr_state = st.selectbox("PR State Scope", ["all", "open", "closed"], index=0)
with pr_opt2:
    pr_days = st.slider("PR Lookback (days)", min_value=7, max_value=180, value=30)
with st.spinner("Loading PR data..."):
    prs = get_pr_stats(state=pr_state, days=pr_days)

pr_col1, pr_col2, pr_col3, pr_col4 = st.columns(4)
with pr_col1:
    st.metric("Total PRs", prs["total"])
with pr_col2:
    st.metric("Open", prs["open"])
with pr_col3:
    st.metric("Merged", prs["merged"])
with pr_col4:
    st.metric("Closed", prs["closed"])

st.divider()

# ── Language Distribution ──
col_lang, col_heatmap = st.columns(2)

with col_lang:
    st.subheader("Language Distribution")
    with st.spinner("Loading language stats..."):
        langs = get_language_stats()
    if langs:
        fig = px.pie(
            values=list(langs.values()),
            names=list(langs.keys()),
            title="Repositories by Language",
        )
        fig.update_layout(
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            font_color="#e0e0e0",
        )
        st.plotly_chart(fig, width="stretch")
    else:
        st.info("No language data available.")

with col_heatmap:
    st.subheader("Commit Activity (30 days)")
    with st.spinner("Loading commit heatmap..."):
        heatmap = get_commit_heatmap_data(days=30)
    if heatmap:
        dates = sorted(heatmap.keys())
        counts = [heatmap[d] for d in dates]
        fig = go.Figure(
            go.Bar(x=dates, y=counts, marker_color="#7c3aed")
        )
        fig.update_layout(
            title="Daily Commits",
            xaxis_title="Date",
            yaxis_title="Commits",
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            font_color="#e0e0e0",
        )
        st.plotly_chart(fig, width="stretch")
    else:
        st.info("No commit data for this period.")

st.divider()

# ── Recent Commits ──
st.subheader("Recent Commits")
days = st.slider("Days", min_value=7, max_value=90, value=30)
with st.spinner("Loading commits..."):
    commits = get_commits(days)

if commits:
    for c in commits[:30]:
        cc1, cc2 = st.columns([1, 5])
        with cc1:
            st.code(c["sha"])
        with cc2:
            st.markdown(f"**{c['repo']}** — {c['message']}")
            st.caption(c["date"][:10] if c["date"] else "")
else:
    st.info("No commits found.")

# ── Repositories ──
st.divider()
with st.expander("All Repositories"):
    repos = get_repos()
    for r in repos:
        rc1, rc2, rc3 = st.columns([4, 1, 1])
        with rc1:
            private_badge = "🔒" if r["private"] else "🌐"
            st.markdown(f"{private_badge} **{r['name']}**")
            if r.get("description"):
                st.caption(r["description"])
        with rc2:
            st.caption(r.get("language") or "—")
        with rc3:
            st.caption(f"⭐ {r.get('stars', 0)}")
