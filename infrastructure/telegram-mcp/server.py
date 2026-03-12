"""
Telegram MCP Server - FastMCP 기반 텔레그램 봇 API 서버.

Joolife Hub의 텔레그램 알림 시스템을 MCP 프로토콜로 노출합니다.
TELEGRAM_BOT_TOKEN과 TELEGRAM_CHAT_ID 환경 변수가 필요합니다.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict

import requests
from dotenv import load_dotenv

try:
    from mcp.server.fastmcp import FastMCP
except ImportError:
    FastMCP = None

# 프로젝트 루트의 .env 로드
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
load_dotenv(_PROJECT_ROOT / ".env")

TELEGRAM_API_BASE = "https://api.telegram.org"
TELEGRAM_MESSAGE_LIMIT = 4096


def _get_token() -> str:
    """봇 토큰을 환경 변수에서 가져옵니다."""
    token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    if not token:
        raise ValueError("TELEGRAM_BOT_TOKEN 환경 변수가 설정되지 않았습니다.")
    return token


def _get_chat_id() -> str:
    """채팅 ID를 환경 변수에서 가져옵니다."""
    chat_id = os.getenv("TELEGRAM_CHAT_ID", "").strip()
    if not chat_id:
        raise ValueError("TELEGRAM_CHAT_ID 환경 변수가 설정되지 않았습니다.")
    return chat_id


def _api_url(method: str) -> str:
    """텔레그램 Bot API URL을 생성합니다."""
    return f"{TELEGRAM_API_BASE}/bot{_get_token()}/{method}"


def _check_response(response: requests.Response) -> Dict[str, Any]:
    """텔레그램 API 응답을 검증하고 JSON을 반환합니다."""
    response.raise_for_status()
    payload = response.json()
    if not payload.get("ok"):
        description = payload.get("description", "텔레그램 API 요청 실패")
        raise RuntimeError(f"Telegram API 오류: {description}")
    return payload


def _truncate_text(text: str, limit: int = TELEGRAM_MESSAGE_LIMIT) -> str:
    """텔레그램 메시지 길이 제한에 맞게 텍스트를 자릅니다."""
    if len(text) <= limit:
        return text
    return text[: limit - 3].rstrip() + "..."


# ---------------------------------------------------------------------------
# 도구 함수 (MCP 유무와 무관하게 사용 가능)
# ---------------------------------------------------------------------------


def _send_message(text: str, parse_mode: str = "HTML") -> Dict[str, Any]:
    """설정된 채팅으로 텍스트 메시지를 전송합니다."""
    clean_text = (text or "").strip()
    if not clean_text:
        raise ValueError("메시지 텍스트가 비어있습니다.")

    truncated = _truncate_text(clean_text)
    payload: Dict[str, Any] = {"chat_id": _get_chat_id(), "text": truncated}
    if parse_mode:
        payload["parse_mode"] = parse_mode

    response = requests.post(_api_url("sendMessage"), json=payload, timeout=15)
    return _check_response(response)


def _send_photo(image_path: str, caption: str = "") -> Dict[str, Any]:
    """설정된 채팅으로 이미지를 캡션과 함께 전송합니다."""
    path = Path(image_path)
    if not path.exists():
        raise FileNotFoundError(f"이미지 파일을 찾을 수 없습니다: {image_path}")
    if not path.is_file():
        raise ValueError(f"경로가 파일이 아닙니다: {image_path}")

    data: Dict[str, Any] = {"chat_id": _get_chat_id()}
    if caption:
        data["caption"] = _truncate_text(caption.strip(), limit=1024)

    with open(path, "rb") as f:
        files = {"photo": (path.name, f, "image/jpeg")}
        response = requests.post(
            _api_url("sendPhoto"), data=data, files=files, timeout=30
        )

    return _check_response(response)


def _get_updates(limit: int = 10) -> Dict[str, Any]:
    """봇이 수신한 최근 업데이트(메시지)를 조회합니다."""
    clamped_limit = max(1, min(int(limit), 100))
    response = requests.get(
        _api_url("getUpdates"),
        params={"limit": clamped_limit, "timeout": 0},
        timeout=15,
    )
    return _check_response(response)


def _get_bot_info() -> Dict[str, Any]:
    """봇의 사용자 이름과 정보를 조회합니다."""
    response = requests.get(_api_url("getMe"), timeout=15)
    return _check_response(response)


# ---------------------------------------------------------------------------
# MCP 서버 등록
# ---------------------------------------------------------------------------

if FastMCP is not None:
    mcp = FastMCP(
        "telegram",
        instructions="텔레그램 봇 API MCP 서버 - 메시지 전송, 사진 전송, 업데이트 조회",
    )

    @mcp.tool()
    def send_message(text: str, parse_mode: str = "HTML") -> Dict[str, Any]:
        """설정된 채팅으로 텍스트 메시지를 전송합니다.

        Args:
            text: 전송할 메시지 텍스트 (최대 4096자, 초과 시 자동 잘림)
            parse_mode: 메시지 파싱 모드 ("HTML", "Markdown", "MarkdownV2")
        """
        return _send_message(text, parse_mode)

    @mcp.tool()
    def send_photo(image_path: str, caption: str = "") -> Dict[str, Any]:
        """설정된 채팅으로 이미지를 캡션과 함께 전송합니다.

        Args:
            image_path: 전송할 이미지 파일의 절대 경로
            caption: 이미지에 첨부할 캡션 (최대 1024자)
        """
        return _send_photo(image_path, caption)

    @mcp.tool()
    def get_updates(limit: int = 10) -> Dict[str, Any]:
        """봇이 수신한 최근 업데이트(메시지)를 조회합니다.

        Args:
            limit: 가져올 업데이트 수 (1~100, 기본값 10)
        """
        return _get_updates(limit)

    @mcp.tool()
    def get_bot_info() -> Dict[str, Any]:
        """봇의 사용자 이름과 정보를 조회합니다."""
        return _get_bot_info()

else:
    mcp = None
    send_message = _send_message
    send_photo = _send_photo
    get_updates = _get_updates
    get_bot_info = _get_bot_info


if __name__ == "__main__":
    if mcp is None:
        print("mcp 패키지 미설치. pip install 'mcp[cli]' 후 다시 실행하세요.")
    else:
        mcp.run()
