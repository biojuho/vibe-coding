from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

WORKSPACE_ROOT = Path(__file__).resolve().parents[1]
if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT))

import psutil
import streamlit as st

from execution.process_manager import ProcessManager, TrackedProcess
from path_contract import REPO_ROOT

st.set_page_config(page_title="작업 허브 - Joolife", page_icon="🧭", layout="wide")

if "pm" not in st.session_state:
    st.session_state.pm = ProcessManager()

pm: ProcessManager = st.session_state.pm

st.markdown(
    """
<style>
    .stApp {
        background: #f7f8f5;
        color: #1b1f1c;
    }
    .hub-intro {
        border-left: 4px solid #2f6f4e;
        padding: 0.75rem 1rem;
        background: #ffffff;
        border-radius: 8px;
        color: #28352d;
        margin-bottom: 1rem;
    }
    .hub-card-line {
        margin: 0.15rem 0;
        color: #37423a;
        overflow-wrap: anywhere;
        word-break: keep-all;
    }
    .hub-chip {
        display: inline-flex;
        align-items: center;
        min-height: 28px;
        padding: 0.1rem 0.55rem;
        margin: 0 0.25rem 0.35rem 0;
        border-radius: 999px;
        background: #e8f1ea;
        color: #214a34;
        font-size: 0.82rem;
        font-weight: 650;
    }
    .hub-chip.warn {
        background: #fff0d8;
        color: #6d4312;
    }
    .hub-chip.blocked {
        background: #fbe2df;
        color: #7a261f;
    }
    h1, h2, h3 {
        font-family: 'Inter', 'Helvetica Neue', sans-serif;
        color: #18231d;
        letter-spacing: 0;
    }
    .stButton > button {
        background: #214a34;
        color: #ffffff;
        border: 1px solid #214a34;
        border-radius: 8px;
        padding: 0.6rem 1.2rem;
        font-weight: 600;
        width: 100%;
        min-height: 44px;
    }
    div[data-testid="stLinkButton"] a,
    a[data-testid="stPageLink-NavLink"],
    a[data-testid="stSidebarNavLink"],
    div[data-testid="stHeaderActionElements"] a,
    button[data-testid="stBaseButton-headerNoPadding"] {
        min-height: 44px;
        min-width: 44px;
        align-items: center;
    }
    @media (max-width: 640px) {
        h1 {
            font-size: 2rem !important;
            line-height: 1.15 !important;
        }
        div[data-testid="stToolbar"] button,
        div[data-testid="stToolbar"] a,
        div[data-testid="stToolbar"] [role="button"],
        div[data-testid="stButton"] button,
        div[data-testid="stLinkButton"] a,
        a[data-testid="stPageLink-NavLink"],
        a[data-testid="stSidebarNavLink"],
        div[data-testid="stHeaderActionElements"] a,
        button[data-testid="stBaseButton-headerNoPadding"] {
            min-height: 44px !important;
            min-width: 44px !important;
        }
        a[data-testid="stSidebarNavLink"] {
            align-items: center !important;
            justify-content: flex-start !important;
            width: 100% !important;
        }
        div[data-testid="stHeaderActionElements"] a {
            align-items: center !important;
            justify-content: center !important;
        }
        div[data-testid="stMetric"] {
            min-width: 0 !important;
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

st.title("🧭 Joolife 작업 허브")
st.caption("바로 쓸 수 있는 결과물과 검증 상태를 기준으로 작업 화면을 고르는 운영 진입점")

_QC_SNAPSHOT_PATH = REPO_ROOT / ".tmp" / "project_qc_runner_latest.json"
_QC_PROJECT_KEYS = {
    "shorts": "shorts-maker-v2",
    "qaqc": None,
    "daily_report": None,
    "api": None,
    "github": None,
    "hanwoo": "hanwoo-dashboard",
    "knowledge": "knowledge-dashboard",
    "blind": "blind-to-x",
}


def load_qc_snapshot(path: Path = _QC_SNAPSHOT_PATH) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
    return data if isinstance(data, dict) else None


def _parse_qc_timestamp(timestamp: str | None) -> datetime | None:
    if not timestamp:
        return None
    try:
        parsed = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _format_qc_timestamp(snapshot: dict[str, Any] | None) -> str:
    parsed = _parse_qc_timestamp(str(snapshot.get("timestamp") or "")) if snapshot else None
    if parsed is None:
        return "증거 없음"
    return parsed.astimezone().strftime("%Y-%m-%d %H:%M")


def _count_passed_projects(snapshot: dict[str, Any] | None) -> tuple[int, int]:
    projects = snapshot.get("projects", {}) if snapshot else {}
    if not isinstance(projects, dict):
        return (0, 0)
    passed_count = sum(
        1
        for project in projects.values()
        if isinstance(project, dict) and str(project.get("status", "")).upper() == "PASS"
    )
    return passed_count, len(projects)


def _safe_int(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _qc_project_summary(snapshot: dict[str, Any] | None, project_key: str) -> str | None:
    qc_project_key = _QC_PROJECT_KEYS.get(project_key)
    if not qc_project_key or not snapshot:
        return None

    projects = snapshot.get("projects", {})
    if not isinstance(projects, dict):
        return None

    project_result = projects.get(qc_project_key)
    if not isinstance(project_result, dict):
        return None

    status = str(project_result.get("status") or "UNKNOWN").upper()
    passed = _safe_int(project_result.get("passed"))
    failed = _safe_int(project_result.get("failed"))
    skipped = _safe_int(project_result.get("skipped"))
    coverage = str(project_result.get("coverage") or "").strip()
    coverage_text = f" · {coverage}" if coverage else ""
    return f"{status} · {passed} passed · {failed} failed · {skipped} skipped{coverage_text}"


def _project_evidence_line(project: dict[str, Any], snapshot: dict[str, Any] | None) -> str:
    qc_summary = _qc_project_summary(snapshot, project["key"])
    return qc_summary or project["quality_signal"]


def _render_quality_overview(snapshot: dict[str, Any] | None) -> None:
    st.markdown(
        """
        <div class="hub-intro">
        좋은 출력 기준: 바로 복사·저장·공유할 수 있을 만큼 구체적이고, 현재 검증 증거와 다음 행동이 같이 보여야 합니다.
        </div>
        """,
        unsafe_allow_html=True,
    )
    passed_count, project_count = _count_passed_projects(snapshot)
    status = str(snapshot.get("status") or "unknown").upper() if snapshot else "NO DATA"

    overview_columns = st.columns(4)
    metric_specs = [
        ("최근 QC", "통과" if status in {"PASSED", "PASS"} else status),
        ("프로젝트 PASS", f"{passed_count}/{project_count}" if project_count else "증거 없음"),
        ("마지막 증거", _format_qc_timestamp(snapshot)),
        ("남은 경계", "배포 승인 + Hanwoo T-251"),
    ]
    for column, (label, value) in zip(overview_columns, metric_specs, strict=False):
        with column:
            st.metric(label, value)


qc_snapshot = load_qc_snapshot()
_render_quality_overview(qc_snapshot)

col_sys1, col_sys2, col_sys3 = st.columns(3)
with col_sys1:
    cpu = psutil.cpu_percent()
    st.metric("CPU", f"{cpu}%", delta_color="inverse")
    st.progress(cpu / 100)
with col_sys2:
    memory = psutil.virtual_memory().percent
    st.metric("메모리", f"{memory}%", delta_color="inverse")
    st.progress(memory / 100)
with col_sys3:
    disk = psutil.disk_usage(os.path.splitdrive(os.path.abspath(__file__))[0] + os.sep).percent
    st.metric("디스크", f"{disk}%", delta_color="inverse")
    st.progress(disk / 100)

st.divider()


def _resolve_target_directory(working_directory: str) -> Path | None:
    target_directory = (REPO_ROOT / working_directory).resolve()
    if not target_directory.exists():
        st.error(f"경로를 찾을 수 없습니다: {target_directory}")
        return None
    return target_directory


def _has_streamlit_port_arg(command_parts: list[str]) -> bool:
    return any(part == "--server.port" or part.startswith("--server.port=") for part in command_parts)


def _append_streamlit_port(command_parts: list[str], port: int | None) -> list[str]:
    if port is None or not command_parts or command_parts[0] != "streamlit":
        return command_parts
    if _has_streamlit_port_arg(command_parts):
        return command_parts
    return [*command_parts, "--server.port", str(port)]


def _normalize_terminal_command(command: str, port: int | None = None) -> str:
    command_parts = _append_streamlit_port(command.split(), port)
    command = " ".join(command_parts)
    if command.startswith("python"):
        return f"{sys.executable} {command[7:]}"
    return command


def _build_terminal_launch(command: str, port: int | None = None) -> tuple[list[str], bool]:
    if os.name != "nt":
        st.warning("새 터미널 실행은 아직 Windows에서만 지원합니다.")
        return _append_streamlit_port(command.split(), port), False
    terminal_command = _normalize_terminal_command(command, port=port)
    return ["cmd", "/c", "start", "cmd", "/k", terminal_command], True


def _build_inline_launch(command: str, port: int | None = None) -> list[str]:
    if command.startswith("streamlit"):
        streamlit_args = _append_streamlit_port(command.split(), port)[1:]
        return [sys.executable, "-m", "streamlit", *streamlit_args]
    if command.startswith("python"):
        python_args = command.split()[1:]
        return [sys.executable, *python_args]

    command_parts = command.split()
    if os.name == "nt" and command_parts and command_parts[0] == "npm":
        command_parts[0] = "npm.cmd"
    return command_parts


def _build_launch_command(
    command: str,
    open_in_new_terminal: bool,
    port: int | None = None,
) -> tuple[list[str], bool]:
    if open_in_new_terminal:
        return _build_terminal_launch(command, port=port)
    return _build_inline_launch(command, port=port), False


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
        st.toast(f"실행 중: {display_name} (PID {process_id})")
        return
    st.warning(f"프로세스가 바로 종료되었습니다: {display_name}")


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

    launch_command, use_shell = _build_launch_command(command, open_in_new_terminal, port=port)
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
        st.error(f"실행 실패: {error}")


def _render_process_summary(process: TrackedProcess) -> None:
    st.markdown(f"**{process.name}**")
    st.caption(f"PID {process.pid} | {process.launched_at}")


def _render_process_status(process: TrackedProcess) -> None:
    st.markdown("실행 중")
    if process.port:
        st.page_link(
            f"http://localhost:{process.port}",
            label=f"localhost:{process.port}",
            icon=":material/open_in_new:",
            width="stretch",
        )


def _handle_stop_button(process_id: int) -> None:
    if st.button("중지", key=f"kill_{process_id}", width="stretch"):
        pm.kill_process(process_id)
        st.rerun()


def _handle_restart_button(process: TrackedProcess) -> None:
    if st.button("재시작", key=f"restart_{process.pid}", width="stretch"):
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

    with st.expander(f"실행 중인 프로세스 ({len(running_processes)})", expanded=False):
        for process in running_processes:
            _render_process_row(process)

        st.divider()
        if st.button("모두 중지", type="primary", key="kill_all", width="stretch"):
            killed_count = pm.kill_all()
            st.toast(f"{killed_count}개 프로세스를 중지했습니다.")
            st.rerun()


_render_process_monitor()

st.divider()

PROJECTS = [
    {
        "key": "shorts",
        "icon": "🎬",
        "name": "Shorts Manager",
        "status": "운영",
        "desc": "쇼츠 생성물 검수, 채널 준비도, 업로드 결과 등록을 한 화면에서 처리합니다.",
        "output": "복사·업로드 가능한 쇼츠 대본/메타데이터와 수동 업로드 기록",
        "best_for": "새 쇼츠 후보를 검수하고 YouTube/X 게시 준비 상태를 확인할 때",
        "quality_signal": "Shorts Maker V2 QC PASS, 채널별 준비도와 잠금 사유 표시",
        "next_action": "검수 큐 확인 -> 채널 잠금 해소 -> 결과 URL 등록",
        "cmd": "streamlit run workspace/execution/pages/shorts_manager.py",
        "cwd": ".",
        "port": 8512,
        "primary": True,
        "category": "작업 앱",
    },
    {
        "key": "api",
        "icon": "📡",
        "name": "API Monitor",
        "status": "운영",
        "desc": "API 사용량과 비용 위험을 운영자가 바로 판단할 수 있게 정리합니다.",
        "output": "예산 초과 위험, 제공자별 비용, 다음 비용 절감 행동",
        "best_for": "콘텐츠 생성/검수 전에 API 비용과 크레딧 상태를 확인할 때",
        "quality_signal": "비용 운영 문구와 예산 액션 가이드를 테스트로 고정",
        "next_action": "예산 경고 확인 -> 고비용 제공자 점검 -> 필요 시 생성량 조절",
        "cmd": "streamlit run workspace/execution/pages/api_monitor.py",
        "cwd": ".",
        "port": 8508,
        "category": "작업 앱",
    },
    {
        "key": "qaqc",
        "icon": "✅",
        "name": "QAQC Status",
        "status": "우선 확인",
        "desc": "가장 최신 검증 증거와 프로젝트별 다음 조치를 먼저 보여줍니다.",
        "output": "현재 HEAD 기준 QC verdict, stale 경고, 프로젝트별 다음 행동",
        "best_for": "배포·공유 전에 로컬 결과물이 실제로 검증됐는지 확인할 때",
        "quality_signal": "최신 .tmp QC artifact 우선 로드, stale/incomplete 경고 테스트",
        "next_action": "최신 QC 시간 확인 -> 실패/누락 프로젝트 조치 -> publish 경계 분리",
        "cmd": "streamlit run workspace/execution/pages/qaqc_status.py",
        "cwd": ".",
        "port": 8515,
        "category": "작업 앱",
    },
    {
        "key": "daily_report",
        "icon": "📝",
        "name": "Daily Report",
        "status": "운영",
        "desc": "하루 작업을 공유 가능한 리포트 형태로 정리하고 내보냅니다.",
        "output": "변경 파일, 검증 결과, 세션 요약이 포함된 공유용 일일 리포트",
        "best_for": "오늘 무엇이 개선됐는지 팀이나 다음 AI 도구에 넘길 때",
        "quality_signal": "세션 로그와 작업 요약을 사용자 전달용 구조로 정리",
        "next_action": "기간 선택 -> 검증 증거 확인 -> 리포트 저장/공유",
        "cmd": "streamlit run workspace/execution/pages/daily_report.py",
        "cwd": ".",
        "port": 8504,
        "category": "작업 앱",
    },
    {
        "key": "github",
        "icon": "🐙",
        "name": "GitHub Dash",
        "status": "보조",
        "desc": "브랜치, PR, 최근 커밋 흐름을 작업 판단에 필요한 수준으로 요약합니다.",
        "output": "저장소 활동, 브랜치 상태, 릴리스 전 확인 지점",
        "best_for": "로컬 작업과 원격 상태의 차이를 확인할 때",
        "quality_signal": "release authorization 전 원격/PR 상태 확인 보조",
        "next_action": "브랜치 상태 확인 -> PR/Action 경계 확인 -> 승인 후 push",
        "cmd": "streamlit run workspace/execution/pages/github_dashboard.py",
        "cwd": ".",
        "port": 8507,
        "category": "작업 앱",
    },
    {
        "key": "hanwoo",
        "icon": "🐄",
        "name": "Hanwoo Dashboard",
        "status": "외부 경계 있음",
        "desc": "축산 현장 업무를 모바일에서 바로 처리할 수 있게 만든 한우 관리 앱입니다.",
        "output": "개체·사료·번식·일정·알림 운영 화면과 현장 입력 흐름",
        "best_for": "농장 데이터 입력/조회 UX와 모바일 작업성을 확인할 때",
        "quality_signal": "로컬 test/lint/build/smoke PASS, T-251 live Supabase CRUD는 credential 재동기화 후 재검증",
        "next_action": "로컬 UX 확인 -> T-251 credential reset 후 live CRUD만 별도 재시도",
        "cmd": "npm run dev",
        "cwd": "projects/hanwoo-dashboard",
        "port": 3001,
        "terminal": True,
        "category": "제품",
    },
    {
        "key": "knowledge",
        "icon": "🧠",
        "name": "Knowledge Dashboard",
        "status": "운영",
        "desc": "검증 결과와 지식 데이터를 인증된 화면에서 전달 가능한 형태로 보여줍니다.",
        "output": "인증 기반 QA/QC 표시, 지식 요약, 공유 가능한 검증 프레젠테이션",
        "best_for": "외부 공유 전 검증 자료를 확인하거나 Knowledge 화면을 점검할 때",
        "quality_signal": "Knowledge test/lint/build/smoke PASS, mobile skip target 검증",
        "next_action": "인증 화면 로드 -> QA/QC 데이터 freshness 확인 -> 공유",
        "cmd": "npm run dev",
        "cwd": "projects/knowledge-dashboard",
        "port": 3000,
        "category": "제품",
    },
    {
        "key": "blind",
        "icon": "X",
        "name": "Blind to X",
        "status": "운영",
        "desc": "블라인드 인기글을 검수 가능한 X 초안과 Notion 리뷰 카드로 전환합니다.",
        "output": "X 게시 가능성 verdict, 수정 계획, Notion 리뷰용 초안",
        "best_for": "트렌드 글을 바로 검수·게시할 수 있는 초안으로 바꿀 때",
        "quality_signal": "Best-of-N 선택 품질, X 가중 글자 수, Notion readiness verdict 테스트",
        "next_action": "소스 수집 -> 후보 검수 -> Ready to Post 항목만 게시",
        "cmd": "python main.py",
        "cwd": "projects/blind-to-x",
        "terminal": True,
        "category": "제품",
    },
    {
        "key": "word_chain",
        "icon": "🎮",
        "name": "Word Chain",
        "status": "동결",
        "desc": "검증된 React/Vite 끝말잇기 게임입니다. 기능 확장은 신중히 분리합니다.",
        "output": "한국어 입력 가능한 브라우저 게임 화면",
        "best_for": "보존된 데모 품질과 브라우저 실행 상태를 확인할 때",
        "quality_signal": "browser QA retained screenshot coverage 확보",
        "next_action": "실행 확인 -> 스크린샷 증거 확인 -> 새 기능은 별도 scope로 분리",
        "cmd": "npm run dev",
        "cwd": "projects/word-chain",
        "port": 5173,
        "category": "제품",
    },
    {
        "key": "suika",
        "icon": "🍉",
        "name": "Suika Game V2",
        "status": "동결",
        "desc": "브라우저 QA 증거를 유지하는 동결 Vite 게임 프로젝트입니다.",
        "output": "실행 가능한 Suika 게임 화면과 retained screenshot evidence",
        "best_for": "브라우저 앱 세트의 상태를 빠르게 확인할 때",
        "quality_signal": "fresh usable/nonblank screenshot coverage 확보",
        "next_action": "실행 확인 -> retained screenshot 확인 -> 변경은 별도 실험으로 분리",
        "cmd": "npm run dev -- --port 5174",
        "cwd": "projects/suika-game-v2",
        "port": 5174,
        "category": "제품",
    },
    {
        "key": "doctor",
        "icon": "🩺",
        "name": "Workspace Doctor",
        "status": "진단",
        "desc": "환경·의존성 문제를 빠르게 확인하는 로컬 진단 도구입니다.",
        "output": "환경 이상 징후와 복구 우선순위",
        "best_for": "테스트 실패가 코드가 아니라 환경 문제인지 가를 때",
        "quality_signal": "로컬 실행형 진단으로 중간 산출물 없이 즉시 확인",
        "next_action": "진단 실행 -> 실패 항목만 수정 -> 관련 QC 재실행",
        "cmd": "python workspace/scripts/doctor.py",
        "cwd": ".",
        "terminal": True,
        "category": "운영",
    },
    {
        "key": "quality_gate",
        "icon": "🛡️",
        "name": "Quality Gate",
        "status": "검증",
        "desc": "루트 품질 게이트를 터미널에서 실행해 릴리스 전 위험을 확인합니다.",
        "output": "전역 품질 게이트 결과와 차단/경고 사유",
        "best_for": "여러 프로젝트를 건드린 뒤 최종 로컬 검증을 시작할 때",
        "quality_signal": "root quality gate를 별도 프로세스로 실행",
        "next_action": "게이트 실행 -> warning/fail 원인 분리 -> focused test 재실행",
        "cmd": "python workspace/scripts/quality_gate.py",
        "cwd": ".",
        "terminal": True,
        "category": "운영",
    },
    {
        "key": "scheduler_worker",
        "icon": "⚙️",
        "name": "Scheduler Worker",
        "status": "자동화",
        "desc": "예약된 작업을 폴링하고 실행하는 워커를 시작합니다.",
        "output": "자동 실행 로그, 실패 알림, Telegram 운영 메시지",
        "best_for": "정기 작업이 실제로 돌아가는지 확인하거나 재시작할 때",
        "quality_signal": "Scheduler Dashboard/Telegram 알림 copy contract 검증",
        "next_action": "워커 실행 -> Scheduler Dashboard에서 실패/대기 작업 확인",
        "cmd": "python workspace/execution/scheduler_worker.py --interval 30",
        "cwd": ".",
        "terminal": True,
        "category": "운영",
    },
    {
        "key": "health",
        "icon": "🏥",
        "name": "Health Check",
        "status": "진단",
        "desc": "시스템 상태를 운영자가 바로 조치할 수 있는 항목으로 정리합니다.",
        "output": "우선순위 조치, 카테고리별 상태, 실패 사유",
        "best_for": "현재 작업 전후로 환경과 연결 상태를 빠르게 점검할 때",
        "quality_signal": "Korean operator actions, priority sorting, 44px controls 테스트",
        "next_action": "점검 실행 -> 우선순위 높은 항목부터 복구 -> 관련 app 재실행",
        "cmd": "streamlit run workspace/execution/pages/health_check_dashboard.py",
        "cwd": ".",
        "port": 8513,
        "category": "운영",
    },
    {
        "key": "debug_history",
        "icon": "🪲",
        "name": "Debug History",
        "status": "분석",
        "desc": "반복 오류와 해결 이력을 재사용 가능한 패턴으로 추적합니다.",
        "output": "오류 패턴, 원인 후보, 재발 방지 메모",
        "best_for": "같은 실패가 반복될 때 이전 해결 증거를 찾을 때",
        "quality_signal": "debug history and error pattern tracker evidence surface",
        "next_action": "오류 검색 -> 이전 해결 패턴 확인 -> 현재 실패에 적용",
        "cmd": "streamlit run workspace/execution/pages/debug_history.py",
        "cwd": ".",
        "port": 8514,
        "category": "운영",
    },
]


def _status_chip_class(status: str) -> str:
    if "경계" in status or "동결" in status:
        return "blocked"
    if status in {"진단", "검증", "분석", "자동화", "보조"}:
        return "warn"
    return ""


def _render_status_chip(status: str) -> None:
    chip_class = _status_chip_class(status)
    class_attr = f"hub-chip {chip_class}".strip()
    st.markdown(f"<span class='{class_attr}'>{status}</span>", unsafe_allow_html=True)


def _project_quality_markdown(project: dict[str, Any], snapshot: dict[str, Any] | None) -> str:
    evidence = _project_evidence_line(project, snapshot)
    return "\n".join(
        [
            f"<p class='hub-card-line'><strong>결과물</strong> · {project['output']}</p>",
            f"<p class='hub-card-line'><strong>사용 장면</strong> · {project['best_for']}</p>",
            f"<p class='hub-card-line'><strong>검증 신호</strong> · {evidence}</p>",
            f"<p class='hub-card-line'><strong>다음 행동</strong> · {project['next_action']}</p>",
        ]
    )


def render_card(project: dict, snapshot: dict[str, Any] | None = None) -> None:
    with st.container(border=True):
        _render_status_chip(project["status"])
        st.header(f"{project['icon']} {project['name']}")
        st.markdown(project["desc"])
        st.markdown(_project_quality_markdown(project, snapshot), unsafe_allow_html=True)

        button_options = {"type": "primary"} if project.get("primary") else {}
        if st.button("실행", key=f"btn_{project['key']}", width="stretch", **button_options):
            launch_process(
                project["cmd"],
                working_directory=project["cwd"],
                process_name=project["name"],
                port=project.get("port"),
                open_in_new_terminal=project.get("terminal", False),
            )
        if project.get("port"):
            st.page_link(
                f"http://localhost:{project['port']}",
                label=f"로컬 열기 · {project['port']}",
                icon=":material/open_in_new:",
                width="stretch",
            )


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


def _render_project_category(
    category_name: str,
    projects: list[dict],
    snapshot: dict[str, Any] | None = None,
) -> None:
    st.divider()
    st.subheader(category_name)
    for project_row in _project_rows(projects):
        row_columns = st.columns(3)
        for column_index, project in enumerate(project_row):
            with row_columns[column_index]:
                render_card(project, snapshot=snapshot)


def _render_project_registry(projects: list[dict], snapshot: dict[str, Any] | None = None) -> None:
    projects_by_category = _group_projects_by_category(projects)
    for category_name, category_projects in projects_by_category.items():
        _render_project_category(category_name, category_projects, snapshot=snapshot)


_render_project_registry(PROJECTS, snapshot=qc_snapshot)

st.divider()
st.caption(f"작업 루트: {REPO_ROOT}")
