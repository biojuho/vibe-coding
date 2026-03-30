from __future__ import annotations

import re
import textwrap
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
EXAMPLE_CONFIG = ROOT / "config.example.yaml"
WORKFLOW_FILE = ROOT / ".github" / "workflows" / "blind-to-x.yml"


def _extract_generated_config_yaml(workflow_text: str) -> str:
    # 1. 헤어독 패턴 (레거시 방식)
    match = re.search(
        r"cat << '?YAML_EOF'? > config\.yaml\r?\n(?P<body>.*?)\r?\n\s*YAML_EOF",
        workflow_text,
        flags=re.DOTALL,
    )
    if match:
        return textwrap.dedent(match.group("body"))

    # 2. envsubst 방식: config.ci.yaml을 템플릿으로 사용
    if "envsubst" in workflow_text and "config.ci.yaml" in workflow_text:
        ci_config = ROOT / "config.ci.yaml"
        if ci_config.exists():
            return ci_config.read_text(encoding="utf-8")

    assert False, (
        "Workflow config generation step not found. "
        "Expected either a heredoc (cat << 'YAML_EOF' ... YAML_EOF) "
        "or envsubst < config.ci.yaml > config.yaml pattern."
    )


def _leaf_paths(obj: object, prefix: tuple[str, ...] = ()) -> set[str]:
    if isinstance(obj, dict):
        paths: set[str] = set()
        if not obj:
            paths.add(".".join(prefix))
            return paths
        for key, value in obj.items():
            paths |= _leaf_paths(value, prefix + (str(key),))
        return paths
    return {".".join(prefix)}


def _get_nested(obj: dict, path: str):
    cur = obj
    for part in path.split("."):
        assert isinstance(cur, dict), f"Expected dict while resolving {path}, got {type(cur)}"
        assert part in cur, f"Missing key: {path}"
        cur = cur[part]
    return cur


def test_workflow_generated_config_matches_example_keyset():
    example_cfg = yaml.safe_load(EXAMPLE_CONFIG.read_text(encoding="utf-8"))
    workflow_yaml = _extract_generated_config_yaml(WORKFLOW_FILE.read_text(encoding="utf-8"))
    workflow_cfg = yaml.safe_load(workflow_yaml)

    example_keys = _leaf_paths(example_cfg)
    workflow_keys = _leaf_paths(workflow_cfg)

    missing = sorted(example_keys - workflow_keys)
    extra = sorted(workflow_keys - example_keys)
    assert not missing and not extra, f"Keyset mismatch.\nmissing_in_workflow={missing}\nextra_in_workflow={extra}"


def test_workflow_generated_config_contains_notion_url_property():
    workflow_yaml = _extract_generated_config_yaml(WORKFLOW_FILE.read_text(encoding="utf-8"))
    workflow_cfg = yaml.safe_load(workflow_yaml)
    assert workflow_cfg["notion"]["properties"]["url"]


def test_workflow_generated_config_required_values_non_empty():
    workflow_yaml = _extract_generated_config_yaml(WORKFLOW_FILE.read_text(encoding="utf-8"))
    workflow_cfg = yaml.safe_load(workflow_yaml)

    required_paths = [
        "notion.properties.url",
        "notion.properties.title",
        "request.timeout_seconds",
        "scrape_quality.min_content_length",
    ]
    for path in required_paths:
        value = _get_nested(workflow_cfg, path)
        assert value not in ("", None), f"Required value is empty: {path}"


def test_workflow_runs_tests_before_pipeline():
    """데이터 정확도 테스트가 파이프라인 스텝보다 먼저 실행돼야 합니다."""
    workflow_cfg = yaml.safe_load(WORKFLOW_FILE.read_text(encoding="utf-8"))
    steps = workflow_cfg["jobs"]["run-pipeline"]["steps"]
    names = [step.get("name", "") for step in steps]

    test_idx = names.index("Run data accuracy tests")
    # "Run pipeline"으로 시작하는 첫 번째 파이프라인 스텝의 인덱스
    pipeline_idx = next(i for i, name in enumerate(names) if name.startswith("Run pipeline"))
    assert test_idx < pipeline_idx, "Run data accuracy tests must be before Run pipeline"


def test_workflow_pipeline_uses_valid_feed_mode():
    """각 파이프라인 스텝이 --trending 또는 --popular 중 하나를 반드시 사용해야 합니다."""
    workflow_cfg = yaml.safe_load(WORKFLOW_FILE.read_text(encoding="utf-8"))
    steps = workflow_cfg["jobs"]["run-pipeline"]["steps"]
    pipeline_steps = [s for s in steps if s.get("name", "").startswith("Run pipeline")]
    assert pipeline_steps, "파이프라인 실행 스텝이 없습니다."
    for step in pipeline_steps:
        run_cmd = step.get("run", "")
        assert "--trending" in run_cmd or "--popular" in run_cmd, (
            f"스텝 '{step.get('name')}': --trending 또는 --popular 중 하나가 필요합니다."
        )
