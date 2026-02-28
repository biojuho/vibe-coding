import sys
import shlex
from pathlib import Path

# execution/ 모듈 import를 위한 경로 설정
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import streamlit as st

try:
    from execution.scheduler_engine import (
        add_task,
        delete_task,
        get_scheduler_kpis,
        get_logs,
        init_db,
        list_tasks,
        run_task,
        toggle_task,
    )
    _MODULE_OK = True
except ImportError as e:
    _MODULE_OK = False
    _MODULE_ERR = str(e)

st.set_page_config(page_title="Scheduler - Joolife", page_icon="📅", layout="wide")

if not _MODULE_OK:
    st.error(f"스케줄러 모듈을 불러올 수 없습니다: {_MODULE_ERR}")
    st.info("실행: `pip install croniter` 후 앱을 재시작하세요.")
    st.stop()

init_db()

st.title("📅 Scheduler Dashboard")
st.caption("Task scheduling & automation management")

# ── KPI ──
kpi = get_scheduler_kpis(days=7)
k1, k2, k3, k4 = st.columns(4)
with k1:
    st.metric("Runs (7d)", kpi["total_runs"])
with k2:
    st.metric("Success Rate", f"{kpi['scheduler_success_rate']:.2f}%")
with k3:
    st.metric("Backlog", kpi["scheduler_backlog"])
with k4:
    st.metric("Successful Runs", kpi["successful_runs"])

st.divider()

# ── Add Task ──
with st.expander("Add New Task", expanded=False):
    with st.form("add_task_form"):
        col_a, col_b = st.columns(2)
        with col_a:
            name = st.text_input("Task Name", placeholder="Daily Backup")
            executable = st.text_input("Executable", placeholder="python")
            args_text = st.text_input("Arguments", placeholder="scripts/backup_data.py --with-env")
        with col_b:
            cwd = st.text_input("Working Directory", value=".")
            cron = st.text_input("Cron Expression", placeholder="0 9 * * *")
            timeout_sec = st.number_input("Timeout (sec)", min_value=10, max_value=3600, value=300, step=10)
            st.caption("Format: min hour day month weekday")
        submitted = st.form_submit_button("Add Task", type="primary")
        if submitted and name and executable and cron:
            try:
                parsed_args = shlex.split(args_text, posix=False) if args_text else []
                tid = add_task(name, executable, parsed_args, cwd, cron, timeout_sec=int(timeout_sec))
                st.success(f"Task #{tid} '{name}' created.")
                st.rerun()
            except Exception as e:
                st.error(f"Failed: {e}")

st.divider()

# ── Task List ──
st.subheader("Scheduled Tasks")
tasks = list_tasks()

if not tasks:
    st.info("No tasks scheduled yet. Add one above.")
else:
    for task in tasks:
        col1, col2, col3, col4 = st.columns([3, 2, 2, 2])
        with col1:
            status_icon = "🟢" if task.enabled else "⚪"
            st.markdown(f"{status_icon} **{task.name}**")
            st.caption(f"`{task.command}` | cron: `{task.cron_expression}`")
        with col2:
            st.caption(f"Last: {task.last_run or 'Never'}")
            st.caption(f"Next: {task.next_run or 'N/A'}")
            st.caption(f"Failure Count: {task.failure_count} | Timeout: {task.timeout_sec}s")
        with col3:
            if st.button(
                "Disable" if task.enabled else "Enable",
                key=f"toggle_{task.id}",
            ):
                toggle_task(task.id, not task.enabled)
                st.rerun()
            if st.button("Run Now", key=f"run_{task.id}"):
                with st.spinner(f"Running {task.name}..."):
                    log = run_task(task.id)
                if log.exit_code == 0:
                    st.success("Completed (exit code: 0)")
                else:
                    st.error(f"Failed (exit code: {log.exit_code})")
                st.rerun()
        with col4:
            if st.button("Delete", key=f"del_{task.id}"):
                delete_task(task.id)
                st.rerun()

st.divider()

# ── Logs ──
st.subheader("Execution Logs")
task_filter = st.selectbox(
    "Filter by task",
    options=[None] + [t.id for t in tasks],
    format_func=lambda x: "All Tasks" if x is None else next(
        (t.name for t in tasks if t.id == x), str(x)
    ),
)
logs = get_logs(task_id=task_filter, limit=30)

if not logs:
    st.info("No logs yet.")
else:
    for log in logs:
        status = "✅" if log.exit_code == 0 else "❌"
        with st.expander(
            f"{status} {log.task_name} — {log.started_at}", expanded=False
        ):
            st.markdown(f"**Exit code:** {log.exit_code}")
            st.markdown(f"**Duration:** {log.duration_ms} ms")
            st.markdown(f"**Trigger:** {log.trigger_type}")
            if log.error_type:
                st.markdown(f"**Error Type:** `{log.error_type}`")
            if log.stdout:
                st.code(log.stdout, language="text")
            if log.stderr:
                st.error(log.stderr)
