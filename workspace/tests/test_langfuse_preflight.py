"""execution/langfuse_preflight.py 회귀 테스트 (T-253 완성).

라이브 도커/네트워크 호출 없이 순수 함수만 검증한다.
"""

from __future__ import annotations

import sys
from pathlib import Path

# repo root 의 execution/ 을 import 가능하게
REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))


def test_check_env_keys_pass():
    from execution.langfuse_preflight import check_env_keys

    env = {
        "LANGFUSE_PUBLIC_KEY": "pk-test-abcdef",
        "LANGFUSE_SECRET_KEY": "sk-test-123456",
        "LANGFUSE_HOST": "http://127.0.0.1:3030",
    }
    r = check_env_keys(env)
    assert r.status == "ok"
    assert "pk-test-" in r.detail
    # secret key는 prefix만 노출 (보안)
    assert "sk-test-123456" not in r.detail


def test_check_env_keys_missing_public(monkeypatch):
    from execution.langfuse_preflight import check_env_keys

    monkeypatch.delenv("LANGFUSE_PUBLIC_KEY", raising=False)
    env = {
        "LANGFUSE_PUBLIC_KEY": "",
        "LANGFUSE_SECRET_KEY": "sk-test",
    }
    r = check_env_keys(env)
    assert r.status == "fail"
    assert "LANGFUSE_PUBLIC_KEY" in r.detail


def test_check_env_keys_missing_secret(monkeypatch):
    from execution.langfuse_preflight import check_env_keys

    monkeypatch.delenv("LANGFUSE_SECRET_KEY", raising=False)
    env = {
        "LANGFUSE_PUBLIC_KEY": "pk-test",
        "LANGFUSE_SECRET_KEY": "",
    }
    r = check_env_keys(env)
    assert r.status == "fail"
    assert "LANGFUSE_SECRET_KEY" in r.detail


def test_check_health_endpoint_url_construction():
    """헬스 URL이 host에 /api/public/health 를 정확히 붙이는지 (trailing slash 양쪽 처리)."""
    from execution.langfuse_preflight import check_health_endpoint

    # 실제 호출은 실패하지만, 실패 메시지에 URL이 그대로 노출되어야 함.
    r = check_health_endpoint("http://127.0.0.1:65535")  # 사용 안 하는 포트
    assert r.status == "fail"
    assert "/api/public/health" in r.detail

    r_with_trailing = check_health_endpoint("http://127.0.0.1:65535/")
    assert r_with_trailing.status == "fail"
    # trailing slash가 있더라도 //api 가 되지 않아야 함
    assert "//api" not in r_with_trailing.detail


def test_check_sdk_installed_smoke():
    """SDK 설치 여부와 무관하게 함수가 예외 없이 결과를 반환하는지."""
    from execution.langfuse_preflight import check_sdk_installed

    r = check_sdk_installed()
    # 둘 다 valid outcome
    assert r.status in {"ok", "fail"}
    if r.status == "fail":
        assert "pip install langfuse" in r.hint


def test_emit_json_payload(capsys):
    """--json 출력이 valid JSON 인지."""
    import json

    from execution.langfuse_preflight import CheckResult, _emit

    results = [
        CheckResult("env_keys", "ok", detail="ok"),
        CheckResult("sdk_installed", "fail", detail="missing", hint="pip install langfuse"),
    ]
    exit_code = _emit(results, as_json=True, exit_code=1)
    assert exit_code == 1
    captured = capsys.readouterr().out
    payload = json.loads(captured)
    assert payload["exit_code"] == 1
    assert len(payload["results"]) == 2
    assert payload["results"][0]["name"] == "env_keys"
    assert payload["results"][1]["status"] == "fail"


def test_main_no_env_returns_fail(monkeypatch, tmp_path):
    """LANGFUSE_PUBLIC_KEY 가 모두 비어있으면 1단계에서 즉시 종료해 fail 반환."""
    import execution.langfuse_preflight as preflight

    monkeypatch.setattr(preflight, "REPO_ROOT", tmp_path)  # .env 없는 디렉터리
    monkeypatch.delenv("LANGFUSE_PUBLIC_KEY", raising=False)
    monkeypatch.delenv("LANGFUSE_SECRET_KEY", raising=False)

    exit_code = preflight.main(["--json", "--skip-smoke"])
    assert exit_code == 1
