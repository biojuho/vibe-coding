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
        get_attention_queue,
        get_recent_failure_summary,
        get_scheduler_ops_summary,
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

try:
    from execution.telegram_notifier import get_delivery_status_summary
    _TG_OK = True
except ImportError:
    _TG_OK = False

st.set_page_config(page_title="Scheduler - Joolife", page_icon="📅", layout="wide")

if not _MODULE_OK:
    st.error(f"스케줄러 모듈을 불러올 수 없습니다: {_MODULE_ERR}")
    st.info("실행: `pip install croniter` 후 앱을 재시작하세요.")
    st.stop()

init_db()


def _ops_badge(status: str) -> str:
    colors = {
        "healthy": "#28a745",
        "warning": "#fd7e14",
        "critical": "#dc3545",
        "setup_required": "#6f42c1",
    }
    labels = {
        "healthy": "Healthy",
        "warning": "Warning",
        "critical": "Critical",
        "setup_required": "Setup Required",
    }
    color = colors.get(status, "#6c757d")
    label = labels.get(status, status)
    return (
        f"<span style='background:{color};color:white;padding:2px 8px;"
        f"border-radius:10px;font-size:0.75rem'>{label}</span>"
    )


st.title("📅 Scheduler Dashboard")
st.caption("Task scheduling & automation management")

# ── KPI ──
ops_summary = get_scheduler_ops_summary()
if ops_summary["status"] == "critical":
    st.error(ops_summary["next_action"])
elif ops_summary["status"] == "warning":
    st.warning(ops_summary["next_action"])
elif ops_summary["status"] == "setup_required":
    st.info(ops_summary["next_action"])

st.subheader("Worker Status")
worker_cols = st.columns([1.2, 1.2, 1.2, 2.4])
with worker_cols[0]:
    st.markdown(_ops_badge(ops_summary["status"]), unsafe_allow_html=True)
with worker_cols[1]:
    st.caption("Last heartbeat")
    st.write(ops_summary["last_heartbeat"] or "Never")
with worker_cols[2]:
    st.caption("Seconds since")
    st.write(
        "-"
        if ops_summary["seconds_since_heartbeat"] is None
        else str(ops_summary["seconds_since_heartbeat"])
    )
with worker_cols[3]:
    st.caption("Next action")
    st.write(ops_summary["next_action"])

if ops_summary.get("note"):
    st.caption(f"Worker note: {ops_summary['note']}")

st.subheader("Recent Failures")
failure_items = get_recent_failure_summary(limit=6)
if not failure_items:
    st.info("No recent scheduler failures.")
else:
    for item in failure_items:
        with st.container(border=True):
            cols = st.columns([2.2, 1.2, 1.2, 2.4])
            with cols[0]:
                st.markdown(f"**{item['name']}**")
                st.caption(f"Error: `{item['last_error_type'] or 'unknown'}`")
            with cols[1]:
                st.caption("Recent 24h")
                st.write(str(item["recent_failures"]))
            with cols[2]:
                st.caption("Consecutive")
                st.write(str(item["failure_count"]))
            with cols[3]:
                st.caption("Next action")
                st.write(item["next_action"])
            if item.get("last_failed_at"):
                st.caption(f"Last failed: {item['last_failed_at']}")
            if item.get("last_stderr"):
                st.caption(f"stderr: {item['last_stderr'][:160]}")

st.subheader("Attention Queue")
attention_items = get_attention_queue(limit=6)
if not attention_items:
    st.info("No attention items.")
else:
    for item in attention_items:
        with st.container(border=True):
            st.markdown(f"**{item['name']}**")
            st.caption(
                f"reason: {', '.join(item['reasons'])} | "
                f"failure_count: {item['failure_count']} | "
                f"next_run: {item['next_run'] or 'N/A'}"
            )
            st.caption(f"next action: {item['next_action']}")

st.subheader("Telegram Status")
if not _TG_OK:
    st.info("Telegram notifier module not available.")
else:
    telegram_summary = get_delivery_status_summary()
    tg_cols = st.columns([1.2, 1.6, 1.6, 2.4])
    with tg_cols[0]:
        st.markdown(_ops_badge(telegram_summary["status"]), unsafe_allow_html=True)
    with tg_cols[1]:
        st.caption("Last success")
        st.write(telegram_summary["last_success_at"] or "Never")
    with tg_cols[2]:
        st.caption("Last failure")
        st.write(telegram_summary["last_failure_at"] or "None")
    with tg_cols[3]:
        st.caption("Next action")
        st.write(telegram_summary["next_action"])
    if telegram_summary.get("last_error"):
        st.caption(f"last error: {telegram_summary['last_error']}")
    if telegram_summary.get("last_message_preview"):
        st.caption(f"last message: {telegram_summary['last_message_preview']}")

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
