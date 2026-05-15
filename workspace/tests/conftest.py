"""
tests/conftest.py
Windows + pytest 캡처 충돌 방지.

pytest가 stdout/stderr를 캡처할 때 Windows에서 subprocess.PIPE와 핸들이 충돌하여
WinError 6 ('핸들이 잘못되었습니다')이 발생합니다.
test_scheduler_engine.py의 테스트들은 실제 subprocess를 실행하므로
캡처를 비활성화해야 합니다.
"""

from __future__ import annotations
import sys
from pathlib import Path

import pytest

WORKSPACE_ROOT = Path(__file__).resolve().parents[1]
if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT))


def pytest_collection_modifyitems(items):
    """scheduler_engine 테스트에 no-capture 마커 자동 적용 (Windows 한정)."""
    if sys.platform != "win32":
        return
    no_capture_files = (
        "test_scheduler_engine",
        "test_frontends",
        "test_graph_engine",
    )
    for item in items:
        if any(name in str(item.fspath) for name in no_capture_files):
            item.add_marker(pytest.mark.usefixtures("_disable_capture"))


@pytest.fixture
def _disable_capture(request):
    """subprocess 실행 테스트를 위해 pytest stdout 캡처를 일시 중단."""
    capman = request.config.pluginmanager.getplugin("capturemanager")
    if capman is not None:
        capman.suspend_global_capture(in_=True)
        yield
        capman.resume_global_capture()
    else:
        yield
