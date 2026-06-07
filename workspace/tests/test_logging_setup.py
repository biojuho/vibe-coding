from __future__ import annotations

import importlib
import io
import sys


def test_loguru_setup_uses_dunder_stderr_when_stderr_is_missing(monkeypatch) -> None:
    import execution._logging as logging_module

    original_stderr = sys.stderr
    original_dunder_stderr = sys.__stderr__
    fallback_stderr = io.StringIO()

    monkeypatch.setattr(sys, "stderr", None)
    monkeypatch.setattr(sys, "__stderr__", fallback_stderr)

    try:
        reloaded = importlib.reload(logging_module)
        reloaded.logger.info("streamlit hosted logging smoke")
    finally:
        monkeypatch.setattr(sys, "stderr", original_stderr)
        monkeypatch.setattr(sys, "__stderr__", original_dunder_stderr)
        importlib.reload(logging_module)

    assert "streamlit hosted logging smoke" in fallback_stderr.getvalue()
