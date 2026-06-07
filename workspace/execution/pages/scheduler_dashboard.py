import re
import shlex
import sys
from pathlib import Path

_WORKSPACE_ROOT = Path(__file__).resolve().parents[2]
if str(_WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(_WORKSPACE_ROOT))

import streamlit as st  # noqa: E402

try:
    from execution.scheduler_engine import (
        add_task,
        delete_task,
        get_attention_queue,
        get_logs,
        get_recent_failure_summary,
        get_scheduler_kpis,
        get_scheduler_ops_summary,
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

_SCHEDULER_BUTTON_KWARGS = {"width": "stretch"}
_ATTENTION_REASON_LABELS = {
    "auto_disabled": "자동 비활성화",
    "repeated_failures": "반복 실패",
    "overdue": "실행 지연",
}
_ERROR_TYPE_LABELS = {
    "auto_disabled": "자동 비활성화",
    "cwd_not_found": "작업 디렉터리 없음",
    "exception": "실행 예외",
    "exec_not_found": "실행 파일 없음",
    "invalid_command": "명령 파싱 실패",
    "non_zero_exit": "비정상 종료",
    "timeout": "시간 초과",
}
_TRIGGER_TYPE_LABELS = {
    "manual": "수동 실행",
    "schedule": "예약 실행",
}

st.set_page_config(page_title="자동 실행 관리 - Joolife", page_icon="📅", layout="wide")

if not _MODULE_OK:
    st.error(f"스케줄러 모듈을 불러올 수 없습니다: {_MODULE_ERR}")
    st.info("실행: `pip install croniter` 후 앱을 재시작하세요.")
    st.stop()


def _inject_scheduler_dashboard_mobile_css() -> None:
    st.markdown(
        """
<style>
@media (max-width: 640px) {
  button[kind='primary'],
  button[kind='secondary'],
  div[data-testid='stFormSubmitButton'] button,
  div[data-testid='stButton'] button,
  div[data-testid='stTextInput'] input,
  div[data-testid='stNumberInput'] input,
  div[data-testid='stNumberInput'] button,
  div[data-baseweb='select'],
  div[data-baseweb='input'] {
    min-height: 44px;
  }
  div[data-testid='stNumberInput'] button,
  div[data-testid='stButton'] button,
  div[data-testid='stFormSubmitButton'] button {
    min-width: 44px;
  }
  div[data-testid='stExpander'] summary {
    min-height: 44px;
    align-items: center;
  }
  button[aria-label='Main menu'],
  button[data-testid='stBaseButton-header'] {
    min-height: 44px;
    min-width: 44px;
  }
}
</style>
""",
        unsafe_allow_html=True,
    )


def _ops_badge(status: str) -> str:
    colors = {
        "healthy": "#28a745",
        "warning": "#fd7e14",
        "critical": "#dc3545",
        "setup_required": "#6f42c1",
    }
    labels = {
        "healthy": "정상",
        "warning": "주의",
        "critical": "위험",
        "setup_required": "설정 필요",
    }
    color = colors.get(status, "#6c757d")
    label = labels.get(status, status)
    return (
        f"<span style='background:{color};color:white;padding:2px 8px;"
        f"border-radius:10px;font-size:0.75rem'>{label}</span>"
    )


def _format_code_label(value: object, labels: dict[str, str], *, empty_label: str = "없음") -> str:
    code = str(value or "").strip()
    if not code:
        return empty_label
    return labels.get(code, code.replace("_", " "))


def _format_attention_reasons(reasons: object) -> str:
    if not isinstance(reasons, (list, tuple)):
        return "상태 확인"
    labels = [_format_code_label(reason, _ATTENTION_REASON_LABELS, empty_label="") for reason in reasons]
    labels = [label for label in labels if label]
    return ", ".join(labels) if labels else "상태 확인"


def _format_error_type(error_type: object) -> str:
    return _format_code_label(error_type, _ERROR_TYPE_LABELS, empty_label="없음")


def _format_trigger_type(trigger_type: object) -> str:
    return _format_code_label(trigger_type, _TRIGGER_TYPE_LABELS, empty_label="알 수 없음")


def _format_duration_ms(duration_ms: object) -> str:
    try:
        value = int(duration_ms or 0)
    except (TypeError, ValueError):
        return "알 수 없음"
    if value >= 1000:
        return f"{value / 1000:.1f}초"
    return f"{value}ms"


def _format_telegram_message_preview(preview: object) -> str:
    text = str(preview or "").strip()
    if not text:
        return ""
    replacements = {
        "[Joolife][Scheduler] SUCCESS": "[Joolife][자동 실행] 성공",
        "[Joolife][Scheduler] FAILED": "[Joolife][자동 실행] 실패",
        "Task:": "작업:",
        "Trigger: manual": "실행 방식: 수동 실행",
        "Trigger: schedule": "실행 방식: 예약 실행",
        "Exit code:": "종료 코드:",
        "Duration:": "소요 시간:",
        "Auto-disabled: yes": "자동 비활성화: 예",
        "Error type:": "오류 유형:",
        "Error:": "오류 내용:",
    }
    for before, after in replacements.items():
        text = text.replace(before, after)
    for code, label in _ERROR_TYPE_LABELS.items():
        text = text.replace(f"오류 유형: {code}", f"오류 유형: {label}")

    return re.sub(
        r"소요 시간:\s*(\d+)\s*ms",
        lambda match: f"소요 시간: {_format_duration_ms(match.group(1))}",
        text,
    )


init_db()
_inject_scheduler_dashboard_mobile_css()

st.title("📅 자동 실행 관리")
st.caption("예약 작업, 워커 상태, 알림 전송을 한 화면에서 점검합니다.")

ops_summary = get_scheduler_ops_summary()
if ops_summary["status"] == "critical":
    st.error(ops_summary["next_action"])
elif ops_summary["status"] == "warning":
    st.warning(ops_summary["next_action"])
elif ops_summary["status"] == "setup_required":
    st.info(ops_summary["next_action"])

st.subheader("워커 상태")
worker_cols = st.columns([1.2, 1.2, 1.2, 2.4])
with worker_cols[0]:
    st.markdown(_ops_badge(ops_summary["status"]), unsafe_allow_html=True)
with worker_cols[1]:
    st.caption("마지막 하트비트")
    st.write(ops_summary["last_heartbeat"] or "기록 없음")
with worker_cols[2]:
    st.caption("경과 시간(초)")
    seconds_since = ops_summary["seconds_since_heartbeat"]
    st.write("-" if seconds_since is None else str(seconds_since))
with worker_cols[3]:
    st.caption("다음 조치")
    st.write(ops_summary["next_action"])

if ops_summary.get("note"):
    st.caption(f"워커 메모: {ops_summary['note']}")

st.subheader("최근 실패")
failure_items = get_recent_failure_summary(limit=6)
if not failure_items:
    st.info("최근 스케줄러 실패가 없습니다.")
else:
    for item in failure_items:
        with st.container(border=True):
            cols = st.columns([2.2, 1.2, 1.2, 2.4])
            with cols[0]:
                st.markdown(f"**{item['name']}**")
                st.caption(f"오류 유형: `{_format_error_type(item['last_error_type'])}`")
            with cols[1]:
                st.caption("최근 24시간")
                st.write(str(item["recent_failures"]))
            with cols[2]:
                st.caption("연속 실패")
                st.write(str(item["failure_count"]))
            with cols[3]:
                st.caption("다음 조치")
                st.write(item["next_action"])
            if item.get("last_failed_at"):
                st.caption(f"마지막 실패: {item['last_failed_at']}")
            if item.get("last_stderr"):
                st.caption(f"stderr: {item['last_stderr'][:160]}")

st.subheader("확인 필요 항목")
attention_items = get_attention_queue(limit=6)
if not attention_items:
    st.info("확인할 항목이 없습니다.")
else:
    for item in attention_items:
        with st.container(border=True):
            st.markdown(f"**{item['name']}**")
            st.caption(
                f"사유: {_format_attention_reasons(item.get('reasons'))} | "
                f"실패 횟수: {item['failure_count']} | "
                f"다음 실행: {item['next_run'] or '없음'}"
            )
            st.caption(f"다음 조치: {item['next_action']}")

st.subheader("텔레그램 알림 상태")
if not _TG_OK:
    st.info("텔레그램 알림 모듈을 불러올 수 없습니다.")
else:
    telegram_summary = get_delivery_status_summary()
    tg_cols = st.columns([1.2, 1.6, 1.6, 2.4])
    with tg_cols[0]:
        st.markdown(_ops_badge(telegram_summary["status"]), unsafe_allow_html=True)
    with tg_cols[1]:
        st.caption("마지막 성공")
        st.write(telegram_summary["last_success_at"] or "기록 없음")
    with tg_cols[2]:
        st.caption("마지막 실패")
        st.write(telegram_summary["last_failure_at"] or "없음")
    with tg_cols[3]:
        st.caption("다음 조치")
        st.write(telegram_summary["next_action"])
    if telegram_summary.get("last_error"):
        st.caption(f"마지막 오류: {telegram_summary['last_error']}")
    last_message_preview = _format_telegram_message_preview(telegram_summary.get("last_message_preview"))
    if last_message_preview:
        st.caption(f"마지막 메시지: {last_message_preview}")

kpi = get_scheduler_kpis(days=7)
k1, k2, k3, k4 = st.columns(4)
with k1:
    st.metric("7일 실행", kpi["total_runs"])
with k2:
    st.metric("성공률", f"{kpi['scheduler_success_rate']:.2f}%")
with k3:
    st.metric("대기열", kpi["scheduler_backlog"])
with k4:
    st.metric("성공 실행", kpi["successful_runs"])

st.divider()

with st.expander("새 작업 추가", expanded=False):
    with st.form("add_task_form"):
        col_a, col_b = st.columns(2)
        with col_a:
            name = st.text_input("작업 이름", placeholder="Daily Backup")
            executable = st.text_input("실행 파일", placeholder="python")
            args_text = st.text_input("인수", placeholder="scripts/backup_data.py --with-env")
        with col_b:
            cwd = st.text_input("작업 디렉터리", value=".")
            cron = st.text_input("Cron 표현식", placeholder="0 9 * * *")
            timeout_sec = st.number_input("제한 시간(초)", min_value=10, max_value=3600, value=300, step=10)
            st.caption("형식: 분 시 일 월 요일")
        submitted = st.form_submit_button("작업 추가", type="primary", **_SCHEDULER_BUTTON_KWARGS)
        if submitted and name and executable and cron:
            try:
                parsed_args = shlex.split(args_text, posix=False) if args_text else []
                task_id = add_task(name, executable, parsed_args, cwd, cron, timeout_sec=int(timeout_sec))
                st.success(f"작업 #{task_id} '{name}'이 생성되었습니다.")
                st.rerun()
            except Exception as e:
                st.error(f"생성 실패: {e}")

st.divider()

st.subheader("예약 작업")
tasks = list_tasks()

if not tasks:
    st.info("예약된 작업이 없습니다. 위에서 새 작업을 추가하세요.")
else:
    for task in tasks:
        col1, col2, col3, col4 = st.columns([3, 2, 2, 2])
        with col1:
            status_icon = "🟢" if task.enabled else "⚪"
            st.markdown(f"{status_icon} **{task.name}**")
            st.caption(f"`{task.command}` | cron: `{task.cron_expression}`")
        with col2:
            st.caption(f"마지막 실행: {task.last_run or '기록 없음'}")
            st.caption(f"다음 실행: {task.next_run or '없음'}")
            st.caption(f"실패 횟수: {task.failure_count} | 제한 시간: {task.timeout_sec}s")
        with col3:
            if st.button(
                "비활성화" if task.enabled else "활성화",
                key=f"toggle_{task.id}",
                **_SCHEDULER_BUTTON_KWARGS,
            ):
                toggle_task(task.id, not task.enabled)
                st.rerun()
            if st.button("지금 실행", key=f"run_{task.id}", **_SCHEDULER_BUTTON_KWARGS):
                with st.spinner(f"{task.name} 실행 중..."):
                    log = run_task(task.id)
                if log.exit_code == 0:
                    st.success("완료 (exit code: 0)")
                else:
                    st.error(f"실패 (exit code: {log.exit_code})")
                st.rerun()
        with col4:
            if st.button("삭제", key=f"del_{task.id}", **_SCHEDULER_BUTTON_KWARGS):
                delete_task(task.id)
                st.rerun()

st.divider()

st.subheader("실행 로그")
task_filter = st.selectbox(
    "작업 필터",
    options=[None] + [t.id for t in tasks],
    format_func=lambda value: (
        "전체 작업" if value is None else next((t.name for t in tasks if t.id == value), str(value))
    ),
)
logs = get_logs(task_id=task_filter, limit=30)

if not logs:
    st.info("아직 실행 로그가 없습니다.")
else:
    for log in logs:
        status = "✅" if log.exit_code == 0 else "❌"
        with st.expander(f"{status} {log.task_name} - {log.started_at}", expanded=False):
            st.markdown(f"**종료 코드:** {log.exit_code}")
            st.markdown(f"**소요 시간:** {_format_duration_ms(log.duration_ms)}")
            st.markdown(f"**실행 방식:** {_format_trigger_type(log.trigger_type)}")
            if log.error_type:
                st.markdown(f"**오류 유형:** `{_format_error_type(log.error_type)}`")
            if log.stdout:
                st.code(log.stdout, language="text")
            if log.stderr:
                st.error(log.stderr)
