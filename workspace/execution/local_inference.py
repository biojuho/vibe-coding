"""
Ollama 로컬 추론 클라이언트.

로컬에서 실행되는 Ollama 서버(http://localhost:11434)와 통신하여
오픈소스 모델(Qwen3-Coder 등)을 비용 없이 호출합니다.

Usage:
    from execution.local_inference import OllamaClient

    client = OllamaClient()
    if client.is_available():
        content, in_tok, out_tok = client.generate(
            system_prompt="...",
            user_prompt="...",
        )
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

WORKSPACE_ROOT = Path(__file__).resolve().parents[1]
if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT))

from execution._logging import logger  # noqa: E402

# ── 기본 설정 ────────────────────────────────────────────────

DEFAULT_OLLAMA_BASE_URL = "http://localhost:11434"
DEFAULT_OLLAMA_MODEL = "qwen3-coder:30b-a3b-q4_K_M"
OLLAMA_TIMEOUT_SEC = 180  # 코드 생성용 긴 추론 대비

# 소형 모델 대안 (VRAM 부족 시)
FALLBACK_MODELS = [
    "qwen3-coder:30b-a3b-q4_K_M",
    "qwen3-coder:8b",
    "deepseek-r1:14b",
    "deepseek-r1:8b",
    "qwen2.5-coder:7b",
    "codellama:7b",
]


class OllamaClient:
    """Ollama HTTP API 래퍼 클라이언트.

    로컬 Ollama 서버와 통신하여 비용 없는 추론을 제공합니다.
    ``/api/chat`` 엔드포인트를 사용하며, 스트리밍 없이 동기 호출합니다.
    """

    def __init__(
        self,
        *,
        base_url: str | None = None,
        default_model: str | None = None,
        timeout_sec: int = OLLAMA_TIMEOUT_SEC,
    ):
        self.base_url = (base_url or os.getenv("OLLAMA_BASE_URL", "").strip() or DEFAULT_OLLAMA_BASE_URL).rstrip("/")
        self.default_model = default_model or os.getenv("OLLAMA_DEFAULT_MODEL", "").strip() or DEFAULT_OLLAMA_MODEL
        self.timeout_sec = timeout_sec
        self._session = None

    @property
    def session(self):
        """Lazy ``requests.Session`` 초기화."""
        if self._session is None:
            import requests

            self._session = requests.Session()
            self._session.headers.update({"Content-Type": "application/json"})
        return self._session

    # ── 서버 상태 확인 ───────────────────────────────────────

    def is_available(self) -> bool:
        """Ollama 서버가 실행 중인지 확인.

        ``GET /api/tags`` 로 연결을 시도합니다.
        """
        try:
            resp = self.session.get(
                f"{self.base_url}/api/tags",
                timeout=5,
            )
            return resp.status_code == 200
        except Exception:
            return False

    def list_models(self) -> list[str]:
        """로컬에 설치된 모델 이름 목록을 반환합니다."""
        try:
            resp = self.session.get(
                f"{self.base_url}/api/tags",
                timeout=10,
            )
            resp.raise_for_status()
            data = resp.json()
            models = data.get("models", [])
            return [m.get("name", "") for m in models if m.get("name")]
        except Exception as e:
            logger.warning("Ollama 모델 목록 조회 실패: %s", e)
            return []

    def find_best_model(self) -> str:
        """로컬에 설치된 모델 중 최적 모델을 선택합니다.

        FALLBACK_MODELS 순서대로 탐색하여 첫 번째로 발견된 모델 반환.
        설치된 모델이 없으면 default_model 반환 (pull 필요).
        """
        available = self.list_models()
        if not available:
            return self.default_model

        for candidate in FALLBACK_MODELS:
            for installed in available:
                # Ollama는 보통 "model:tag" 형식
                if candidate in installed or installed.startswith(candidate.split(":")[0]):
                    return installed

        # FALLBACK_MODELS에 없는 모델이라도 하나 있으면 사용
        return available[0] if available else self.default_model

    # ── 추론 실행 ────────────────────────────────────────────

    def generate(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        model: str | None = None,
        temperature: float = 0.7,
        json_mode: bool = False,
    ) -> tuple[str, int, int]:
        """Ollama ``/api/chat`` 엔드포인트 호출.

        Args:
            system_prompt: 시스템 프롬프트
            user_prompt: 유저 프롬프트
            model: 모델 이름 (None이면 default_model 사용)
            temperature: 생성 온도
            json_mode: True면 JSON 형식 응답 요청

        Returns:
            (content, input_tokens, output_tokens)

        Raises:
            ConnectionError: Ollama 서버 연결 실패
            RuntimeError: 추론 실패
        """
        import requests

        model = model or self.default_model

        payload: dict[str, Any] = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "stream": False,
            "options": {
                "temperature": temperature,
            },
        }

        if json_mode:
            payload["format"] = "json"

        try:
            resp = self.session.post(
                f"{self.base_url}/api/chat",
                json=payload,
                timeout=self.timeout_sec,
            )
            resp.raise_for_status()
        except requests.ConnectionError as e:
            raise ConnectionError(
                f"Ollama 서버 연결 실패 ({self.base_url}). 서버가 실행 중인지 확인하세요: ollama serve"
            ) from e
        except requests.Timeout as e:
            raise RuntimeError(
                f"Ollama 타임아웃 ({self.timeout_sec}초). 모델이 너무 크거나 하드웨어가 부족할 수 있습니다."
            ) from e
        except requests.HTTPError as e:
            raise RuntimeError(f"Ollama HTTP 에러: {resp.status_code} - {resp.text}") from e

        data = resp.json()

        # 응답 추출
        message = data.get("message", {})
        content = message.get("content", "")

        # 토큰 사용량 추출
        input_tokens = data.get("prompt_eval_count", 0) or 0
        output_tokens = data.get("eval_count", 0) or 0

        if not content:
            raise RuntimeError(f"Ollama 빈 응답. 모델 '{model}'이 설치되어 있는지 확인하세요: ollama pull {model}")

        logger.info(
            "Ollama 추론 완료: model=%s, in=%d, out=%d",
            model,
            input_tokens,
            output_tokens,
        )

        return content, input_tokens, output_tokens

    # ── 편의 메서드 ──────────────────────────────────────────

    def generate_text(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        model: str | None = None,
        temperature: float = 0.7,
    ) -> str:
        """텍스트 응답만 반환하는 편의 메서드."""
        content, _, _ = self.generate(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            model=model,
            temperature=temperature,
            json_mode=False,
        )
        return content

    def generate_json(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        model: str | None = None,
        temperature: float = 0.7,
    ) -> dict[str, Any] | list[Any]:
        """JSON 응답을 파싱하여 반환하는 편의 메서드."""
        content, _, _ = self.generate(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            model=model,
            temperature=temperature,
            json_mode=True,
        )

        # 마크다운 코드블록 제거
        cleaned = content.strip()
        if cleaned.startswith("```json"):
            cleaned = cleaned[7:]
        elif cleaned.startswith("```"):
            cleaned = cleaned[3:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        cleaned = cleaned.strip()

        return json.loads(cleaned)

    def close(self) -> None:
        """세션 정리."""
        if self._session is not None:
            self._session.close()
            self._session = None


# ── CLI ──────────────────────────────────────────────────────


def _cli_main() -> None:
    """CLI 진입점: 연결 테스트 및 모델 확인."""
    import argparse

    parser = argparse.ArgumentParser(description="Ollama 로컬 추론 클라이언트")
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("status", help="서버 상태 및 모델 목록 확인")
    sub.add_parser("test", help="간단한 추론 테스트 실행")

    demo_parser = sub.add_parser("demo", help="데모 코드 생성")
    demo_parser.add_argument("--model", default=None, help="사용할 모델")

    args = parser.parse_args()
    client = OllamaClient()

    if args.command == "status":
        avail = client.is_available()
        print(f"Ollama 서버: {'✅ 실행 중' if avail else '❌ 연결 불가'}")
        print(f"Base URL: {client.base_url}")
        if avail:
            models = client.list_models()
            print(f"설치 모델: {len(models)}개")
            for m in models:
                print(f"  - {m}")
            best = client.find_best_model()
            print(f"추천 모델: {best}")

    elif args.command == "test":
        if not client.is_available():
            print("❌ Ollama 서버 연결 불가. 'ollama serve'를 먼저 실행하세요.")
            return

        print("간단한 코드 생성 테스트...")
        try:
            content, in_tok, out_tok = client.generate(
                system_prompt="You are a helpful coding assistant.",
                user_prompt="Write a Python function that computes the Fibonacci sequence up to n.",
                temperature=0.3,
            )
            print(f"✅ 성공! (입력: {in_tok} tokens, 출력: {out_tok} tokens)")
            print(f"--- 응답 ---\n{content[:500]}")
        except Exception as e:
            print(f"❌ 테스트 실패: {e}")

    elif args.command == "demo":
        if not client.is_available():
            print("❌ Ollama 서버 연결 불가.")
            return

        model = args.model or client.find_best_model()
        print(f"데모 실행 (모델: {model})...")
        try:
            content = client.generate_text(
                system_prompt="당신은 한국어로 답변하는 코딩 전문가입니다.",
                user_prompt="Python으로 퀵소트 알고리즘을 구현하고 설명해 주세요.",
                model=model,
                temperature=0.5,
            )
            print(f"--- 결과 ---\n{content}")
        except Exception as e:
            print(f"❌ 데모 실패: {e}")

    else:
        parser.print_help()


if __name__ == "__main__":
    _cli_main()
