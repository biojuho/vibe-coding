import os
import subprocess
import sys
import time
from pathlib import Path

import psutil
import streamlit as st

from execution.process_manager import ProcessManager, TrackedProcess

st.set_page_config(page_title="Joolife Hub", page_icon="?㎛", layout="wide")

# -- Process Manager 珥덇린??--
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
    h1 {
        background: linear-gradient(90deg, #fff, #a5b4fc);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-weight: 800;
    }
    .stButton > button {
        background: linear-gradient(92deg, #4f46e5 0%, #7c3aed 100%);
        color: white;
        border: none;
        border-radius: 8px;
        padding: 0.6rem 1.2rem;
        font-weight: 600;
        letter-spacing: 0.5px;
        width: 100%;
        transition: all 0.2s ease;
    }
    .stButton > button:hover {
        opacity: 0.9;
        transform: scale(1.02);
        box-shadow: 0 0 20px rgba(124, 58, 237, 0.4);
    }
    .stButton > button:active {
        transform: scale(0.98);
    }
    [data-testid="stMetricValue"] {
        font-size: 1.8rem;
        color: #a5b4fc;
    }
    hr {
        border-color: rgba(255, 255, 255, 0.1);
    }
    .process-bar {
        background: rgba(79, 70, 229, 0.15);
        border: 1px solid rgba(79, 70, 229, 0.3);
        border-radius: 8px;
        padding: 8px 16px;
        margin-bottom: 4px;
    }
</style>
""",
    unsafe_allow_html=True,
)

st.title("?㎛ Joolife Hub")
st.caption("짤 2026 Joolife - Enterprise Command Center")

# ?? System Metrics ??
col_sys1, col_sys2, col_sys3 = st.columns(3)
with col_sys1:
    cpu = psutil.cpu_percent()
    st.metric("CPU Load", f"{cpu}%", delta_color="inverse")
    st.progress(cpu / 100)
with col_sys2:
    mem = psutil.virtual_memory().percent
    st.metric("Memory Usage", f"{mem}%", delta_color="inverse")
    st.progress(mem / 100)
with col_sys3:
    disk = psutil.disk_usage(os.path.splitdrive(os.path.abspath(__file__))[0] + os.sep).percent
    st.metric("Disk Usage", f"{disk}%", delta_color="inverse")
    st.progress(disk / 100)

st.divider()


# ?? Launch Helper ?? (Process Monitor蹂대떎 癒쇱? ?뺤쓽?섏뼱????
def _resolve_target_directory(working_directory: str) -> Path | None:
    project_root = Path(__file__).resolve().parent
    target_directory = (project_root / working_directory).resolve()
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


# ?? Project Registry ??
PROJECTS = [
    # Row 1: Core Projects
    {"key": "agent", "icon": "?쨼", "name": "Personal Agent", "desc": "Your AI assistant.",
     "cmd": "streamlit run app.py", "cwd": "personal-agent", "port": 8501, "primary": True,
     "category": "Core Projects"},
    {"key": "game", "icon": "?렜", "name": "Word Chain", "desc": "AI word game.",
     "cmd": "python main.py", "cwd": "word-chain-pygame",
     "category": "Core Projects"},
    {"key": "dash", "icon": "?뱤", "name": "Knowledge Dash", "desc": "Knowledge management.",
     "cmd": "npm run dev", "cwd": "knowledge-dashboard", "port": 3000,
     "category": "Core Projects"},
    # Row 2: More Projects
    {"key": "hanwoo", "icon": "?맢", "name": "Hanwoo Dash", "desc": "Cattle management system.",
     "cmd": "npm run dev", "cwd": "hanwoo-dashboard", "port": 3001, "primary": True, "terminal": True,
     "category": "Projects"},
    {"key": "profit", "icon": "?뮥", "name": "Profit Gen", "desc": "Content generation CLI.",
     "cmd": "streamlit run app.py", "cwd": "profit-content-generator", "port": 8502,
     "category": "Projects"},
    {"key": "blind", "icon": "X", "name": "Blind to X", "desc": "Blind scraper & X draft.",
     "cmd": "python blind_scraper.py --trending", "cwd": "blind-to-x", "terminal": True,
     "category": "Projects"},
    # Row 3: Hub Tools
    {"key": "scheduler", "icon": "?뱟", "name": "Scheduler", "desc": "Task scheduling & automation.",
     "cmd": "streamlit run pages/scheduler_dashboard.py", "cwd": ".", "port": 8503,
     "category": "Hub Tools"},
    {"key": "improver", "icon": "?뵇", "name": "Code Improver", "desc": "Static code analysis tool.",
     "cmd": "python execution/code_improver.py . --format markdown", "cwd": ".", "terminal": True,
     "category": "Hub Tools"},
    {"key": "report", "icon": "?뱷", "name": "Daily Report", "desc": "Daily activity summary.",
     "cmd": "streamlit run pages/daily_report.py", "cwd": ".", "port": 8504,
     "category": "Hub Tools"},
    # Row 4: Data & Analytics
    {"key": "notion", "icon": "?뱥", "name": "Notion Tasks", "desc": "Notion task management.",
     "cmd": "streamlit run pages/notion_tasks.py", "cwd": ".", "port": 8505,
     "category": "Data & Analytics"},
    {"key": "finance", "icon": "?뮫", "name": "Finance", "desc": "Income & expense tracker.",
     "cmd": "streamlit run pages/finance_tracker.py", "cwd": ".", "port": 8506,
     "category": "Data & Analytics"},
    {"key": "github", "icon": "?릻", "name": "GitHub Dash", "desc": "GitHub activity & stats.",
     "cmd": "streamlit run pages/github_dashboard.py", "cwd": ".", "port": 8507,
     "category": "Data & Analytics"},
    # Row 5: Monitoring
    {"key": "api", "icon": "?뱻", "name": "API Monitor", "desc": "API usage & credit tracking.",
     "cmd": "streamlit run pages/api_monitor.py", "cwd": ".", "port": 8508,
     "category": "Monitoring"},
    {"key": "scheduler_worker", "icon": "?깍툘", "name": "Scheduler Worker", "desc": "Run due-task polling worker.",
     "cmd": "python execution/scheduler_worker.py --interval 30", "cwd": ".", "terminal": True,
     "category": "Monitoring"},
    # Row 6: Mini Games (1)
    {"key": "discord", "icon": "?쨼", "name": "Discord Bot", "desc": "二쇱궗?? 媛?꾨컮?꾨낫, ? ?섎늻湲?",
     "cmd": "python bot.py", "cwd": "discord-bot", "terminal": True,
     "category": "Mini Games"},
    {"key": "statcard", "icon": "?렣", "name": "Stat Card Maker", "desc": "RPG ?ㅽ꺈 移대뱶 ?대?吏 ?앹꽦.",
     "cmd": "streamlit run app.py", "cwd": "stat-card-maker", "port": 8509,
     "category": "Mini Games"},
    {"key": "roulette", "icon": "?렟", "name": "Champion Roulette", "desc": "諛쒕줈???& LoL 梨뷀뵾??猷곕젢.",
     "cmd": "npm run dev", "cwd": "champion-roulette", "port": 3100,
     "category": "Mini Games"},
    # Row 7: Mini Games (2)
    {"key": "escape", "icon": "?뵑", "name": "Escape Room", "desc": "?ъ씠踰꾪럱???댄궧 諛⑺깉異?",
     "cmd": "streamlit run app.py", "cwd": "escape-room", "port": 8510,
     "category": "Mini Games"},
    {"key": "esports", "icon": "?룇", "name": "E-Sports Alert", "desc": "寃쎄린 ?쇱젙 & 移댁슫?몃떎??",
     "cmd": "streamlit run app.py", "cwd": "esports-alert", "port": 8511,
     "category": "Mini Games"},
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
        rows.append(projects[start_index:start_index + row_size])
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
st.caption(
    f"Welcome back, **JooPark**. System Time: {time.strftime('%Y-%m-%d %H:%M:%S')}"
)
