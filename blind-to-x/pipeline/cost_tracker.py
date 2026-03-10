"""Tracks estimated API usage and configurable provider costs.

Changes:
  - CostDatabase 연동: 비용 기록을 SQLite에 영속화
  - Telegram 알림: Gemini RPD 80% / 100% 도달 시 경고
"""

from __future__ import annotations

import logging
from pathlib import Path
import sys

logger = logging.getLogger(__name__)


DEFAULT_TEXT_PRICING = {
    "anthropic": {"input_per_1m": 0.80, "output_per_1m": 4.00},  # claude-haiku-4-5
    "openai": {"input_per_1m": 0.0, "output_per_1m": 0.0},
    "gemini": {"input_per_1m": 0.0, "output_per_1m": 0.0},
    "xai": {"input_per_1m": 0.0, "output_per_1m": 0.0},
    "deepseek": {"input_per_1m": 0.001, "output_per_1m": 0.002},
    "moonshot": {"input_per_1m": 0.003, "output_per_1m": 0.005},
    "zhipuai": {"input_per_1m": 0.002, "output_per_1m": 0.003},
}

DALLE3_COST_PER_IMAGE = 0.040
GEMINI_IMAGE_DAILY_LIMIT = 500
_GEMINI_RPD_WARN_THRESHOLD = 400   # 80% → Telegram 경고
_GEMINI_RPD_CRIT_THRESHOLD = 500   # 100% → Telegram 위험


def _try_send_telegram(message: str, level: str = "INFO") -> None:
    """루트 프로젝트 telegram_notifier로 Telegram 알림 전송 (실패 시 무시)."""
    try:
        _root = Path(__file__).resolve().parent.parent.parent
        if str(_root) not in sys.path:
            sys.path.insert(0, str(_root))
        from execution.telegram_notifier import is_configured, send_alert
        if is_configured():
            send_alert(message, level=level)
            logger.info("Telegram %s 알림 전송: %s", level, message[:60])
    except Exception as exc:
        logger.debug("Telegram 알림 전송 실패 (무시됨): %s", exc)


def _try_get_cost_db():
    """CostDatabase 인스턴스 반환. 실패 시 None (graceful degradation)."""
    try:
        from pipeline.cost_db import CostDatabase
        return CostDatabase()
    except Exception:
        try:
            from blind_to_x_cost_db import CostDatabase  # fallback alias
            return CostDatabase()
        except Exception:
            return None


class CostTracker:
    def __init__(self, config):
        self.config = config
        self.daily_budget = config.get("limits.daily_api_budget_usd", 3.0)
        self.current_cost = 0.0
        self.provider_calls = {provider: 0 for provider in DEFAULT_TEXT_PRICING}
        self.provider_tokens = {
            provider: {"input": 0, "output": 0} for provider in DEFAULT_TEXT_PRICING
        }
        self.dalle_calls = 0
        self.gemini_image_count = 0

        # CostDB 영속화 (실패 시 None → 인메모리만 유지)
        self._cost_db = _try_get_cost_db()
        if self._cost_db:
            self._load_persisted_totals()

        # Telegram 알림 중복 방지 (세션 내 1회)
        self._gemini_warn_sent = False
        self._gemini_crit_sent = False

    def _load_persisted_totals(self) -> None:
        try:
            summary = self._cost_db.get_today_summary()
            self.current_cost = float(summary.get("total_usd", 0.0) or 0.0)
            self.gemini_image_count = int(summary.get("gemini_image_count", 0) or 0)
            for provider in summary.get("providers", []):
                name = provider.get("provider")
                if not name:
                    continue
                self.provider_calls[name] = int(provider.get("calls", 0) or 0)
                self.provider_tokens[name] = {
                    "input": int(provider.get("tokens_input", 0) or 0),
                    "output": int(provider.get("tokens_output", 0) or 0),
                }
        except Exception as exc:
            logger.debug("Failed to load persisted cost totals: %s", exc)

    def _pricing_for(self, provider: str) -> dict[str, float]:
        configured = self.config.get(f"llm.pricing.{provider}", {}) or {}
        defaults = DEFAULT_TEXT_PRICING.get(provider, {"input_per_1m": 0.0, "output_per_1m": 0.0})
        return {
            "input_per_1m": float(configured.get("input_per_1m", defaults["input_per_1m"])),
            "output_per_1m": float(configured.get("output_per_1m", defaults["output_per_1m"])),
        }

    def add_text_generation_cost(self, provider: str, input_tokens: int = 0, output_tokens: int = 0):
        pricing = self._pricing_for(provider)
        cost = (input_tokens / 1_000_000) * pricing["input_per_1m"]
        cost += (output_tokens / 1_000_000) * pricing["output_per_1m"]
        self.current_cost += cost
        self.provider_calls.setdefault(provider, 0)
        self.provider_calls[provider] += 1
        self.provider_tokens.setdefault(provider, {"input": 0, "output": 0})
        self.provider_tokens[provider]["input"] += int(input_tokens or 0)
        self.provider_tokens[provider]["output"] += int(output_tokens or 0)
        logger.debug(
            "Added %s text generation cost: $%.5f. Total cost so far: $%.5f",
            provider,
            cost,
            self.current_cost,
        )
        # SQLite 영속화
        if self._cost_db:
            self._cost_db.record_text_cost(
                provider=provider,
                tokens_input=int(input_tokens or 0),
                tokens_output=int(output_tokens or 0),
                usd=cost,
            )

    def add_claude_cost(self, input_tokens: int, output_tokens: int):
        self.add_text_generation_cost("anthropic", input_tokens=input_tokens, output_tokens=output_tokens)

    def add_dalle_cost(self, num_images: int = 1):
        cost = num_images * DALLE3_COST_PER_IMAGE
        self.current_cost += cost
        self.dalle_calls += num_images
        logger.debug("Added DALL-E cost: $%.5f. Total cost so far: $%.5f", cost, self.current_cost)
        if self._cost_db:
            self._cost_db.record_image_cost(provider="dalle", image_count=num_images, usd=cost)

    def add_gemini_image_count(self, count: int = 1):
        self.gemini_image_count += count
        logger.debug(
            "Gemini image count: %d / %d (daily limit)",
            self.gemini_image_count,
            GEMINI_IMAGE_DAILY_LIMIT,
        )
        if self._cost_db:
            self._cost_db.record_image_cost(provider="gemini", image_count=count, usd=0.0)

        # ── Telegram 알림 (80% 경고 / 100% 위험) ────────────────────
        if not self._gemini_warn_sent and self.gemini_image_count >= _GEMINI_RPD_WARN_THRESHOLD:
            self._gemini_warn_sent = True
            _try_send_telegram(
                f"⚠️ [blind-to-x] Gemini 이미지 RPD 80% 도달\n"
                f"사용: {self.gemini_image_count}/{GEMINI_IMAGE_DAILY_LIMIT}장\n"
                f"잔여: {GEMINI_IMAGE_DAILY_LIMIT - self.gemini_image_count}장 → Pollinations으로 자동 전환 예정",
                level="WARNING"
            )

        if not self._gemini_crit_sent and self.gemini_image_count >= _GEMINI_RPD_CRIT_THRESHOLD:
            self._gemini_crit_sent = True
            _try_send_telegram(
                f"🚨 [blind-to-x] Gemini 이미지 일일 한도 소진!\n"
                f"사용: {self.gemini_image_count}/{GEMINI_IMAGE_DAILY_LIMIT}장\n"
                f"→ 이후 이미지는 Pollinations(무료) 폴백으로 생성됩니다.",
                level="CRITICAL"
            )

    def can_use_gemini_image(self) -> bool:
        """오늘 Gemini 이미지 한도(500장/일)가 남아 있는지 확인."""
        if self._cost_db:
            try:
                self.gemini_image_count = max(
                    self.gemini_image_count,
                    int(self._cost_db.get_gemini_image_count_today() or 0),
                )
            except Exception:
                pass
        return self.gemini_image_count < GEMINI_IMAGE_DAILY_LIMIT

    def is_budget_exceeded(self) -> bool:
        if self._cost_db:
            try:
                self.current_cost = max(
                    self.current_cost,
                    float(self._cost_db.get_today_summary().get("total_usd", 0.0) or 0.0),
                )
            except Exception:
                pass
        exceeded = self.current_cost >= self.daily_budget
        if exceeded:
            _try_send_telegram(
                f"🚨 [blind-to-x] 일일 API 예산 초과!\n"
                f"사용: ${self.current_cost:.3f} / 한도: ${self.daily_budget:.3f}",
                level="CRITICAL"
            )
        return exceeded

    def get_summary(self) -> str:
        provider_lines = []
        for provider, calls in sorted(self.provider_calls.items()):
            if calls <= 0:
                continue
            tokens = self.provider_tokens.get(provider, {"input": 0, "output": 0})
            provider_lines.append(
                f"- {provider}: {calls} calls (input={tokens['input']}, output={tokens['output']})"
            )
        if not provider_lines:
            provider_lines.append("- text providers: 0 calls")

        gemini_pct = self.gemini_image_count / GEMINI_IMAGE_DAILY_LIMIT * 100

        # 포스트당 평균 비용 (CostDB 연동)
        cost_per_post_line = ""
        if self._cost_db:
            try:
                cpp = self._cost_db.get_cost_per_post(days=30)
                cost_per_post_line = f"\n- Avg Cost/Post (30d): ${cpp['avg_cost_per_post']:.5f} ({cpp['total_posts']} posts)"
            except Exception:
                pass

        return (
            "API Cost Summary:\n"
            + "\n".join(provider_lines)
            + f"\n- DALL-E Calls: {self.dalle_calls}"
            + f"\n- Gemini Image Calls: {self.gemini_image_count} / {GEMINI_IMAGE_DAILY_LIMIT} ({gemini_pct:.1f}%)"
            + f"\n- Total Estimated Cost: ${self.current_cost:.3f} / ${self.daily_budget:.3f}"
            + f"\n- Budget Exceeded: {'Yes' if self.current_cost >= self.daily_budget else 'No'}"
            + cost_per_post_line
        )
