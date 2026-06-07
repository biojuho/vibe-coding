import json
import sys
from datetime import date
from pathlib import Path

WORKSPACE_ROOT = Path(__file__).resolve().parents[2]
if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT))

import streamlit as st  # noqa: E402

try:
    from execution.daily_report import REPORT_DIR, generate_report

    _MODULE_OK = True
except ImportError as e:
    _MODULE_OK = False
    _MODULE_ERR = str(e)

PLOTLY_CHART_CONFIG = {"displayModeBar": False, "displaylogo": False, "responsive": True}


def _inject_mobile_touch_target_styles() -> None:
    st.markdown(
        """
        <style>
        @media (max-width: 640px) {
            div[data-testid="stToolbar"] button,
            div[data-testid="stToolbar"] a,
            div[data-testid="stToolbar"] [role="button"],
            button[data-testid="stBaseButton-header"],
            button[data-testid="stMainMenuButton"],
            button[data-testid="stBaseButton-headerNoPadding"],
            div[data-testid="stHeaderActionElements"] a,
            a[href^="#"],
            div[data-testid="stDateInput"] button,
            div[data-testid="stDateInput"] input,
            div[data-testid="stButton"] button {
                min-height: 44px !important;
                min-width: 44px !important;
                align-items: center !important;
                justify-content: center !important;
            }
            div[data-testid="stMarkdownContainer"],
            div[data-testid="stCaptionContainer"] {
                overflow-wrap: anywhere;
                word-break: keep-all;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _render_plotly_chart(fig: object) -> None:
    st.plotly_chart(fig, width="stretch", config=PLOTLY_CHART_CONFIG)


def _render_summary_metrics(summary: dict) -> None:
    metric_specs = [
        ("총 커밋", summary["total_commits"]),
        ("활성 저장소", summary["active_repos"]),
        ("수정 파일", summary["files_modified"]),
        ("자동 실행", summary["scheduler_tasks_run"]),
        ("LLM 호출", summary.get("llm_bridge_calls", 0)),
        ("브리지 수리", summary.get("llm_bridge_repairs", 0)),
        ("브리지 폴백", summary.get("llm_bridge_fallbacks", 0)),
        ("API 알림", summary.get("api_alerts", 0)),
    ]

    for row_start in range(0, len(metric_specs), 4):
        columns = st.columns(4)
        for column, (label, value) in zip(columns, metric_specs[row_start : row_start + 4], strict=False):
            with column:
                st.metric(label, value)


st.set_page_config(page_title="일일 리포트 - Joolife", page_icon="📝", layout="wide")
_inject_mobile_touch_target_styles()

if not _MODULE_OK:
    st.error(f"일일 리포트 모듈을 불러올 수 없습니다: {_MODULE_ERR}")
    st.stop()

st.title("📝 일일 운영 리포트")
st.caption("커밋, 파일 변경, 자동 실행, LLM 브리지, API 알림을 하루 단위로 점검")

# ── Date Picker ──
col_date, col_btn = st.columns([2, 1])
with col_date:
    target = st.date_input("리포트 날짜", value=date.today())
with col_btn:
    st.markdown("")
    st.markdown("")
    generate_btn = st.button("리포트 생성", type="primary")

# 기존 리포트 로드 또는 새로 생성
report_path = REPORT_DIR / f"daily_{target.isoformat()}.json"
report = None

if generate_btn:
    with st.spinner("활동 데이터를 수집하는 중..."):
        report = generate_report(target)
    st.success("리포트가 생성되었습니다.")
elif report_path.exists():
    report = json.loads(report_path.read_text(encoding="utf-8"))

if report is None:
    st.info("선택한 날짜의 리포트가 없습니다. `리포트 생성`을 눌러 새로 만드세요.")
    st.stop()

# ── Summary Metrics ──
st.divider()
s = report["summary"]
_render_summary_metrics(s)

# ── Git Activity ──
st.divider()
st.subheader("Git 활동")

by_repo = report["git_activity"].get("by_repo", {})
if by_repo:
    import plotly.express as px

    fig = px.bar(
        x=list(by_repo.keys()),
        y=list(by_repo.values()),
        labels={"x": "저장소", "y": "커밋"},
        title="저장소별 커밋",
    )
    fig.update_layout(
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font_color="#1f2933",
    )
    _render_plotly_chart(fig)

commits = report["git_activity"].get("commits", [])
if commits:
    st.markdown("**최근 커밋**")
    for c in commits[:20]:
        st.markdown(f"- `{c['repo']}` **{c['hash']}** {c['message']}")
else:
    st.info("이 날짜의 커밋이 없습니다.")

# ── Scheduler Logs ──
sched_logs = report.get("scheduler_logs", [])
if sched_logs:
    st.divider()
    st.subheader("자동 실행 이력")
    for log in sched_logs:
        icon = "✅" if log.get("exit_code") == 0 else "❌"
        st.markdown(f"{icon} **{log['task_name']}** — {log['started_at']}")

bridge = report.get("llm_bridge", {})
if bridge.get("total_calls", 0):
    st.divider()
    st.subheader("LLM 브리지")
    bridge_col1, bridge_col2, bridge_col3, bridge_col4 = st.columns(4)
    with bridge_col1:
        st.metric("Shadow 호출", bridge.get("shadow_calls", 0))
    with bridge_col2:
        st.metric("Enforce 호출", bridge.get("enforce_calls", 0))
    with bridge_col3:
        st.metric("평균 언어 점수", bridge.get("average_language_score") or 0)
    with bridge_col4:
        st.metric("Provider 수", len(bridge.get("by_provider", {})))

    reason_codes = bridge.get("top_reason_codes", [])
    if reason_codes:
        st.markdown("**상위 사유 코드**")
        for item in reason_codes[:10]:
            st.markdown(f"- `{item['reason_code']}` {item['count']}회")

api_alerts = report.get("api_alerts", {})
if api_alerts.get("alert_count", 0):
    st.divider()
    st.subheader("API 알림")
    for alert in api_alerts.get("alerts", [])[:10]:
        alert_type = alert.get("type") or "unknown"
        detail = alert.get("detail") or alert.get("provider") or "세부 정보 없음"
        st.warning(f"`{alert_type}` {detail}")
