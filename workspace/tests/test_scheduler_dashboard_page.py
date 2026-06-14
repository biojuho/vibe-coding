from __future__ import annotations

import importlib
import sys
import types
from pathlib import Path
from types import SimpleNamespace

import pytest

WORKSPACE_ROOT = Path(__file__).resolve().parents[1]
if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT))


class _DummyBlock:
    def __init__(self, streamlit_module: "_FakeStreamlit") -> None:
        self._streamlit = streamlit_module

    def __enter__(self) -> "_DummyBlock":
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:
        return False

    def __getattr__(self, name: str):
        return getattr(self._streamlit, name)


class _FakeStreamlit(types.ModuleType):
    def __init__(self) -> None:
        super().__init__("streamlit")
        self.events: list[tuple[str, object, dict]] = []

    def _record(self, name: str, payload: object = None, **kwargs) -> None:
        self.events.append((name, payload, kwargs))

    def set_page_config(self, **kwargs) -> None:
        self._record("set_page_config", kwargs)

    def title(self, label: object) -> None:
        self._record("title", label)

    def caption(self, label: object) -> None:
        self._record("caption", label)

    def subheader(self, label: object) -> None:
        self._record("subheader", label)

    def markdown(self, body: object, **kwargs) -> None:
        self._record("markdown", body, **kwargs)

    def info(self, message: object) -> None:
        self._record("info", message)

    def error(self, message: object) -> None:
        self._record("error", message)

    def button(self, label: object, **kwargs) -> bool:
        self._record("button", label, **kwargs)
        return False

    def form_submit_button(self, label: object, **kwargs) -> bool:
        self._record("form_submit_button", label, **kwargs)
        return False

    def text_input(self, label: object, **kwargs) -> str:
        self._record("text_input", label, **kwargs)
        return str(kwargs.get("value", ""))

    def number_input(self, label: object, **kwargs) -> object:
        self._record("number_input", label, **kwargs)
        return kwargs.get("value")

    def selectbox(self, label: object, **kwargs) -> object:
        self._record("selectbox", label, **kwargs)
        options = kwargs.get("options") or []
        return options[0] if options else None

    def columns(self, spec):
        count = spec if isinstance(spec, int) else len(spec)
        return [_DummyBlock(self) for _ in range(count)]

    def container(self, *args, **kwargs) -> _DummyBlock:
        self._record("container", None, **kwargs)
        return _DummyBlock(self)

    def expander(self, *args, **kwargs) -> _DummyBlock:
        self._record("expander", args[0] if args else None, **kwargs)
        return _DummyBlock(self)

    def form(self, *args, **kwargs) -> _DummyBlock:
        self._record("form", args[0] if args else None, **kwargs)
        return _DummyBlock(self)

    def stop(self) -> None:
        raise RuntimeError("streamlit stop called")

    def rerun(self) -> None:
        self._record("rerun")

    def __getattr__(self, name: str):
        def _method(*args, **kwargs):
            self._record(name, args[0] if args else None, **kwargs)

        return _method


def _install_scheduler_dependencies(
    monkeypatch: pytest.MonkeyPatch,
    *,
    with_task: bool = False,
    with_ops_items: bool = False,
) -> None:
    scheduler = types.ModuleType("execution.scheduler_engine")
    task = SimpleNamespace(
        id=7,
        enabled=True,
        name="daily-shorts",
        command="python runner.py",
        cron_expression="0 9 * * *",
        last_run=None,
        next_run="2026-06-08 09:00",
        failure_count=0,
        timeout_sec=300,
    )
    failure_items = [
        {
            "name": "daily-shorts",
            "last_error_type": "non_zero_exit",
            "recent_failures": 2,
            "failure_count": 3,
            "next_action": "명령과 환경을 우선 점검",
            "last_failed_at": "2026-06-08 08:40",
            "last_stderr": "quotaExceeded",
        }
    ]
    attention_items = [
        {
            "name": "daily-shorts",
            "reasons": ["auto_disabled", "repeated_failures", "overdue"],
            "failure_count": 3,
            "next_run": "2026-06-08 08:00",
            "next_action": "오류 수정 후 재활성화",
        }
    ]
    logs = [
        SimpleNamespace(
            exit_code=1,
            task_name="daily-shorts",
            started_at="2026-06-08 08:40",
            duration_ms=1500,
            trigger_type="schedule",
            error_type="exec_not_found",
            stdout="",
            stderr="runner not found",
        )
    ]
    scheduler.add_task = lambda *args, **kwargs: 101
    scheduler.delete_task = lambda task_id: None
    scheduler.get_attention_queue = lambda limit=6: attention_items[:limit] if with_ops_items else []
    scheduler.get_logs = lambda task_id=None, limit=30: logs[:limit] if with_ops_items else []
    scheduler.get_recent_failure_summary = lambda limit=6: failure_items[:limit] if with_ops_items else []
    scheduler.get_scheduler_ops_summary = lambda: {
        "status": "healthy",
        "next_action": "정상 작동 중",
        "last_heartbeat": "2026-06-08 08:50",
        "seconds_since_heartbeat": 10,
        "note": "",
    }
    scheduler.get_scheduler_kpis = lambda days=7: {
        "total_runs": 3,
        "scheduler_success_rate": 100.0,
        "scheduler_backlog": 0,
        "successful_runs": 3,
    }
    scheduler.init_db = lambda: None
    scheduler.list_tasks = lambda: [task] if with_task else []
    scheduler.run_task = lambda task_id: SimpleNamespace(exit_code=0)
    scheduler.toggle_task = lambda task_id, enabled: None
    monkeypatch.setitem(sys.modules, "execution.scheduler_engine", scheduler)

    telegram = types.ModuleType("execution.telegram_notifier")
    telegram.get_delivery_status_summary = lambda: {
        "status": "healthy",
        "last_success_at": "2026-06-08 08:55",
        "last_failure_at": None,
        "next_action": "정상 작동 중",
        "last_error": "",
        "last_message_preview": "done",
    }
    monkeypatch.setitem(sys.modules, "execution.telegram_notifier", telegram)


def _import_scheduler_dashboard(
    monkeypatch: pytest.MonkeyPatch,
    *,
    with_task: bool = False,
    with_ops_items: bool = False,
):
    sys.modules.pop("execution.pages.scheduler_dashboard", None)
    fake_streamlit = _FakeStreamlit()
    monkeypatch.setitem(sys.modules, "streamlit", fake_streamlit)
    _install_scheduler_dependencies(monkeypatch, with_task=with_task, with_ops_items=with_ops_items)

    module = importlib.import_module("execution.pages.scheduler_dashboard")
    return module, fake_streamlit


def test_scheduler_dashboard_uses_workspace_root_import_contract() -> None:
    source = Path("workspace/execution/pages/scheduler_dashboard.py").read_text(encoding="utf-8")

    assert "_WORKSPACE_ROOT = Path(__file__).resolve().parents[2]" in source
    assert "sys.path.insert(0, str(_WORKSPACE_ROOT))" in source
    assert "Path(__file__).resolve().parent.parent" not in source


def test_scheduler_dashboard_imports_with_fake_dependencies(monkeypatch: pytest.MonkeyPatch) -> None:
    _module, fake_streamlit = _import_scheduler_dashboard(monkeypatch)

    assert ("set_page_config", {"page_title": "자동 실행 관리 - Joolife", "page_icon": "📅", "layout": "wide"}, {}) in (
        fake_streamlit.events
    )
    assert ("title", "📅 자동 실행 관리", {}) in fake_streamlit.events
    assert not [event for event in fake_streamlit.events if event[0] == "error"]


def test_scheduler_dashboard_injects_mobile_touch_target_css(monkeypatch: pytest.MonkeyPatch) -> None:
    module, fake_streamlit = _import_scheduler_dashboard(monkeypatch)
    fake_streamlit.events.clear()

    module._inject_scheduler_dashboard_mobile_css()

    markdowns = [(payload, kwargs) for name, payload, kwargs in fake_streamlit.events if name == "markdown"]
    assert markdowns
    css, kwargs = markdowns[-1]
    assert kwargs == {"unsafe_allow_html": True}
    assert "@media (max-width: 640px)" in css
    assert "div[data-testid='stFormSubmitButton']" in css
    assert "div[data-testid='stButton']" in css
    assert "div[data-testid='stTextInput'] input" in css
    assert "div[data-testid='stNumberInput']" in css
    assert "div[data-testid='stExpander'] summary" in css
    assert "div[data-baseweb='select'] > div" in css
    assert "div[data-baseweb='input'] > div" in css
    assert "button[aria-label='Main menu']" in css
    assert "button[data-testid='stBaseButton-header']" in css
    assert "min-height: 44px !important" in css
    assert "height: 44px !important" in css
    assert "min-width: 44px !important" in css


def test_scheduler_dashboard_formats_status_reason_and_log_codes(monkeypatch: pytest.MonkeyPatch) -> None:
    module, fake_streamlit = _import_scheduler_dashboard(monkeypatch, with_task=True, with_ops_items=True)

    assert "위험" in module._ops_badge("critical")
    assert "설정 필요" in module._ops_badge("setup_required")
    assert module._format_attention_reasons(["auto_disabled", "repeated_failures", "overdue"]) == (
        "자동 비활성화, 반복 실패, 실행 지연"
    )

    rendered_text = "\n".join(str(payload) for _name, payload, _kwargs in fake_streamlit.events)
    assert "오류 유형: `비정상 종료`" in rendered_text
    assert "사유: 자동 비활성화, 반복 실패, 실행 지연" in rendered_text
    assert "**종료 코드:** 1" in rendered_text
    assert "**소요 시간:** 1.5초" in rendered_text
    assert "**실행 방식:** 예약 실행" in rendered_text
    assert "**오류 유형:** `실행 파일 없음`" in rendered_text
    assert "auto_disabled" not in rendered_text
    assert "repeated_failures" not in rendered_text
    assert "exec_not_found" not in rendered_text
    assert "**Exit code:**" not in rendered_text
    assert "**Duration:**" not in rendered_text
    assert "**Trigger:**" not in rendered_text
    assert "**Error Type:**" not in rendered_text


def test_scheduler_dashboard_formats_legacy_telegram_preview(monkeypatch: pytest.MonkeyPatch) -> None:
    module, _fake_streamlit = _import_scheduler_dashboard(monkeypatch)

    preview = module._format_telegram_message_preview(
        "[Joolife][Scheduler] FAILED\n"
        "Task: daily-shorts\n"
        "Trigger: schedule\n"
        "Exit code: 1\n"
        "Duration: 1500 ms\n"
        "Error type: exec_not_found\n"
        "Auto-disabled: yes\n"
        "Error: runner not found"
    )

    assert "[Joolife][자동 실행] 실패" in preview
    assert "작업: daily-shorts" in preview
    assert "실행 방식: 예약 실행" in preview
    assert "종료 코드: 1" in preview
    assert "소요 시간: 1.5초" in preview
    assert "오류 유형: 실행 파일 없음" in preview
    assert "자동 비활성화: 예" in preview
    assert "오류 내용: runner not found" in preview
    assert "FAILED" not in preview
    assert "Task:" not in preview
    assert "exec_not_found" not in preview


def test_scheduler_dashboard_uses_korean_operator_copy_and_stretch_actions() -> None:
    source = Path("workspace/execution/pages/scheduler_dashboard.py").read_text(encoding="utf-8")

    assert 'st.title("📅 자동 실행 관리")' in source
    assert "예약 작업, 워커 상태, 알림 전송을 한 화면에서 점검합니다." in source
    assert "워커 상태" in source
    assert "최근 실패" in source
    assert "새 작업 추가" in source
    assert "예약 작업" in source
    assert "작업 필터" in source
    assert "Scheduler Dashboard" not in source
    assert "Task scheduling & automation management" not in source
    assert "Add New Task" not in source
    assert "Run Now" not in source
    assert "**Exit code:**" not in source
    assert "**Duration:**" not in source
    assert "**Trigger:**" not in source
    assert "**Error Type:**" not in source
    assert '_SCHEDULER_BUTTON_KWARGS = {"width": "stretch"}' in source


def test_scheduler_dashboard_task_actions_use_stretch_width(monkeypatch: pytest.MonkeyPatch) -> None:
    _module, fake_streamlit = _import_scheduler_dashboard(monkeypatch, with_task=True)

    buttons = [(payload, kwargs) for name, payload, kwargs in fake_streamlit.events if name == "button"]
    assert buttons
    assert ("비활성화", {"key": "toggle_7", "width": "stretch"}) in buttons
    assert ("지금 실행", {"key": "run_7", "width": "stretch"}) in buttons
    assert ("삭제", {"key": "del_7", "width": "stretch"}) in buttons

    submit_buttons = [
        (payload, kwargs) for name, payload, kwargs in fake_streamlit.events if name == "form_submit_button"
    ]
    assert submit_buttons == [("작업 추가", {"type": "primary", "width": "stretch"})]


def test_scheduler_dashboard_formats_scheduler_status_codes(monkeypatch: pytest.MonkeyPatch) -> None:
    module, _fake_streamlit = _import_scheduler_dashboard(monkeypatch)

    assert module._format_attention_reasons(["auto_disabled", "overdue"]) == "자동 비활성화, 실행 지연"
    assert module._format_attention_reasons(None) == "상태 확인"
    assert module._format_error_type("non_zero_exit") == "비정상 종료"
    assert module._format_trigger_type("manual") == "수동 실행"
    assert module._format_duration_ms(1200) == "1.2초"
    assert module._format_duration_ms("bad") == "알 수 없음"
    assert "설정 필요" in module._ops_badge("setup_required")

    preview = module._format_telegram_message_preview(
        "[Joolife][Scheduler] SUCCESS Task: ok-task Trigger: manual Exit code: 0 Duration: 1200 ms"
    )
    assert preview == "[Joolife][자동 실행] 성공 작업: ok-task 실행 방식: 수동 실행 종료 코드: 0 소요 시간: 1.2초"
