import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import streamlit as st

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

st.set_page_config(page_title="Notion Tasks - Joolife", page_icon="📋", layout="wide")

if not _MODULE_OK:
    st.error(f"Notion 모듈을 불러올 수 없습니다: {_MODULE_ERR}")
    st.stop()

st.title("📋 Notion Tasks")
st.caption("Notion task database management")

if not is_configured():
    st.warning(
        "Notion API not configured. Add `NOTION_API_KEY` and `NOTION_TASK_DATABASE_ID` to your `.env` file."
    )
    st.code(
        "NOTION_API_KEY=ntn_your_key_here\nNOTION_TASK_DATABASE_ID=your_database_id",
        language="text",
    )
    st.stop()

# 데이터 미리 로드 (상태 옵션 계산용)
all_tasks = list_tasks()
default_statuses = ["To Do", "In Progress", "Done"]
status_columns = [s for s in default_statuses if any(t.get("status") == s for t in all_tasks)]
extra_statuses = []
for task in all_tasks:
    st_name = (task.get("status") or "").strip()
    if st_name and st_name not in default_statuses and st_name not in extra_statuses:
        extra_statuses.append(st_name)
if not status_columns:
    status_columns = default_statuses.copy()
status_columns.extend(extra_statuses)

# ── Add Task ──
with st.expander("Add New Task", expanded=False):
    with st.form("add_notion_task"):
        title = st.text_input("Task Title")
        col_s, col_d = st.columns(2)
        with col_s:
            status = st.selectbox("Status", status_columns)
        with col_d:
            due = st.date_input("Due Date (optional)", value=None)
        if st.form_submit_button("Create Task", type="primary"):
            if title:
                due_str = due.isoformat() if due else None
                page_id = create_task(title, status, due_str)
                if page_id:
                    st.success("Task created!")
                    st.rerun()
                else:
                    st.error("Failed to create task.")

st.divider()

# ── Kanban View ──
if not all_tasks:
    st.info("No tasks found. Create one above or check your Notion database configuration.")
    st.stop()

cols = st.columns(len(status_columns))

for i, status in enumerate(status_columns):
    with cols[i]:
        st.subheader(f"{'📌' if status == 'To Do' else '🔄' if status == 'In Progress' else '✅'} {status}")
        filtered = [t for t in all_tasks if t["status"] == status]
        st.caption(f"{len(filtered)} task(s)")

        for task in filtered:
            with st.container():
                st.markdown(f"**{task['title']}**")
                if task.get("due_date"):
                    st.caption(f"Due: {task['due_date']}")

                # 상태 이동 버튼
                move_options = [s for s in status_columns if s != status]
                if move_options:
                    btn_cols = st.columns(len(move_options))
                    for j, new_status in enumerate(move_options):
                        with btn_cols[j]:
                            label = f"→ {new_status}"
                            if st.button(label, key=f"move_{task['id']}_{new_status}"):
                                if update_task_status(task["id"], new_status):
                                    st.rerun()
                else:
                    st.caption("No alternate statuses configured.")

                if task.get("url"):
                    st.markdown(f"[Open in Notion]({task['url']})")
                st.divider()
