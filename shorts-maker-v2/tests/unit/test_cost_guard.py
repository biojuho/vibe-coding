from __future__ import annotations

from shorts_maker_v2.config import CostTable
from shorts_maker_v2.utils.cost_guard import CostGuard


def test_cost_guard_video_downgrade_condition() -> None:
    guard = CostGuard(
        max_cost_usd=0.2,
        price_table=CostTable(
            llm_per_job=0.1,
            tts_per_second=0.001,
            veo_per_second=0.03,
            image_per_scene=0.04,
        ),
    )
    guard.add_llm_cost()
    guard.add_tts_cost(10)
    assert guard.can_use_video(2) is True
    assert guard.can_use_video(4) is False


def test_cost_guard_tracks_total() -> None:
    guard = CostGuard(
        max_cost_usd=2.0,
        price_table=CostTable(
            llm_per_job=0.25,
            tts_per_second=0.001,
            veo_per_second=0.03,
            image_per_scene=0.04,
        ),
    )
    guard.add_llm_cost()
    guard.add_tts_cost(30)
    guard.add_image_cost()
    assert guard.estimated_cost_usd > 0.3


# ─── Phase 2-A: atomic check-then-add ─────────────────────────────────────


def test_add_video_cost_if_under_accepts() -> None:
    """Under limit → adds cost and returns True."""
    guard = CostGuard(
        max_cost_usd=1.0,
        price_table=CostTable(llm_per_job=0.1, tts_per_second=0.001, veo_per_second=0.03, image_per_scene=0.04),
    )
    assert guard.add_video_cost_if_under(5.0) is True
    assert guard.estimated_cost_usd == round(5.0 * 0.03, 6)


def test_add_video_cost_if_under_rejects() -> None:
    """Over limit → returns False without adding cost."""
    guard = CostGuard(
        max_cost_usd=0.1,
        price_table=CostTable(llm_per_job=0.1, tts_per_second=0.001, veo_per_second=0.03, image_per_scene=0.04),
    )
    guard.add_llm_cost()  # 0.1 → at limit
    before = guard.estimated_cost_usd
    assert guard.add_video_cost_if_under(5.0) is False
    assert guard.estimated_cost_usd == before  # unchanged


def test_add_image_cost_if_under_accepts() -> None:
    guard = CostGuard(
        max_cost_usd=1.0,
        price_table=CostTable(llm_per_job=0.1, tts_per_second=0.001, veo_per_second=0.03, image_per_scene=0.04),
    )
    assert guard.add_image_cost_if_under() is True
    assert guard.estimated_cost_usd == 0.04


def test_add_image_cost_if_under_rejects() -> None:
    guard = CostGuard(
        max_cost_usd=0.03,
        price_table=CostTable(llm_per_job=0.1, tts_per_second=0.001, veo_per_second=0.03, image_per_scene=0.04),
    )
    assert guard.add_image_cost_if_under() is False
    assert guard.estimated_cost_usd == 0.0
