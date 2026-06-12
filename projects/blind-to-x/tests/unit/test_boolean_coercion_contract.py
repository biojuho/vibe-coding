"""Boolean 강제 단일화 계약 테스트.

배경: config 플래그의 문자열 "false"가 Python truthiness로 True가 되는 버그가
52회의 디버그 루프 동안 파일별 `_as_bool()` 복붙으로 땜질됐다 (17개 변종,
"off"/"y" 같은 토큰에서 서로 모순). 이 테스트는 세 가지를 강제한다:

1. canonical `config.as_bool` / `as_optional_float` / `ConfigManager.get_bool` 의 동작 명세.
2. pipeline/ 아래 어떤 모듈도 로컬 `_as_bool`을 재정의하지 않는다 (공유 구현 강제).
3. standalone scripts(import 불가)의 `_as_bool` 사본은 canonical 과 동작 동치,
   `_quote_powershell_arg` 3벌은 상호 동치를 유지한다.
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

import pytest

from config import ConfigManager, as_bool, as_optional_float

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


# ---------------------------------------------------------------------------
# 1. canonical 명세
# ---------------------------------------------------------------------------

TRUE_VALUES = [True, 1, 1.5, -1, "1", "true", "TRUE", " yes ", "y", "on", "On"]
FALSE_VALUES = [False, 0, 0.0, "0", "false", "False", " FALSE ", "no", "n", "off", ""]


@pytest.mark.parametrize("value", TRUE_VALUES)
def test_as_bool_true_tokens(value):
    assert as_bool(value) is True


@pytest.mark.parametrize("value", FALSE_VALUES)
def test_as_bool_false_tokens(value):
    assert as_bool(value) is False


def test_as_bool_none_and_garbage_fall_to_default():
    assert as_bool(None) is False
    assert as_bool(None, default=True) is True
    # 오타 토큰이 기본-켜짐 게이트를 끄지 않아야 한다.
    assert as_bool("ture", default=True) is True
    assert as_bool("maybe") is False


def test_as_optional_float_preserves_zero():
    assert as_optional_float(0) == 0.0
    assert as_optional_float("0") == 0.0
    assert as_optional_float(None) is None
    assert as_optional_float("") is None
    assert as_optional_float("  ") is None
    assert as_optional_float("abc") is None
    assert as_optional_float("1.5") == 1.5
    # bool을 1.0/0.0으로 승격하면 점수 필드가 silent하게 오염된다.
    assert as_optional_float(True) is None
    assert as_optional_float(False) is None


def test_config_manager_get_bool(tmp_path):
    cfg_file = tmp_path / "config.yaml"
    cfg_file.write_text(
        'twitter:\n  enabled: "false"\nviral_filter:\n  enabled: "ture"\n',
        encoding="utf-8",
    )
    config = ConfigManager(str(cfg_file))
    assert config.get_bool("twitter.enabled") is False
    assert config.get_bool("twitter.enabled", True) is False
    # 미인식 토큰은 호출측 default를 따른다.
    assert config.get_bool("viral_filter.enabled", True) is True
    assert config.get_bool("missing.key", True) is True
    assert config.get_bool("missing.key") is False


# ---------------------------------------------------------------------------
# 2. pipeline/ 로컬 재정의 금지
# ---------------------------------------------------------------------------


def test_no_local_as_bool_definitions_in_pipeline():
    offenders = []
    for path in (ROOT / "pipeline").rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == "_as_bool":
                offenders.append(f"{path.relative_to(ROOT)}:{node.lineno}")
    assert not offenders, (
        "pipeline 모듈은 로컬 _as_bool을 정의하지 말고 "
        f"`from config import as_bool as _as_bool`을 사용할 것: {offenders}"
    )


# ---------------------------------------------------------------------------
# 3. standalone scripts 사본의 동작 동치
# ---------------------------------------------------------------------------

SCRIPT_MODULES_WITH_AS_BOOL = [
    "scripts.notion_doctor",
    "scripts.review_experiment_dry_run",
    "scripts.source_preflight_evidence_doctor",
    "scripts.source_preflight_strategy_simulation",
]

EQUIVALENCE_MATRIX = TRUE_VALUES + FALSE_VALUES + [None, "maybe", "ture", 2, -0.0, [], ["x"], {}]


@pytest.mark.parametrize("module_name", SCRIPT_MODULES_WITH_AS_BOOL)
def test_script_as_bool_matches_canonical(module_name):
    import importlib

    module = importlib.import_module(module_name)
    script_as_bool = module._as_bool
    for value in EQUIVALENCE_MATRIX:
        assert script_as_bool(value) == as_bool(value), (
            f"{module_name}._as_bool({value!r}) != config.as_bool({value!r})"
        )


# ---------------------------------------------------------------------------
# 4. 잔존 raw-truthiness 지점 회귀 (string "false"가 게이트를 통과/차단하지 않는다)
# ---------------------------------------------------------------------------


class _DictConfig:
    """dotted-key config stub."""

    def __init__(self, values):
        self._values = values

    def get(self, key, default=None):
        return self._values.get(key, default)


def test_review_queue_missing_title_gate_respects_string_false():
    from pipeline.review_queue import build_review_decision

    config = _DictConfig(
        {
            "review.reject_on_missing_title": "false",
            "review.reject_on_missing_content": "false",
            "ranking.final_rank_min": 60,
        }
    )
    decision = build_review_decision(config, {"title": "", "content": ""}, {"final_rank_score": 90})
    assert decision["review_reason"] not in {"missing_title", "missing_content"}


def test_image_ab_variant_respects_string_false():
    from pipeline.process_stages.persist_stage import _inject_image_ab_variant

    config = _DictConfig({"image_ab_testing.enabled": "false"})
    post_data: dict = {"title": "t"}
    _inject_image_ab_variant(config, post_data, "topic", "emotion")
    assert "image_ab_variant" not in post_data
    assert post_data == {"title": "t"}


SCRIPT_MODULES_WITH_AS_FLOAT = [
    "scripts.build_weekly_report",
    "scripts.review_experiment_dry_run",
]

FLOAT_EQUIVALENCE_MATRIX = [None, "", "  ", 0, "0", 1.5, "1.5", " 2.5 ", "abc", True, False, -3, "−1", [], {}]


@pytest.mark.parametrize("module_name", SCRIPT_MODULES_WITH_AS_FLOAT)
def test_script_as_float_matches_canonical(module_name):
    import importlib

    module = importlib.import_module(module_name)
    for value in FLOAT_EQUIVALENCE_MATRIX:
        assert module._as_float(value) == as_optional_float(value), (
            f"{module_name}._as_float({value!r}) != config.as_optional_float({value!r})"
        )


def test_source_preflight_input_paths_implementations_identical():
    """trend report와 strategy simulation의 _input_paths 및 경로 헬퍼는
    동일 구현을 유지해야 한다 (loop 13/17/18에서 이 중복이 각각 어긋나 버그가 됐다)."""
    shared_helpers = ["_input_paths", "_resolve_explicit_input_path", "_unique_paths"]
    dumps = {}
    for rel in ("scripts/source_preflight_trend_report.py", "scripts/source_preflight_strategy_simulation.py"):
        tree = ast.parse((ROOT / rel).read_text(encoding="utf-8"))
        found = {
            node.name: ast.dump(node)
            for node in ast.walk(tree)
            if isinstance(node, ast.FunctionDef) and node.name in shared_helpers
        }
        assert set(found) == set(shared_helpers), f"{rel}에 {set(shared_helpers) - set(found)} 누락"
        dumps[rel] = found
    a, b = dumps.values()
    for name in shared_helpers:
        assert a[name] == b[name], f"{name} 구현이 두 스크립트 간에 어긋남"


POWERSHELL_QUOTE_MODULES = [
    "scripts.source_browser_probe",
    "scripts.source_preflight_evidence_doctor",
    "scripts.write_weekly_smoke_inputs",
]


def test_powershell_quote_helpers_equivalent():
    import importlib

    samples = [
        "",
        "plain",
        ".tmp/traces/source&preflight.zip",
        ".tmp/weekly smoke/manifest.json",
        "it's",
        "한글 경로/파일.json",
        "semi;colon|pipe",
    ]
    modules = [importlib.import_module(name) for name in POWERSHELL_QUOTE_MODULES]
    safe_sets = {frozenset(getattr(m, "SAFE_POWERSHELL_ARG_CHARS")) for m in modules}
    assert len(safe_sets) == 1, "SAFE_POWERSHELL_ARG_CHARS가 스크립트 간에 어긋남"
    for sample in samples:
        results = {m._quote_powershell_arg(sample) for m in modules}
        assert len(results) == 1, f"_quote_powershell_arg({sample!r}) 결과가 어긋남: {results}"
