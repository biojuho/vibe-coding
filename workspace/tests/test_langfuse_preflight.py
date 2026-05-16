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


def test_check_smoke_trace_uses_loaded_env_and_restores_process_env(monkeypatch):
    import os
    import types

    import execution.langfuse_preflight as preflight

    calls = []

    def fake_emit(**kwargs):
        calls.append(
            {
                "kwargs": kwargs,
                "env": {
                    "LANGFUSE_ENABLED": os.environ.get("LANGFUSE_ENABLED"),
                    "LANGFUSE_PUBLIC_KEY": os.environ.get("LANGFUSE_PUBLIC_KEY"),
                    "LANGFUSE_SECRET_KEY": os.environ.get("LANGFUSE_SECRET_KEY"),
                    "LANGFUSE_HOST": os.environ.get("LANGFUSE_HOST"),
                    "LANGFUSE_BASE_URL": os.environ.get("LANGFUSE_BASE_URL"),
                },
            }
        )

    monkeypatch.setitem(sys.modules, "execution.llm_client", types.SimpleNamespace(_emit_langfuse_trace=fake_emit))
    monkeypatch.setenv("LANGFUSE_ENABLED", "0")
    for key in ("LANGFUSE_PUBLIC_KEY", "LANGFUSE_SECRET_KEY", "LANGFUSE_HOST", "LANGFUSE_BASE_URL"):
        monkeypatch.delenv(key, raising=False)

    result = preflight.check_smoke_trace(
        "http://127.0.0.1:3030",
        {
            "LANGFUSE_PUBLIC_KEY": "pk-from-env-file",
            "LANGFUSE_SECRET_KEY": "sk-from-env-file",
            "LANGFUSE_HOST": "http://langfuse.local",
        },
    )

    assert result.status == "ok"
    assert calls[0]["kwargs"]["endpoint"] == "langfuse_preflight"
    assert calls[0]["env"] == {
        "LANGFUSE_ENABLED": "1",
        "LANGFUSE_PUBLIC_KEY": "pk-from-env-file",
        "LANGFUSE_SECRET_KEY": "sk-from-env-file",
        "LANGFUSE_HOST": "http://langfuse.local",
        "LANGFUSE_BASE_URL": "http://langfuse.local",
    }
    assert os.environ["LANGFUSE_ENABLED"] == "0"
    assert os.environ.get("LANGFUSE_PUBLIC_KEY") is None
    assert os.environ.get("LANGFUSE_SECRET_KEY") is None
    assert os.environ.get("LANGFUSE_HOST") is None
    assert os.environ.get("LANGFUSE_BASE_URL") is None


def test_check_smoke_trace_fails_when_keys_never_resolve(monkeypatch):
    import types

    import execution.langfuse_preflight as preflight

    calls = []
    monkeypatch.setitem(
        sys.modules,
        "execution.llm_client",
        types.SimpleNamespace(_emit_langfuse_trace=lambda **_kwargs: calls.append(True)),
    )
    for key in ("LANGFUSE_PUBLIC_KEY", "LANGFUSE_SECRET_KEY"):
        monkeypatch.delenv(key, raising=False)

    result = preflight.check_smoke_trace("http://127.0.0.1:3030", {})

    assert result.status == "fail"
    assert "LANGFUSE_PUBLIC_KEY" in result.detail
    assert "LANGFUSE_SECRET_KEY" in result.detail
    assert calls == []


def test_main_passes_loaded_env_to_smoke(monkeypatch, tmp_path):
    import execution.langfuse_preflight as preflight

    (tmp_path / ".env").write_text(
        "\n".join(
            [
                "LANGFUSE_PUBLIC_KEY=pk-from-dotenv",
                "LANGFUSE_SECRET_KEY=sk-from-dotenv",
                "LANGFUSE_HOST=http://langfuse.local",
            ]
        ),
        encoding="utf-8",
    )
    captured = {}

    monkeypatch.setattr(preflight, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(preflight, "check_sdk_installed", lambda: preflight.CheckResult("sdk_installed", "ok"))
    monkeypatch.setattr(preflight, "check_compose_config", lambda: preflight.CheckResult("compose_config", "skip"))
    monkeypatch.setattr(preflight, "check_health_endpoint", lambda host: preflight.CheckResult("health_endpoint", "ok"))

    def fake_smoke(host, env):
        captured["host"] = host
        captured["env"] = env
        return preflight.CheckResult("smoke_trace", "ok")

    monkeypatch.setattr(preflight, "check_smoke_trace", fake_smoke)

    assert preflight.main(["--json"]) == 0
    assert captured == {
        "host": "http://langfuse.local",
        "env": {
            "LANGFUSE_PUBLIC_KEY": "pk-from-dotenv",
            "LANGFUSE_SECRET_KEY": "sk-from-dotenv",
            "LANGFUSE_HOST": "http://langfuse.local",
        },
    }


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
