"""
Telegram MCP Server - FastMCP 기반 텔레그램 봇 API 서버.

Joolife Hub의 텔레그램 알림 시스템을 MCP 프로토콜로 노출합니다.
TELEGRAM_BOT_TOKEN과 TELEGRAM_CHAT_ID 환경 변수가 필요합니다.
"""

from __future__ import annotations

import logging
import mimetypes
import os
from pathlib import Path
from typing import Any

import requests
from dotenv import load_dotenv

try:
    from mcp.server.fastmcp import FastMCP
except ImportError:
    FastMCP = None

# 프로젝트 루트의 .env 로드
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
load_dotenv(_PROJECT_ROOT / ".env")

logger = logging.getLogger(__name__)

TELEGRAM_API_BASE = "https://api.telegram.org"
TELEGRAM_MESSAGE_LIMIT = 4096

# env vars를 시작 시 1회 읽기
_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "").strip()

# HTTP 세션 재사용 (TCP 연결 풀링)
_session = requests.Session()


def _api_url(method: str) -> str:
    """텔레그램 Bot API URL을 생성합니다."""
    if not _BOT_TOKEN:
        raise ValueError("TELEGRAM_BOT_TOKEN 환경 변수가 설정되지 않았습니다.")
    return f"{TELEGRAM_API_BASE}/bot{_BOT_TOKEN}/{method}"


def _get_chat_id() -> str:
    """채팅 ID를 반환합니다."""
    if not _CHAT_ID:
        raise ValueError("TELEGRAM_CHAT_ID 환경 변수가 설정되지 않았습니다.")
    return _CHAT_ID


def _check_response(response: requests.Response) -> dict[str, Any]:
    """텔레그램 API 응답을 검증하고 JSON을 반환합니다."""
    response.raise_for_status()
    payload = response.json()
    if not payload.get("ok"):
        description = payload.get("description", "텔레그램 API 요청 실패")
        return {"error": f"Telegram API 오류: {description}"}
    return payload


def _truncate_text(text: str, limit: int = TELEGRAM_MESSAGE_LIMIT) -> str:
    """텔레그램 메시지 길이 제한에 맞게 텍스트를 자릅니다."""
    if len(text) <= limit:
        return text
    return text[: limit - 3].rstrip() + "..."


# ---------------------------------------------------------------------------
# 도구 함수
# ---------------------------------------------------------------------------


def _send_message(text: str, parse_mode: str = "HTML") -> dict[str, Any]:
    """설정된 채팅으로 텍스트 메시지를 전송합니다."""
    try:
        clean_text = (text or "").strip()
        if not clean_text:
            return {"error": "메시지 텍스트가 비어있습니다."}

        truncated = _truncate_text(clean_text)
        payload: dict[str, Any] = {"chat_id": _get_chat_id(), "text": truncated}
        if parse_mode:
            payload["parse_mode"] = parse_mode

        response = _session.post(_api_url("sendMessage"), json=payload, timeout=15)
        return _check_response(response)
    except Exception as e:
        logger.error("메시지 전송 실패: %s", e)
        return {"error": f"메시지 전송 실패: {e}"}


def _send_photo(image_path: str, caption: str = "") -> dict[str, Any]:
    """설정된 채팅으로 이미지를 캡션과 함께 전송합니다."""
    try:
        path = Path(image_path)
        data: dict[str, Any] = {"chat_id": _get_chat_id()}
        if caption:
            data["caption"] = _truncate_text(caption.strip(), limit=1024)

        mime_type = mimetypes.guess_type(str(path))[0] or "application/octet-stream"

        with open(path, "rb") as f:
            files = {"photo": (path.name, f, mime_type)}
            response = _session.post(
                _api_url("sendPhoto"), data=data, files=files, timeout=30
            )

        return _check_response(response)
    except Exception as e:
        logger.error("사진 전송 실패: %s", e)
        return {"error": f"사진 전송 실패: {e}"}


def _get_updates(limit: int = 10) -> dict[str, Any]:
    """봇이 수신한 최근 업데이트(메시지)를 조회합니다."""
    try:
        clamped_limit = max(1, min(int(limit), 100))
        response = _session.get(
            _api_url("getUpdates"),
            params={"limit": clamped_limit, "timeout": 0},
            timeout=15,
        )
        return _check_response(response)
    except Exception as e:
        logger.error("업데이트 조회 실패: %s", e)
        return {"error": f"업데이트 조회 실패: {e}"}


def _get_bot_info() -> dict[str, Any]:
    """봇의 사용자 이름과 정보를 조회합니다."""
    try:
        response = _session.get(_api_url("getMe"), timeout=15)
        return _check_response(response)
    except Exception as e:
        logger.error("봇 정보 조회 실패: %s", e)
        return {"error": f"봇 정보 조회 실패: {e}"}


# ---------------------------------------------------------------------------
# MCP 서버 등록
# ---------------------------------------------------------------------------

if FastMCP is not None:
    mcp = FastMCP(
        "telegram",
        instructions="텔레그램 봇 API MCP 서버 - 메시지 전송, 사진 전송, 업데이트 조회",
    )

    @mcp.tool()
    def send_message(text: str, parse_mode: str = "HTML") -> dict[str, Any]:
        """설정된 채팅으로 텍스트 메시지를 전송합니다.

        Args:
            text: 전송할 메시지 텍스트 (최대 4096자, 초과 시 자동 잘림)
            parse_mode: 메시지 파싱 모드 ("HTML", "Markdown", "MarkdownV2")
        """
        return _send_message(text, parse_mode)

    @mcp.tool()
    def send_photo(image_path: str, caption: str = "") -> dict[str, Any]:
        """설정된 채팅으로 이미지를 캡션과 함께 전송합니다.

        Args:
            image_path: 전송할 이미지 파일의 절대 경로
            caption: 이미지에 첨부할 캡션 (최대 1024자)
        """
        return _send_photo(image_path, caption)

    @mcp.tool()
    def get_updates(limit: int = 10) -> dict[str, Any]:
        """봇이 수신한 최근 업데이트(메시지)를 조회합니다.

        Args:
            limit: 가져올 업데이트 수 (1~100, 기본값 10)
        """
        return _get_updates(limit)

    @mcp.tool()
    def get_bot_info() -> dict[str, Any]:
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
