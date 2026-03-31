from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path

WORKSPACE_ROOT = Path(__file__).resolve().parents[1]
if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT))

import psutil
import streamlit as st

from execution.process_manager import ProcessManager, TrackedProcess
from path_contract import REPO_ROOT

st.set_page_config(page_title="Joolife Hub", page_icon="🧭", layout="wide")

if "pm" not in st.session_state:
    st.session_state.pm = ProcessManager()

pm: ProcessManager = st.session_state.pm

st.markdown(
    """
<style>
    .stApp {
        background: linear-gradient(135deg, #0f0c29 0%, #302b63 50%, #24243e 100%);
        color: #e0e0e0;
    }
    .card {
        background: rgba(255, 255, 255, 0.03);
        border-radius: 16px;
        padding: 24px;
        backdrop-filter: blur(12px);
        -webkit-backdrop-filter: blur(12px);
        border: 1px solid rgba(255, 255, 255, 0.08);
        box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.3);
        transition: transform 0.2s ease, box-shadow 0.2s ease;
        height: 100%;
    }
    .card:hover {
        transform: translateY(-5px);
        box-shadow: 0 12px 40px 0 rgba(0, 0, 0, 0.4);
        border: 1px solid rgba(255, 255, 255, 0.2);
    }
    h1, h2, h3 {
        font-family: 'Inter', 'Helvetica Neue', sans-serif;
        color: #ffffff;
        letter-spacing: -0.5px;
    }
    .stButton > button {
        background: linear-gradient(92deg, #4f46e5 0%, #7c3aed 100%);
        color: white;
        border: none;
        border-radius: 8px;
        padding: 0.6rem 1.2rem;
        font-weight: 600;
        width: 100%;
    }
</style>
""",
    unsafe_allow_html=True,
)

st.title("🧭 Joolife Hub")
st.caption("Canonical launcher for workspace apps and projects")

col_sys1, col_sys2, col_sys3 = st.columns(3)
with col_sys1:
    cpu = psutil.cpu_percent()
    st.metric("CPU Load", f"{cpu}%", delta_color="inverse")
    st.progress(cpu / 100)
with col_sys2:
    memory = psutil.virtual_memory().percent
    st.metric("Memory Usage", f"{memory}%", delta_color="inverse")
    st.progress(memory / 100)
with col_sys3:
    disk = psutil.disk_usage(os.path.splitdrive(os.path.abspath(__file__))[0] + os.sep).percent
    st.metric("Disk Usage", f"{disk}%", delta_color="inverse")
    st.progress(disk / 100)

st.divider()


def _resolve_target_directory(working_directory: str) -> Path | None:
    target_directory = (REPO_ROOT / working_directory).resolve()
    if not target_directory.exists():
        st.error(f"Path not found: {target_directory}")
        return None
    return target_directory


def _normalize_terminal_command(command: str) -> str:
    if command.startswith("python"):
        return f"{sys.executable} {command[7:]}"
    return command


def _build_terminal_launch(command: str) -> tuple[list[str], bool]:
    if os.name != "nt":
        st.warning("New terminal not supported on non-Windows yet.")
        return command.split(), False
    terminal_command = _normalize_terminal_command(command)
    return ["cmd", "/c", "start", "cmd", "/k", terminal_command], True


def _build_inline_launch(command: str) -> list[str]:
    if command.startswith("streamlit"):
        streamlit_args = command.split()[1:]
        return [sys.executable, "-m", "streamlit", *streamlit_args]
    if command.startswith("python"):
        python_args = command.split()[1:]
        return [sys.executable, *python_args]

    command_parts = command.split()
    if os.name == "nt" and command_parts and command_parts[0] == "npm":
        command_parts[0] = "npm.cmd"
    return command_parts


def _build_launch_command(command: str, open_in_new_terminal: bool) -> tuple[list[str], bool]:
    if open_in_new_terminal:
        return _build_terminal_launch(command)
    return _build_inline_launch(command), False


def _register_launched_process(
    process_id: int,
    display_name: str,
    command: str,
    working_directory: str,
    port: int = None,
) -> None:
    pm.register(
        pid=process_id,
        name=display_name,
        command=command,
        cwd=working_directory,
        port=port,
    )


def _notify_launch_status(process_id: int, display_name: str) -> None:
    time.sleep(1)
    if psutil.pid_exists(process_id):
        st.toast(f"Running: {display_name} (PID {process_id})")
        return
    st.warning(f"Process exited immediately: {display_name}")


def launch_process(
    command: str,
    working_directory: str,
    process_name: str = "",
    open_in_new_terminal: bool = False,
    port: int = None,
) -> None:
    target_directory = _resolve_target_directory(working_directory)
    if target_directory is None:
        return

    launch_command, use_shell = _build_launch_command(command, open_in_new_terminal)
    display_name = process_name or command

    try:
        launched_process = subprocess.Popen(
            launch_command,
            cwd=str(target_directory),
            shell=use_shell,
        )
        _register_launched_process(
            process_id=launched_process.pid,
            display_name=display_name,
            command=command,
            working_directory=working_directory,
            port=port,
        )
        _notify_launch_status(
            process_id=launched_process.pid,
            display_name=display_name,
        )
    except Exception as error:
        st.error(f"Failed to launch: {error}")


def _render_process_summary(process: TrackedProcess) -> None:
    st.markdown(f"**{process.name}**")
    st.caption(f"PID {process.pid} | {process.launched_at}")


def _render_process_status(process: TrackedProcess) -> None:
    st.markdown("Running")
    if process.port:
        st.markdown(f"[localhost:{process.port}](http://localhost:{process.port})")


def _handle_stop_button(process_id: int) -> None:
    if st.button("Stop", key=f"kill_{process_id}"):
        pm.kill_process(process_id)
        st.rerun()


def _handle_restart_button(process: TrackedProcess) -> None:
    if st.button("Restart", key=f"restart_{process.pid}"):
        pm.kill_process(process.pid)
        launch_process(
            process.command,
            working_directory=process.cwd,
            process_name=process.name,
            port=process.port,
        )
        st.rerun()


def _render_process_row(process: TrackedProcess) -> None:
    summary_column, status_column, stop_column, restart_column = st.columns([4, 2, 1, 1])
    with summary_column:
        _render_process_summary(process)
    with status_column:
        _render_process_status(process)
    with stop_column:
        _handle_stop_button(process.pid)
    with restart_column:
        _handle_restart_button(process)


def _render_process_monitor() -> None:
    running_processes = pm.get_alive_processes()
    if not running_processes:
        return

    with st.expander(f"Running Processes ({len(running_processes)})", expanded=False):
        for process in running_processes:
            _render_process_row(process)

        st.divider()
        if st.button("Stop All Processes", type="primary", key="kill_all"):
            killed_count = pm.kill_all()
            st.toast(f"Stopped {killed_count} process(es).")
            st.rerun()


_render_process_monitor()

st.divider()

PROJECTS = [
    {
        "key": "shorts",
        "icon": "🎬",
        "name": "Shorts Manager",
        "desc": "YouTube Shorts automation workspace.",
        "cmd": "streamlit run workspace/execution/pages/shorts_manager.py",
        "cwd": ".",
        "port": 8512,
        "primary": True,
        "category": "Workspace Apps",
    },
    {
        "key": "api",
        "icon": "📡",
        "name": "API Monitor",
        "desc": "API usage and credit tracking dashboard.",
        "cmd": "streamlit run workspace/execution/pages/api_monitor.py",
        "cwd": ".",
        "port": 8508,
        "category": "Workspace Apps",
    },
    {
        "key": "qaqc",
        "icon": "✅",
        "name": "QAQC Status",
        "desc": "Unified QA/QC status and history viewer.",
        "cmd": "streamlit run workspace/execution/pages/qaqc_status.py",
        "cwd": ".",
        "port": 8515,
        "category": "Workspace Apps",
    },
    {
        "key": "daily_report",
        "icon": "📝",
        "name": "Daily Report",
        "desc": "Daily activity summary and export tools.",
        "cmd": "streamlit run workspace/execution/pages/daily_report.py",
        "cwd": ".",
        "port": 8504,
        "category": "Workspace Apps",
    },
    {
        "key": "github",
        "icon": "🐙",
        "name": "GitHub Dash",
        "desc": "Repository activity and status metrics.",
        "cmd": "streamlit run workspace/execution/pages/github_dashboard.py",
        "cwd": ".",
        "port": 8507,
        "category": "Workspace Apps",
    },
    {
        "key": "hanwoo",
        "icon": "🐄",
        "name": "Hanwoo Dashboard",
        "desc": "Cattle management web dashboard.",
        "cmd": "npm run dev",
        "cwd": "projects/hanwoo-dashboard",
        "port": 3001,
        "terminal": True,
        "category": "Projects",
    },
    {
        "key": "knowledge",
        "icon": "🧠",
        "name": "Knowledge Dashboard",
        "desc": "Knowledge dashboard and QA/QC presentation layer.",
        "cmd": "npm run dev",
        "cwd": "projects/knowledge-dashboard",
        "port": 3000,
        "category": "Projects",
    },
    {
        "key": "blind",
        "icon": "X",
        "name": "Blind to X",
        "desc": "Blind scraper and X draft pipeline.",
        "cmd": "python main.py",
        "cwd": "projects/blind-to-x",
        "terminal": True,
        "category": "Projects",
    },
    {
        "key": "word_chain",
        "icon": "🎮",
        "name": "Word Chain",
        "desc": "React/Vite word chain project.",
        "cmd": "npm run dev",
        "cwd": "projects/word-chain",
        "port": 5173,
        "category": "Projects",
    },
    {
        "key": "suika",
        "icon": "🍉",
        "name": "Suika Game V2",
        "desc": "Frozen Vite game project.",
        "cmd": "npm run dev -- --port 5174",
        "cwd": "projects/suika-game-v2",
        "port": 5174,
        "category": "Projects",
    },
    {
        "key": "doctor",
        "icon": "🩺",
        "name": "Workspace Doctor",
        "desc": "Run environment and dependency checks.",
        "cmd": "python workspace/scripts/doctor.py",
        "cwd": ".",
        "terminal": True,
        "category": "Operations",
    },
    {
        "key": "quality_gate",
        "icon": "🛡️",
        "name": "Quality Gate",
        "desc": "Run the root quality gate in a terminal.",
        "cmd": "python workspace/scripts/quality_gate.py",
        "cwd": ".",
        "terminal": True,
        "category": "Operations",
    },
    {
        "key": "scheduler_worker",
        "icon": "⚙️",
        "name": "Scheduler Worker",
        "desc": "Run the due-task polling worker.",
        "cmd": "python workspace/execution/scheduler_worker.py --interval 30",
        "cwd": ".",
        "terminal": True,
        "category": "Operations",
    },
    {
        "key": "health",
        "icon": "🏥",
        "name": "Health Check",
        "desc": "System health dashboard.",
        "cmd": "streamlit run workspace/execution/pages/health_check_dashboard.py",
        "cwd": ".",
        "port": 8513,
        "category": "Operations",
    },
    {
        "key": "debug_history",
        "icon": "🪲",
        "name": "Debug History",
        "desc": "Debug history and error pattern tracker.",
        "cmd": "streamlit run workspace/execution/pages/debug_history.py",
        "cwd": ".",
        "port": 8514,
        "category": "Operations",
    },
]


def render_card(project: dict) -> None:
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.header(f"{project['icon']} {project['name']}")
    st.markdown(project["desc"])
    button_options = {"type": "primary"} if project.get("primary") else {}
    if st.button("Launch", key=f"btn_{project['key']}", **button_options):
        launch_process(
            project["cmd"],
            working_directory=project["cwd"],
            process_name=project["name"],
            port=project.get("port"),
            open_in_new_terminal=project.get("terminal", False),
        )
    if project.get("port") and project["cmd"].startswith("npm"):
        st.markdown(f"[Open Localhost](http://localhost:{project['port']})")
    st.markdown("</div>", unsafe_allow_html=True)


def _group_projects_by_category(projects: list[dict]) -> dict[str, list[dict]]:
    grouped_projects: dict[str, list[dict]] = {}
    for project in projects:
        category_name = project["category"]
        grouped_projects.setdefault(category_name, []).append(project)
    return grouped_projects


def _project_rows(projects: list[dict], row_size: int = 3) -> list[list[dict]]:
    rows: list[list[dict]] = []
    for start_index in range(0, len(projects), row_size):
        rows.append(projects[start_index : start_index + row_size])
    return rows


def _render_project_category(category_name: str, projects: list[dict]) -> None:
    st.divider()
    st.subheader(category_name)
    for project_row in _project_rows(projects):
        row_columns = st.columns(3)
        for column_index, project in enumerate(project_row):
            with row_columns[column_index]:
                render_card(project)


def _render_project_registry(projects: list[dict]) -> None:
    projects_by_category = _group_projects_by_category(projects)
    for category_name, category_projects in projects_by_category.items():
        _render_project_category(category_name, category_projects)


_render_project_registry(PROJECTS)

st.divider()
st.caption(f"Workspace Root: {REPO_ROOT}")
