"""Discord webhook notification manager."""

import asyncio
import logging
import os
import sys
from pathlib import Path

import requests

logger = logging.getLogger(__name__)

# Try to import telegram_notifier from execution/
try:
    root_dir = Path(__file__).resolve().parent.parent.parent
    if str(root_dir) not in sys.path:
        sys.path.insert(0, str(root_dir))
    from execution.telegram_notifier import send_alert as telegram_send_alert
    TELEGRAM_AVAILABLE = True
except ImportError:
    TELEGRAM_AVAILABLE = False


class NotificationManager:
    def __init__(self, config):
        self.webhook_url = os.environ.get("DISCORD_WEBHOOK_URL") or config.get("discord.webhook_url")

    async def send_message(self, message: str, level: str = "INFO"):
        if TELEGRAM_AVAILABLE and telegram_send_alert:
            try:
                loop = asyncio.get_running_loop()
                await loop.run_in_executor(None, lambda: telegram_send_alert(message, level=level))
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
