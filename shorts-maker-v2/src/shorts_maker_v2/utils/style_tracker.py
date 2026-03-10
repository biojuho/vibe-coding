"""Phase 4-E: A/B style performance tracker.

Scans past job manifests to compute success rates per hook_pattern
and caption_combo. Provides weighted random selection for ScriptStep
and RenderStep to favor historically successful styles.

Usage:
    tracker = StyleTracker(output_dir)
    best_pattern = tracker.weighted_pick("hook_pattern", ["질문형", "충격형", "공감형"])
"""
from __future__ import annotations

import json
import logging
import random
from collections import Counter
from pathlib import Path
from typing import Sequence

logger = logging.getLogger(__name__)


class StyleTracker:
    """Reads past manifests and computes style success rates."""

    def __init__(self, output_dir: Path, max_manifests: int = 200):
        self._output_dir = Path(output_dir)
        self._max_manifests = max_manifests
        self._stats: dict[str, Counter] = {}
        self._loaded = False

    def _load(self) -> None:
        if self._loaded:
            return
        self._loaded = True
        if not self._output_dir.exists():
            return
        manifests = sorted(
            self._output_dir.glob("*_manifest.json"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )[: self._max_manifests]

        for mf in manifests:
            try:
                data = json.loads(mf.read_text(encoding="utf-8"))
                status = data.get("status", "")
                ab_variant = data.get("ab_variant", {})
                if not ab_variant:
                    continue
                for key, value in ab_variant.items():
                    if key not in self._stats:
                        self._stats[key] = Counter()
                    if status == "success":
                        self._stats[key][str(value)] += 1
                    else:
                        # Track failures with negative weight
                        self._stats[key][str(value)] += 0
            except Exception:
                continue

        if self._stats:
            logger.debug("StyleTracker loaded %d manifests, keys=%s", len(manifests), list(self._stats.keys()))

    def get_success_counts(self, key: str) -> dict[str, int]:
        """Return {variant_name: success_count} for given A/B key."""
        self._load()
        return dict(self._stats.get(key, {}))

    def weighted_pick(self, key: str, candidates: Sequence[str], min_data: int = 5) -> str:
        """Select from candidates weighted by past success rate.

        Falls back to uniform random if insufficient data (<min_data total runs).
        """
        self._load()
        counts = self._stats.get(key, Counter())
        total = sum(counts.values())

        if total < min_data or not candidates:
            return random.choice(candidates) if candidates else ""

        # Build weights: success_count + 1 (Laplace smoothing)
        weights = [counts.get(str(c), 0) + 1 for c in candidates]
        return random.choices(candidates, weights=weights, k=1)[0]
