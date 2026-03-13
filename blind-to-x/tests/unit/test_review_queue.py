from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pipeline.review_queue import build_review_decision  # noqa: E402


class FakeConfig:
    def __init__(self):
        self.data = {
            "ranking": {"final_rank_min": 60},
            "review": {
                "auto_move_to_review_threshold": 65,
                "reject_on_missing_title": True,
                "reject_on_missing_content": True,
            },
        }

    def get(self, key, default=None):
        cur = self.data
        for part in key.split("."):
            if isinstance(cur, dict):
                cur = cur.get(part)
            else:
                return default
        return default if cur is None else cur


def test_build_review_decision_accepts_ranked_items():
    decision = build_review_decision(
        FakeConfig(),
        {"title": "제목", "content": "본문"},
        {"final_rank_score": 78},
    )
    assert decision["should_queue"] is True
    assert decision["review_status"] == "검토필요"


def test_build_review_decision_rejects_missing_content():
    decision = build_review_decision(
        FakeConfig(),
        {"title": "제목", "content": ""},
        {"final_rank_score": 90},
    )
    assert decision["should_queue"] is False
    assert decision["review_reason"] == "missing_content"


def test_build_review_decision_rejects_below_threshold():
    decision = build_review_decision(
        FakeConfig(),
        {"title": "제목", "content": "본문"},
        {"final_rank_score": 50},
    )
    assert decision["should_queue"] is False
    assert decision["review_reason"] == "final_rank_below_threshold"
