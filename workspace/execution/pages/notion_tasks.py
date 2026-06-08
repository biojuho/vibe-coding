import sys
from pathlib import Path

WORKSPACE_ROOT = Path(__file__).resolve().parents[2]
if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT))

import streamlit as st  # noqa: E402

try:
    from execution.notion_client import (
        create_task,
        is_configured,
        list_tasks,
        update_task_status,
    )

    _MODULE_OK = True
except ImportError as e:
    _MODULE_OK = False
    _MODULE_ERR = str(e)


STATUS_LABELS = {
    "To Do": "할 일",
    "In Progress": "진행 중",
    "Done": "완료",
}

MOBILE_TOUCH_TARGET_CSS = """
<style>
@media (max-width: 640px) {
    button,
    button[kind],
    a[href],
    input,
    textarea,
    div[data-testid="stButton"] button,
    div[data-testid="stFormSubmitButton"] button,
    div[data-testid="stHeader"] button,
    div[data-testid="stToolbar"] button,
    div[data-testid="stToolbar"] a,
    div[data-testid="stHeaderActionElements"] button,
    div[data-testid="stHeaderActionElements"] a,
    div[data-baseweb="select"],
    div[data-baseweb="select"] > div,
    div[data-baseweb="input"],
    div[data-baseweb="input"] > div,
    div[data-baseweb="input"] input {
        min-height: 44px !important;
        min-width: 44px !important;
    }

    input,
    textarea,
    div[data-baseweb="select"] > div,
    div[data-baseweb="input"] > div {
        align-items: center !important;
        font-size: 1rem !important;
    }

    a[href^="#"],
    div[data-testid="stHeadingWithActionElements"] a {
        display: inline-flex !important;
        align-items: center !important;
        justify-content: center !important;
        min-height: 44px !important;
        min-width: 44px !important;
    }

    div[data-testid="stMarkdownContainer"],
    div[data-testid="stCodeBlock"],
    p,
    span {
        overflow-wrap: anywhere;
    }
}
</style>
"""


def _display_status(status: str) -> str:
    return STATUS_LABELS.get(status, status or "상태 없음")


def _status_icon(status: str) -> str:
    if status == "Done":
        return "✅"
    if status == "In Progress":
        return "⏳"
    return "📋"


def _inject_mobile_touch_target_styles() -> None:
    st.markdown(MOBILE_TOUCH_TARGET_CSS, unsafe_allow_html=True)


st.set_page_config(page_title="Notion 작업 - Joolife", page_icon="✅", layout="wide")

if not _MODULE_OK:
    st.error(f"Notion 작업 모듈을 불러올 수 없습니다: {_MODULE_ERR}")
    st.stop()

_inject_mobile_touch_target_styles()

st.title("Notion 작업 보드", anchor=False)
st.caption("Notion 데이터베이스의 작업을 상태별로 확인하고 필요한 후속 조치를 바로 정리합니다.")

if not is_configured():
    st.warning("Notion 작업 데이터베이스 연결이 아직 설정되지 않았습니다.")
    st.markdown(
        """
1. Notion 개발자 포털에서 내부 연결 또는 개인 액세스 토큰을 준비합니다.
2. 작업 데이터베이스 페이지에서 해당 연결을 추가해 읽기/쓰기 권한을 공유합니다.
3. 로컬 `.env`에 아래 값을 채운 뒤 이 페이지를 새로고침합니다.
"""
    )
    st.code(
        "NOTION_API_KEY=ntn_your_key_here\nNOTION_TASK_DATABASE_ID=your_database_or_data_source_id",
        language="text",
        wrap_lines=True,
    )
    st.stop()


all_tasks = list_tasks()
default_statuses = ["To Do", "In Progress", "Done"]
status_columns = [s for s in default_statuses if any(t.get("status") == s for t in all_tasks)]
extra_statuses = []
for task in all_tasks:
    status_name = (task.get("status") or "").strip()
    if status_name and status_name not in default_statuses and status_name not in extra_statuses:
        extra_statuses.append(status_name)
if not status_columns:
    status_columns = default_statuses.copy()
status_columns.extend(extra_statuses)

with st.expander("새 작업 추가", expanded=False):
    with st.form("add_notion_task"):
        title = st.text_input("작업 제목")
        col_s, col_d = st.columns(2)
        with col_s:
            status = st.selectbox("상태", status_columns, format_func=_display_status)
        with col_d:
            due = st.date_input("마감일(선택)", value=None)
        if st.form_submit_button("작업 생성", type="primary"):
            if title:
                due_str = due.isoformat() if due else None
                page_id = create_task(title, status, due_str)
                if page_id:
                    st.success("작업을 생성했습니다.")
                    st.rerun()
                else:
                    st.error("작업을 생성하지 못했습니다. Notion 연결과 데이터베이스 권한을 확인하세요.")

st.divider()

if not all_tasks:
    st.info("작업이 없습니다. 위에서 새 작업을 만들거나 Notion 데이터베이스 공유 설정을 확인하세요.")
    st.stop()

cols = st.columns(len(status_columns))

for i, status in enumerate(status_columns):
    with cols[i]:
        st.subheader(f"{_status_icon(status)} {_display_status(status)}", anchor=False)
        filtered = [t for t in all_tasks if t["status"] == status]
        st.caption(f"{len(filtered)}개 작업")

        for task in filtered:
            with st.container():
                st.markdown(f"**{task['title']}**")
                if task.get("due_date"):
                    st.caption(f"마감: {task['due_date']}")

                move_options = [s for s in status_columns if s != status]
                if move_options:
                    btn_cols = st.columns(len(move_options))
                    for j, new_status in enumerate(move_options):
                        with btn_cols[j]:
                            label = f"→ {_display_status(new_status)}"
                            if st.button(label, key=f"move_{task['id']}_{new_status}"):
                                if update_task_status(task["id"], new_status):
                                    st.rerun()
                else:
                    st.caption("이동할 다른 상태가 없습니다.")

                if task.get("url"):
                    st.markdown(f"[Notion에서 열기]({task['url']})")
                st.divider()
