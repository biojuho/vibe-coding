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
import pytest


def pytest_collection_modifyitems(items):
    """scheduler_engine 테스트에 no-capture 마커 자동 적용 (Windows 한정)."""
    if sys.platform != "win32":
        return
    for item in items:
        if "test_scheduler_engine" in str(item.fspath):
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
