"""Discord webhook notification manager."""

import asyncio
import logging
import os
import sys
from pathlib import Path
from typing import Any

import requests

logger = logging.getLogger(__name__)

# Try to import telegram_notifier from execution/
try:
    root_dir = Path(__file__).resolve().parent.parent.parent.parent
    workspace_dir = root_dir / "workspace"
    if str(workspace_dir) not in sys.path:
        sys.path.insert(0, str(workspace_dir))
    from execution.telegram_notifier import send_alert as telegram_send_alert

    TELEGRAM_AVAILABLE = True
except ImportError:
    TELEGRAM_AVAILABLE = False


class NotificationManager:
    def __init__(self, config):
        self.webhook_url = os.environ.get("DISCORD_WEBHOOK_URL") or config.get("discord.webhook_url")

    async def send_message(self, message: str, level: str = "INFO", reply_markup: dict | None = None):
        if TELEGRAM_AVAILABLE and telegram_send_alert:
            try:
                loop = asyncio.get_running_loop()
                telegram_kwargs = {"level": level}
                if reply_markup is not None:
                    telegram_kwargs["reply_markup"] = reply_markup
                await loop.run_in_executor(None, lambda: telegram_send_alert(message, **telegram_kwargs))
            except Exception as e:
                logger.error(f"Failed to send Telegram notification: {e}")

        if not self.webhook_url:
            return

        prefixes = {
            "CRITICAL": "🚨 [CRITICAL]",
            "WARNING": "⚠️ [WARNING]",
            "INFO": "ℹ️ [INFO]",
        }
        prefix = prefixes.get(level.upper(), "ℹ️ [INFO]")
        discord_message = f"{prefix}\n{message}"

        repo = os.environ.get("GITHUB_REPOSITORY")
        run_id = os.environ.get("GITHUB_RUN_ID")
        server_url = os.environ.get("GITHUB_SERVER_URL", "https://github.com")
        if repo and run_id:
            run_url = f"{server_url}/{repo}/actions/runs/{run_id}"
            discord_message += f"\n\n🔍 **[보기: GitHub Actions 로그]({run_url})**"

        payload = {"content": discord_message}
        try:
            loop = asyncio.get_running_loop()
            response = await loop.run_in_executor(
                None, lambda: requests.post(self.webhook_url, json=payload, timeout=10)
            )
            if response.status_code >= 400:
                logger.error(f"Discord webhook failed: {response.text}")
            else:
                logger.debug("Discord notification sent.")
        except Exception as e:
            logger.error(f"Failed to send Discord notification: {e}")

    # ── Viral Escalation Engine 전용 알림 ────────────────────────────

    async def send_surge_alert(
        self,
        event: Any,
        draft_x: str = "",
        draft_threads: str = "",
        generation_time: float = 0.0,
    ) -> bool:
        """Surge 스파이크 알림 전송.

        Args:
            event: QueuedEvent 또는 SpikeEvent (title, source, velocity_score 필수).
            draft_x: X(트위터) 초안.
            draft_threads: Threads 초안.
            generation_time: 초안 생성 소요 시간 (초).

        Returns:
            전송 성공 여부.
        """
        source_label = {
            "blind": "블라인드",
            "ppomppu": "뽐뿌",
            "fmkorea": "에펨코리아",
            "jobplanet": "잡플래닛",
        }.get(getattr(event, "source", ""), getattr(event, "source", "unknown"))

        v_score = getattr(event, "velocity_score", 0.0)
        title = getattr(event, "title", "제목 없음")
        url = getattr(event, "url", "")

        # 이모지 등급
        if v_score >= 20:
            level_emoji = "🔥🔥🔥"
        elif v_score >= 10:
            level_emoji = "🔥🔥"
        else:
            level_emoji = "🔥"

        lines = [
            f"{level_emoji} *SURGE ALERT* {level_emoji}",
            "",
            f"📍 *소스*: {source_label}",
            f"📄 *제목*: {title}",
            f"⚡ *속도점수*: {v_score:.1f}",
        ]
        if url:
            lines.append(f"🔗 {url}")

        if draft_x:
            lines.extend(["", "━━ X 초안 ━━", draft_x])
        if draft_threads:
            lines.extend(["", "━━ Threads 초안 ━━", draft_threads])

        if generation_time > 0:
            lines.extend(["", f"⏱ 생성시간: {generation_time:.1f}초"])

        # 텔레그램 inline keyboard 1-click 승인 버튼 추가
        # event_id는 반드시 정수형 식별자(DB ID)를 사용해야 텔레그램 콜백 데이터 길이 제한(64 byte)을 넘지 않음.
        # [QA 수정] DB ID 사용으로 ValueError 예방 및 최적화
        event_id = getattr(event, "id", None)
        if not event_id:
            event_id = hash(getattr(event, "url", getattr(event, "event_key", "mock"))) % 100000

        keyboard = {
            "inline_keyboard": [
                [
                    {"text": "✅ 발행 승인", "callback_data": f"approve_{event_id}"},
                    {"text": "❌ 거부 (폐기)", "callback_data": f"reject_{event_id}"},
                ]
            ]
        }

        message = "\n".join(lines)
        try:
            await self.send_message(message, level="WARNING", reply_markup=keyboard)
            return True
        except Exception as exc:
            logger.error("Surge 알림 전송 실패: %s", exc)
            return False
