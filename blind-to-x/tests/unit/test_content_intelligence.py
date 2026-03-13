from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pipeline.content_intelligence import build_content_profile  # noqa: E402


def test_build_content_profile_is_deterministic():
    post_data = {
        "title": "이직 고민하는데 팀장 때문에 현타 왔다",
        "content": "회사 문화랑 팀장 스타일 때문에 퇴사를 고민하는 직장인 공감 글입니다.",
        "likes": 120,
        "comments": 24,
    }
    examples = [
        {
            "views": 12000,
            "topic_cluster": "이직",
            "hook_type": "공감형",
            "emotion_axis": "현타",
            "draft_style": "공감형",
            "text": "예시",
        }
    ]
    first = build_content_profile(post_data, 88, examples).to_dict()
    second = build_content_profile(post_data, 88, examples).to_dict()
    assert first == second
    assert first["topic_cluster"] == "이직"
    assert first["recommended_draft_type"] == "공감형"
    assert first["final_rank_score"] >= 60


def test_build_content_profile_uses_examples_for_performance_score():
    post_data = {
        "title": "연봉 협상 망해서 현타 온다",
        "content": "연봉 인상률이 낮아 허탈한 직장인 이야기입니다.",
        "likes": 80,
        "comments": 12,
    }
    matching_examples = [
        {
            "views": 22000,
            "topic_cluster": "연봉",
            "hook_type": "공감형",
            "emotion_axis": "허탈",
            "draft_style": "공감형",
            "text": "예시",
        }
    ]
    mismatching_examples = [
        {
            "views": 22000,
            "topic_cluster": "가족",
            "hook_type": "정보형",
            "emotion_axis": "통찰",
            "draft_style": "정보전달형",
            "text": "예시",
        }
    ]
    matched = build_content_profile(post_data, 82, matching_examples).to_dict()
    mismatched = build_content_profile(post_data, 82, mismatching_examples).to_dict()
    assert matched["performance_score"] > mismatched["performance_score"]
