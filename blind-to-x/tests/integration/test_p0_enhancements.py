"""P0 Enhancement Tests: content_intelligence & draft_generator YAML integration."""

from __future__ import annotations

import pytest
from unittest.mock import patch

# ── content_intelligence tests ──────────────────────────────────────────────


def test_get_season_boost_returns_float():
    """get_season_boost returns a float between 0 and 15."""
    from pipeline.content_intelligence import get_season_boost

    result = get_season_boost("연봉", month=1)
    assert isinstance(result, float)
    assert 0.0 <= result <= 15.0


def test_get_season_boost_known_topic():
    """For a topic in season_weights, returns positive boost."""
    from pipeline.content_intelligence import get_season_boost

    # 1월 연봉 시즌 → 반드시 양수
    boost = get_season_boost("연봉", month=1)
    assert boost > 0, "1월 연봉 시즌 부스트는 0보다 커야 합니다."


def test_get_season_boost_unknown_topic():
    """For a topic NOT in season_weights, returns 0.0."""
    from pipeline.content_intelligence import get_season_boost

    boost = get_season_boost("존재하지않는토픽", month=6)
    assert boost == 0.0


def test_get_season_boost_auto_month():
    """get_season_boost with month=None uses current month without error."""
    from pipeline.content_intelligence import get_season_boost

    boost = get_season_boost("이직", month=None)
    assert isinstance(boost, float)


def test_classify_topic_cluster_new_topics():
    """New topics (부동산, IT, 건강, 정치, 자기계발) are classified correctly."""
    from pipeline.content_intelligence import classify_topic_cluster

    # 부동산 전용 키워드: 아파트, 전세, 월세, 청약, 집값
    assert classify_topic_cluster("아파트 청약 당첨", "아파트 분양 매매") == "부동산"
    # IT 전용 키워드: 코딩, 프로그래밍, 데이터
    assert classify_topic_cluster("코딩 테스트 준비", "프로그래밍 데이터 분석") == "IT"
    # 건강 전용 키워드: 헬스, 다이어트, 수면
    assert classify_topic_cluster("헬스 다이어트", "수면 부족 스트레스") == "건강"


def test_classify_emotion_axis_new_emotions():
    """New emotions (자부심, 불안, 기대감) are classified correctly."""
    from pipeline.content_intelligence import classify_emotion_axis
    from unittest.mock import patch

    with patch("pipeline.emotion_analyzer.get_emotion_profile", side_effect=Exception("Mock ML disabled")):
        assert classify_emotion_axis("자부심 넘침", "뿌듯하고 자랑스러운 성과") == "자부심"
        assert classify_emotion_axis("불안한 미래", "걱정되고 불안한 노후") == "불안"
        assert classify_emotion_axis("기대감 폭발", "설레고 기대되는 결과") == "기대감"


def test_calculate_6d_score_with_season_boost():
    """calculate_6d_score incorporates season boost into trend_relevance_score."""
    from pipeline.content_intelligence import calculate_6d_score

    post = {
        "title": "연봉 인상 소식",
        "content": "올해 연봉이 크게 올랐다는 소식",
        "likes": 50,
        "comments": 20,
    }
    # 1월은 연봉 시즌 → trend_relevance가 더 높아야 함
    with patch("pipeline.content_intelligence.get_season_boost", return_value=10.0):
        rank_6d_boosted, dims_boosted = calculate_6d_score(post, "연봉", "공감형", "공감", "전직장인")

    with patch("pipeline.content_intelligence.get_season_boost", return_value=0.0):
        rank_6d_base, dims_base = calculate_6d_score(post, "연봉", "공감형", "공감", "전직장인")

    assert dims_boosted["trend_relevance_score"] >= dims_base["trend_relevance_score"]
    assert rank_6d_boosted >= rank_6d_base


# ── draft_generator tests ──────────────────────────────────────────────────


def test_resolve_tone_yaml_topic():
    """_resolve_tone returns YAML-based tone for known topic_cluster."""
    from pipeline.content_intelligence import _load_rules
    from pipeline.draft_generator import TweetDraftGenerator, _load_draft_rules

    rules = _load_draft_rules()
    tone_map = rules.get("tone_mapping", {})
    if not tone_map:
        pytest.skip("No tone_mapping in YAML")

    # Create a minimal config mock
    class FakeConfig:
        def get(self, key, default=None):
            return default

    gen = TweetDraftGenerator(FakeConfig())
    post_data = {
        "content_profile": {"topic_cluster": "연봉"},
        "category": "general",
    }
    result = gen._resolve_tone(post_data)
    expected = tone_map.get("연봉", "")
    if expected:
        assert result == expected


def test_resolve_tone_fallback_category():
    """_resolve_tone falls back to category-based tone when topic not in YAML."""
    from pipeline.draft_generator import TweetDraftGenerator

    class FakeConfig:
        def get(self, key, default=None):
            return default

    gen = TweetDraftGenerator(FakeConfig())
    post_data = {
        "content_profile": {"topic_cluster": "없는토픽"},
        "category": "relationship",
    }
    result = gen._resolve_tone(post_data)
    assert "공감" in result or "다정" in result


def test_format_examples_with_golden():
    """_format_examples merges golden examples from YAML with top_examples."""
    from pipeline.draft_generator import TweetDraftGenerator, _load_draft_rules

    rules = _load_draft_rules()
    golden = rules.get("golden_examples", {})
    if not golden:
        pytest.skip("No golden_examples in YAML")

    topic = list(golden.keys())[0]
    result = TweetDraftGenerator._format_examples(
        top_examples=None,
        topic_cluster=topic,
    )
    assert "골든 예시" in result
    assert "등급:" in result


def test_format_examples_empty():
    """_format_examples returns empty string when no examples."""
    from pipeline.draft_generator import TweetDraftGenerator

    result = TweetDraftGenerator._format_examples(
        top_examples=None,
        topic_cluster="없는토픽",
    )
    assert result == ""


def test_build_prompt_has_yaml_system_role():
    """_build_prompt uses system_role from YAML when available."""
    from pipeline.draft_generator import TweetDraftGenerator, _load_draft_rules

    class FakeConfig:
        def get(self, key, default=None):
            return default

    gen = TweetDraftGenerator(FakeConfig())
    post_data = {
        "title": "테스트 제목",
        "content": "테스트 본문 내용",
        "category": "career",
        "source": "블라인드",
        "likes": 10,
        "comments": 5,
        "content_profile": {
            "topic_cluster": "이직",
            "hook_type": "공감형",
            "emotion_axis": "공감",
            "audience_fit": "이직준비층",
            "recommended_draft_type": "공감형",
            "publishability_score": 75,
            "performance_score": 60,
        },
    }
    prompt = gen._build_prompt(post_data, None, ["twitter"])

    rules = _load_draft_rules()
    system_role = rules.get("prompt_templates", {}).get("system_role", "")
    if system_role:
        assert system_role in prompt


def test_parse_response_thread():
    """_parse_response parses <twitter_thread> tags correctly."""
    from pipeline.draft_generator import TweetDraftGenerator

    class FakeConfig:
        def get(self, key, default=None):
            return default

    gen = TweetDraftGenerator(FakeConfig())
    response = """
<twitter_thread>
1/3 첫 번째 트윗입니다.
2/3 두 번째 트윗입니다.
3/3 세 번째 트윗입니다.
</twitter_thread>
<image_prompt>A tired office worker</image_prompt>
"""
    drafts, img = gen._parse_response(response, ["twitter"], "test")
    assert "twitter_thread" in drafts
    assert "twitter" in drafts
    assert "1/3" in drafts["twitter_thread"]
    assert img == "A tired office worker"


def test_parse_response_standard():
    """_parse_response still handles standard <twitter> tags."""
    from pipeline.draft_generator import TweetDraftGenerator

    class FakeConfig:
        def get(self, key, default=None):
            return default

    gen = TweetDraftGenerator(FakeConfig())
    response = "<twitter>공감형: 오늘도 고생한 직장인들</twitter><image_prompt>office</image_prompt>"
    drafts, img = gen._parse_response(response, ["twitter"], "anthropic")
    assert drafts["twitter"] == "공감형: 오늘도 고생한 직장인들"
    assert img == "office"
