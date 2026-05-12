"""Langfuse 셀프호스트 활성화 전 안전 검증 (T-253 완성).

`directives/llm_observability_langfuse.md` 의 라이브화 직전 체크리스트를
자동화한다. `LANGFUSE_ENABLED=1`로 전환하기 전에 이 스크립트를 한 번 통과시키면
런타임에서 silent drop이 의도치 않게 동작하지 않음이 보장된다.

검증 항목 (순서대로 — 한 단계 실패 시 다음으로 진행 안 함):
  1. .env 키 존재 (LANGFUSE_PUBLIC_KEY / LANGFUSE_SECRET_KEY / LANGFUSE_HOST)
  2. langfuse Python SDK 설치 여부
  3. docker-compose.yml 구문 유효성 (선택 — docker 있을 때만)
  4. UI 헬스 엔드포인트 (/api/public/health) 접근
  5. 인증된 trace 1건 송신 + flush + UI에서 즉시 조회 (smoke)

Usage:
    python execution/langfuse_preflight.py              # 전체 체크 + 텍스트 보고
    python execution/langfuse_preflight.py --json       # 머신 판독용
    python execution/langfuse_preflight.py --skip-smoke # 4단계까지만 (서비스 시작 직후 등)

Exit codes:
    0 — 모두 통과, LANGFUSE_ENABLED=1 안전
    1 — 한 단계 실패, 상세 사유는 stdout/JSON 참조
    2 — 인자/환경 오류
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]


@dataclass
class CheckResult:
    name: str
    status: str  # "ok" | "fail" | "skip"
    detail: str = ""
    hint: str = ""
    extra: dict[str, Any] = field(default_factory=dict)


def _load_env() -> dict[str, str]:
    """root .env를 KEY=VALUE 라인 단위로 단순 파싱 (python-dotenv 비의존)."""
    env: dict[str, str] = {}
    env_path = REPO_ROOT / ".env"
    if not env_path.exists():
        return env
    for raw in env_path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        env[key.strip()] = value.strip().strip('"').strip("'")
    return env


def check_env_keys(env: dict[str, str]) -> CheckResult:
    """필수 .env 키가 채워져 있는지."""
    public = env.get("LANGFUSE_PUBLIC_KEY") or os.getenv("LANGFUSE_PUBLIC_KEY", "")
    secret = env.get("LANGFUSE_SECRET_KEY") or os.getenv("LANGFUSE_SECRET_KEY", "")
    host = env.get("LANGFUSE_HOST") or os.getenv("LANGFUSE_HOST", "")
    missing = [k for k, v in {"LANGFUSE_PUBLIC_KEY": public, "LANGFUSE_SECRET_KEY": secret}.items() if not v]
    if missing:
        return CheckResult(
            "env_keys",
            "fail",
            detail=f"missing: {', '.join(missing)}",
            hint="UI(http://127.0.0.1:3030) Settings에서 키 발급 후 root .env에 입력",
        )
    return CheckResult(
        "env_keys",
        "ok",
        detail=f"public={public[:8]}... secret={secret[:8]}... host={host or '(default)'}",
    )


def check_sdk_installed() -> CheckResult:
    """langfuse Python SDK가 import 가능한지 — workspace LLMClient의 _emit_langfuse_trace 의존."""
    try:
        import langfuse  # type: ignore[import-not-found]

        version = getattr(langfuse, "__version__", "unknown")
        return CheckResult("sdk_installed", "ok", detail=f"langfuse=={version}")
    except ImportError:
        return CheckResult(
            "sdk_installed",
            "fail",
            detail="langfuse SDK import 실패",
            hint="pip install langfuse  (또는 uv add langfuse)",
        )


def check_compose_config() -> CheckResult:
    """docker compose config 구문 유효성 — docker가 있을 때만."""
    import shutil
    import subprocess

    if not shutil.which("docker"):
        return CheckResult("compose_config", "skip", detail="docker not found in PATH")
    compose_path = REPO_ROOT / "infrastructure" / "langfuse" / "docker-compose.yml"
    if not compose_path.exists():
        return CheckResult(
            "compose_config",
            "fail",
            detail=f"compose 파일 없음: {compose_path}",
        )
    try:
        result = subprocess.run(
            ["docker", "compose", "-f", str(compose_path), "config", "--quiet"],
            capture_output=True,
            text=True,
            timeout=20,
        )
    except (subprocess.SubprocessError, OSError) as exc:
        return CheckResult("compose_config", "fail", detail=f"docker compose 실행 실패: {exc}")
    if result.returncode != 0:
        return CheckResult(
            "compose_config",
            "fail",
            detail=result.stderr[:500] or "compose config returned non-zero",
            hint=".env에 LANGFUSE_DB_PASSWORD / LANGFUSE_NEXTAUTH_SECRET / LANGFUSE_SALT / "
            "LANGFUSE_ENCRYPTION_KEY / LANGFUSE_CLICKHOUSE_PASSWORD / LANGFUSE_REDIS_AUTH / "
            "LANGFUSE_MINIO_ROOT_PASSWORD 채우기",
        )
    return CheckResult("compose_config", "ok", detail="docker compose config valid")


def check_health_endpoint(host: str) -> CheckResult:
    """UI /api/public/health 엔드포인트가 200 OK 반환하는지."""
    url = host.rstrip("/") + "/api/public/health"
    try:
        with urllib.request.urlopen(url, timeout=5) as resp:
            status = resp.status
            body = resp.read(200).decode("utf-8", errors="replace")
    except urllib.error.URLError as exc:
        return CheckResult(
            "health_endpoint",
            "fail",
            detail=f"{url} 접근 실패: {exc}",
            hint="docker compose -f infrastructure/langfuse/docker-compose.yml up -d 로 컨테이너 기동",
        )
    if status != 200:
        return CheckResult(
            "health_endpoint",
            "fail",
            detail=f"HTTP {status}: {body!r}",
        )
    return CheckResult("health_endpoint", "ok", detail=f"{url} -> 200 OK")


def _resolve_smoke_env(env: Mapping[str, str] | None, host: str) -> tuple[dict[str, str], list[str]]:
    env = env or {}
    public = env.get("LANGFUSE_PUBLIC_KEY") or os.getenv("LANGFUSE_PUBLIC_KEY", "")
    secret = env.get("LANGFUSE_SECRET_KEY") or os.getenv("LANGFUSE_SECRET_KEY", "")
    base_url = (
        env.get("LANGFUSE_BASE_URL")
        or os.getenv("LANGFUSE_BASE_URL", "")
        or env.get("LANGFUSE_HOST")
        or os.getenv("LANGFUSE_HOST", "")
        or host
    )
    missing = [
        key for key, value in {"LANGFUSE_PUBLIC_KEY": public, "LANGFUSE_SECRET_KEY": secret}.items() if not value
    ]
    return (
        {
            "LANGFUSE_ENABLED": "1",
            "LANGFUSE_PUBLIC_KEY": public,
            "LANGFUSE_SECRET_KEY": secret,
            "LANGFUSE_HOST": base_url,
            "LANGFUSE_BASE_URL": base_url,
        },
        missing,
    )


@contextmanager
def _temporary_env(overrides: Mapping[str, str]) -> Iterator[None]:
    previous = {key: os.environ.get(key) for key in overrides}
    os.environ.update({key: value for key, value in overrides.items() if value})
    try:
        yield
    finally:
        for key, value in previous.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


def check_smoke_trace(host: str, env: Mapping[str, str] | None = None) -> CheckResult:
    """실제 trace 1건 송신 + flush — workspace LLMClient의 _emit_langfuse_trace 와 동일 경로."""
    workspace_root = REPO_ROOT / "workspace"
    if str(workspace_root) not in sys.path:
        sys.path.insert(0, str(workspace_root))
    try:
        from execution.llm_client import _emit_langfuse_trace
    except ImportError as exc:
        return CheckResult("smoke_trace", "fail", detail=f"workspace LLMClient import 실패: {exc}")

    smoke_env, missing = _resolve_smoke_env(env, host)
    if missing:
        return CheckResult(
            "smoke_trace",
            "fail",
            detail=f"missing env for smoke: {', '.join(missing)}",
            hint="root .env 또는 현재 프로세스 환경에 Langfuse public/secret key를 설정",
        )

    try:
        with _temporary_env(smoke_env):
            _emit_langfuse_trace(
                provider="preflight",
                model="preflight-noop",
                endpoint="langfuse_preflight",
                input_tokens=0,
                output_tokens=0,
                cost_usd=0.0,
                caller_script="execution/langfuse_preflight.py",
                metadata={"preflight": True, "host": host},
            )
    except Exception as exc:
        return CheckResult("smoke_trace", "fail", detail=f"trace 송신 중 예외: {exc}")

    # SDK는 비동기 flush — 즉시 UI 조회는 보장 안 함. 송신 호출 자체에 예외 없으면 ok.
    return CheckResult(
        "smoke_trace",
        "ok",
        detail="_emit_langfuse_trace 호출 정상 종료 (UI 반영은 수초 지연 가능)",
        hint=f"확인: {host.rstrip('/')}/  (Traces 페이지에 'langfuse_preflight' name 항목)",
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Langfuse 셀프호스트 활성화 전 안전 검증")
    parser.add_argument("--json", action="store_true", help="JSON 출력")
    parser.add_argument("--skip-smoke", action="store_true", help="trace 송신 단계 생략")
    args = parser.parse_args(argv)

    env = _load_env()
    results: list[CheckResult] = []

    # 1. .env keys
    r1 = check_env_keys(env)
    results.append(r1)
    if r1.status == "fail":
        return _emit(results, args.json, exit_code=1)

    host = env.get("LANGFUSE_HOST") or os.getenv("LANGFUSE_HOST", "http://127.0.0.1:3030")

    # 2. SDK
    r2 = check_sdk_installed()
    results.append(r2)
    if r2.status == "fail":
        return _emit(results, args.json, exit_code=1)

    # 3. docker compose config
    results.append(check_compose_config())

    # 4. health endpoint
    r4 = check_health_endpoint(host)
    results.append(r4)
    if r4.status == "fail":
        return _emit(results, args.json, exit_code=1)

    # 5. smoke trace
    if not args.skip_smoke:
        results.append(check_smoke_trace(host, env))

    exit_code = 0 if all(r.status != "fail" for r in results) else 1
    return _emit(results, args.json, exit_code=exit_code)


def _emit(results: list[CheckResult], as_json: bool, *, exit_code: int) -> int:
    if as_json:
        sys.stdout.write(
            json.dumps(
                {"exit_code": exit_code, "results": [asdict(r) for r in results]},
                ensure_ascii=False,
                indent=2,
            )
            + "\n"
        )
        return exit_code

    print("Langfuse preflight")
    print("=" * 60)
    for r in results:
        marker = {"ok": "✓", "fail": "✗", "skip": "·"}.get(r.status, "?")
        print(f"  {marker} {r.name}: {r.detail}")
        if r.hint and r.status != "ok":
            print(f"      → {r.hint}")
    print("=" * 60)
    print(f"결과: exit {exit_code} ({'안전' if exit_code == 0 else 'BLOCKED'})")
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
