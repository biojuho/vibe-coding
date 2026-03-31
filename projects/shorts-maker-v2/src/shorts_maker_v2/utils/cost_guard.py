from __future__ import annotations

import threading
from dataclasses import dataclass

from shorts_maker_v2.config import CostTable


@dataclass
class CostEvent:
    stage: str
    amount_usd: float
    total_usd: float


class CostGuard:
    def __init__(self, max_cost_usd: float, price_table: CostTable):
        if max_cost_usd <= 0:
            raise ValueError("max_cost_usd must be > 0.")
        self.max_cost_usd = max_cost_usd
        self.price_table = price_table
        self.estimated_cost_usd = 0.0
        self.events: list[CostEvent] = []
        self._lock = threading.Lock()

    def _add(self, stage: str, amount_usd: float) -> float:
        amount = round(float(amount_usd), 6)
        with self._lock:
            self.estimated_cost_usd = round(self.estimated_cost_usd + amount, 6)
            self.events.append(CostEvent(stage=stage, amount_usd=amount, total_usd=self.estimated_cost_usd))
        return amount

    def add_llm_cost(self) -> float:
        return self._add("llm", self.price_table.llm_per_job)

    def add_tts_cost(self, duration_sec: float) -> float:
        return self._add("tts", duration_sec * self.price_table.tts_per_second)

    def add_video_cost(self, duration_sec: float) -> float:
        return self._add("video", duration_sec * self.price_table.veo_per_second)

    def add_image_cost(self) -> float:
        return self._add("image", self.price_table.image_per_scene)

    def add_stock_cost(self) -> float:
        return self._add("stock_video", self.price_table.stock_per_scene)

    def projected_video_cost(self, duration_sec: float) -> float:
        return round(duration_sec * self.price_table.veo_per_second, 6)

    def projected_image_cost(self) -> float:
        return round(self.price_table.image_per_scene, 6)

    def can_use_video(self, duration_sec: float) -> bool:
        projected = self.projected_video_cost(duration_sec)
        with self._lock:
            return (self.estimated_cost_usd + projected) <= self.max_cost_usd

    def add_video_cost_if_under(self, duration_sec: float) -> bool:
        """Atomic check-then-add for video cost. Returns True if added."""
        amount = round(duration_sec * self.price_table.veo_per_second, 6)
        with self._lock:
            if (self.estimated_cost_usd + amount) > self.max_cost_usd:
                return False
            self.estimated_cost_usd = round(self.estimated_cost_usd + amount, 6)
            self.events.append(CostEvent(stage="video", amount_usd=amount, total_usd=self.estimated_cost_usd))
        return True

    def add_image_cost_if_under(self) -> bool:
        """Atomic check-then-add for image cost. Returns True if added."""
        amount = round(self.price_table.image_per_scene, 6)
        with self._lock:
            if (self.estimated_cost_usd + amount) > self.max_cost_usd:
                return False
            self.estimated_cost_usd = round(self.estimated_cost_usd + amount, 6)
            self.events.append(CostEvent(stage="image", amount_usd=amount, total_usd=self.estimated_cost_usd))
        return True

    def is_over_limit(self) -> bool:
        with self._lock:
            return self.estimated_cost_usd > self.max_cost_usd
