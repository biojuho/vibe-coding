from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pipeline.content_intelligence import (  # noqa: E402
    build_content_profile,
    calculate_publishability_score,
    evaluate_candidate_editorial_fit,
)


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


def test_build_content_profile_exposes_editorial_brief_fields():
    post_data = {
        "title": "실수령 280 듣고 회의실이 조용해진 날",
        "content": "회의실에서 실수령 280 이야기가 나오자 다들 웃다가도 한숨을 쉬었다. 연봉 비교와 이직 고민이 한 번에 터지는 글이다.",
        "likes": 95,
        "comments": 21,
        "source": "blind",
    }
    profile = build_content_profile(post_data, 90, historical_examples=[]).to_dict()

    assert profile["selection_summary"]
    assert profile["selection_reason_labels"]
    assert profile["audience_need"]
    assert profile["emotion_lane"]
    assert profile["empathy_anchor"]
    assert profile["spinoff_angle"]
    assert profile["publishability_score"] >= 60


def test_evaluate_candidate_editorial_fit_preserves_scoring_dimensions():
    result = evaluate_candidate_editorial_fit(
        title="실수령 280 듣고 회의실이 조용해진 날",
        source="blind",
        content="회의실에서 실수령 280 이야기가 나오자 다들 웃다가도 한숨을 쉬었다. 연봉 비교와 이직 고민이 한 번에 터지는 글이다.",
    )

    assert result["score"] == 91.75
    assert result["dimensions"] == {
        "reader_desire": 100.0,
        "empathy_fun": 90.0,
        "spinoff": 100.0,
        "specificity": 75.0,
        "workplace_fit": 80.0,
    }
    assert result["hard_reject"] is False
    assert result["reason_labels"] == [
        "직장인이 바로 눌러볼 만한 주제",
        "공감하거나 웃을 장면이 분명함",
        "댓글과 파생 대화로 이어질 각이 있음",
        "숫자·대사·상황이 구체적임",
        "직장인 독자 맥락에 정확히 맞음",
    ]


def test_calculate_publishability_score_returns_brief_from_editorial_fit():
    post_data = {
        "title": "실수령 280 듣고 회의실이 조용해진 날",
        "content": "회의실에서 실수령 280 이야기가 나오자 다들 웃다가도 한숨을 쉬었다. 연봉 비교와 이직 고민이 한 번에 터지는 글이다.",
        "source": "blind",
        "likes": 95,
        "comments": 21,
    }

    score, rationale, brief = calculate_publishability_score(
        post_data,
        topic_cluster="연봉",
        hook_type="공감형",
        emotion_axis="공감",
    )

    assert score >= 60.0
    assert rationale
    assert brief["selection_summary"]
    assert brief["selection_reason_labels"] == rationale
    assert set(brief["editorial_dimensions"]) == {
        "reader_desire",
        "empathy_fun",
        "spinoff",
        "specificity",
        "workplace_fit",
    }
