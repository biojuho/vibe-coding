"""Tests for shorts_manager.py pure helper functions (T-114).

Loads only the function-definition portion of the module (before the
Streamlit page-rendering block that starts at ~line 457), so we can
exercise pure helpers without a real Streamlit runtime.
"""

from __future__ import annotations

import sys
import types
from pathlib import Path
from unittest.mock import MagicMock

# ---------------------------------------------------------------------------
# Stub Streamlit and optional deps — save originals so we can restore later
# ---------------------------------------------------------------------------
_STUBBED_MODULES: dict = {}


def _stub(name: str, mod) -> None:
    global _STUBBED_MODULES
    _STUBBED_MODULES[name] = sys.modules.get(name)
    sys.modules[name] = mod


_st = types.ModuleType("streamlit")
for _attr in (
    "set_page_config",
    "error",
    "stop",
    "info",
    "success",
    "warning",
    "caption",
    "markdown",
    "tabs",
    "columns",
    "container",
    "expander",
    "button",
    "image",
    "code",
    "divider",
    "rerun",
    "metric",
    "dataframe",
    "text_input",
    "number_input",
    "selectbox",
    "checkbox",
    "form",
    "form_submit_button",
    "title",
    "subheader",
    "sidebar",
    "write",
):
    setattr(_st, _attr, MagicMock(return_value=None))
_st.session_state = {}
_stub("streamlit", _st)

_pc = types.ModuleType("path_contract")
_pc.resolve_project_dir = MagicMock(return_value=None)  # type: ignore[attr-defined]
_stub("path_contract", _pc)

for _m in ("execution.content_db", "execution.youtube_uploader", "execution.notion_shorts_sync"):
    _stub(_m, MagicMock())

# ---------------------------------------------------------------------------
# exec only the function-definition portion of shorts_manager.py
# ---------------------------------------------------------------------------
WORKSPACE_ROOT = Path(__file__).resolve().parents[2]
_src_path = WORKSPACE_ROOT / "workspace" / "execution" / "pages" / "shorts_manager.py"
_lines = _src_path.read_text(encoding="utf-8").splitlines(keepends=True)

# Page rendering starts at "st.title(" — stop before that
_cutoff = next(i for i, ln in enumerate(_lines) if ln.strip().startswith("st.title("))
_src_defs = "".join(_lines[:_cutoff])

_ns: dict = {"__file__": str(_src_path), "__name__": "shorts_manager"}
exec(compile(_src_defs, str(_src_path), "exec"), _ns)  # noqa: S102

_fmt_dur = _ns["_fmt_dur"]
_fmt_cost = _ns["_fmt_cost"]
_youtube_badge = _ns["_youtube_badge"]
_build_upload_metadata = _ns["_build_upload_metadata"]
_voice_index = _ns["_voice_index"]
_style_index = _ns["_style_index"]
VOICE_OPTIONS = _ns["VOICE_OPTIONS"]
STYLE_OPTIONS = _ns["STYLE_OPTIONS"]

# Restore original modules so other test files in the same session are not
# affected by the stubs above. (pytest collects all tests in one process.)
for _mod_name, _orig in _STUBBED_MODULES.items():
    if _orig is None:
        sys.modules.pop(_mod_name, None)
    else:
        sys.modules[_mod_name] = _orig
del _STUBBED_MODULES


# ---------------------------------------------------------------------------
# _fmt_dur
# ---------------------------------------------------------------------------


class TestFmtDur:
    def test_zero_returns_dash(self):
        assert _fmt_dur(0) == "-"

    def test_negative_returns_dash(self):
        assert _fmt_dur(-5) == "-"

    def test_under_a_minute(self):
        assert _fmt_dur(45) == "0:45"

    def test_exact_minute(self):
        assert _fmt_dur(60) == "1:00"

    def test_mixed(self):
        assert _fmt_dur(125) == "2:05"


# ---------------------------------------------------------------------------
# _fmt_cost
# ---------------------------------------------------------------------------


class TestFmtCost:
    def test_zero_returns_dash(self):
        assert _fmt_cost(0) == "-"

    def test_positive(self):
        assert _fmt_cost(0.0025) == "$0.0025"

    def test_negative_returns_dash(self):
        assert _fmt_cost(-1.0) == "-"


# ---------------------------------------------------------------------------
# _youtube_badge
# ---------------------------------------------------------------------------


class TestYoutubeBadge:
    def test_uploaded_with_url(self):
        result = _youtube_badge("uploaded", "https://youtube.com/watch?v=abc")
        assert "href=" in result
        assert "youtube.com" in result

    def test_uploaded_no_url(self):
        result = _youtube_badge("uploaded", "")
        assert "href=" not in result
        assert "YT" in result

    def test_failed(self):
        result = _youtube_badge("failed")
        assert "YT 실패" in result

    def test_empty_returns_empty(self):
        assert _youtube_badge("") == ""

    def test_xss_in_url_escaped(self):
        result = _youtube_badge("uploaded", "https://y.com/?q=<script>")
        assert "<script>" not in result


# ---------------------------------------------------------------------------
# _build_upload_metadata
# ---------------------------------------------------------------------------


class TestBuildUploadMetadata:
    def test_with_channel(self):
        desc, tags = _build_upload_metadata({"topic": "Black Holes", "channel": "space"})
        assert "#space" in desc
        assert "#Black Holes" in desc
        assert "space" in tags
        assert "shorts" in tags

    def test_without_channel(self):
        desc, tags = _build_upload_metadata({"topic": "AI", "channel": ""})
        assert "#AI" in desc
        assert tags == ["shorts"]


# ---------------------------------------------------------------------------
# _voice_index / _style_index
# ---------------------------------------------------------------------------


class TestIndexHelpers:
    def test_voice_known(self):
        idx = _voice_index({"voice": "nova"})
        assert VOICE_OPTIONS[idx] == "nova"

    def test_voice_unknown_defaults_to_zero(self):
        assert _voice_index({"voice": "unknown_voice"}) == 0

    def test_voice_none_settings_defaults_to_zero(self):
        assert _voice_index(None) == 0

    def test_style_known(self):
        idx = _style_index({"style_preset": "neon"})
        assert STYLE_OPTIONS[idx] == "neon"

    def test_style_unknown_defaults_to_zero(self):
        assert _style_index({"style_preset": "nonexistent"}) == 0
