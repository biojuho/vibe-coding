"""P2 확장 기능 단위 테스트."""
import pytest


# ── A-3: 이미지 프롬프트 자동 빌드 ──────────────────────────────────


class TestBuildImagePrompt:
    """토픽/감정 기반 이미지 프롬프트 테스트."""

    def test_topic_style_applied(self):
        from pipeline.image_generator import ImageGenerator
        prompt = ImageGenerator.build_image_prompt(topic_cluster="연봉")
        assert "infographic" in prompt.lower()
        assert "Korean office workers" in prompt

    def test_emotion_override(self):
        from pipeline.image_generator import ImageGenerator
        prompt = ImageGenerator.build_image_prompt(topic_cluster="이직", emotion_axis="분노")
        assert "intense" in prompt.lower() or "frustrated" in prompt.lower()

    def test_title_hint_included(self):
        from pipeline.image_generator import ImageGenerator
        prompt = ImageGenerator.build_image_prompt(
            topic_cluster="IT",
            title="개발자 연봉 인상 꿀팁 공개",
        )
        assert "개발자" in prompt or "futuristic" in prompt.lower()

    def test_default_style_for_unknown_topic(self):
        from pipeline.image_generator import ImageGenerator
        prompt = ImageGenerator.build_image_prompt(topic_cluster="알수없는토픽")
        assert "modern illustration" in prompt.lower()

    def test_all_topics_have_styles(self):
        from pipeline.image_generator import _TOPIC_IMAGE_STYLES
        expected_topics = ["연봉", "이직", "회사문화", "상사", "복지", "부동산", "IT", "건강", "정치", "자기계발"]
        for topic in expected_topics:
            assert topic in _TOPIC_IMAGE_STYLES, f"{topic} 스타일 매핑 누락"

    def test_empty_inputs_still_works(self):
        from pipeline.image_generator import ImageGenerator
        prompt = ImageGenerator.build_image_prompt()
        assert len(prompt) > 10  # 빈 입력이어도 유효한 프롬프트 생성


# ── C-1: 뉴스레터 고도화 ────────────────────────────────────────────


class TestNewsletterNewMappings:
    """신규 토픽/감정 매핑 테스트."""

    def test_new_topics_have_insight(self):
        from pipeline.newsletter_formatter import _INSIGHT_BY_TOPIC
        for topic in ["부동산", "IT", "건강", "정치", "자기계발"]:
            assert topic in _INSIGHT_BY_TOPIC, f"{topic} 인사이트 매핑 누락"

    def test_new_emotions_have_cta(self):
        from pipeline.newsletter_formatter import _CTA_BY_EMOTION
        for emotion in ["자부심", "불안", "기대감"]:
            assert emotion in _CTA_BY_EMOTION, f"{emotion} CTA 매핑 누락"

    def test_new_topic_in_format(self):
        from pipeline.newsletter_formatter import format_newsletter
        result = format_newsletter(
            draft_text="개발자 연봉 1억 시대가 왔다. 하지만 모든 개발자가 그런건 아니다.",
            profile={"topic_cluster": "IT", "emotion_axis": "통찰", "hook_type": "정보형"},
        )
        assert len(result.full_text) > 50


class TestFormatForBlog:
    """블로그 포맷 변환 테스트."""

    def test_naver_format(self):
        from pipeline.newsletter_formatter import format_for_blog, format_newsletter
        nl = format_newsletter(
            draft_text="연봉 5천 자랑글 밑에 댓글이 레전드",
            profile={"topic_cluster": "연봉", "emotion_axis": "공감", "hook_type": "공감형"},
        )
        blog = format_for_blog(nl, platform="naver")
        assert "[직장인 라이프]" in blog
        assert "#연봉" in blog
        assert "#블라인드" in blog

    def test_brunch_format(self):
        from pipeline.newsletter_formatter import format_for_blog, format_newsletter
        nl = format_newsletter(
            draft_text="퇴사 결심하니까 갑자기 다 보여요",
            profile={"topic_cluster": "이직", "emotion_axis": "현타", "hook_type": "공감형"},
        )
        blog = format_for_blog(nl, platform="brunch")
        assert "# " in blog  # Markdown heading
        assert "#이직" in blog
        assert "---" in blog

    def test_dict_input(self):
        from pipeline.newsletter_formatter import format_for_blog
        data = {
            "hook": "테스트 훅",
            "story": "테스트 스토리",
            "insight": "테스트 인사이트",
            "cta": "테스트 CTA",
            "topic_cluster": "건강",
        }
        result = format_for_blog(data, platform="naver")
        assert "#건강" in result


class TestCurateFromRecords:
    """자동 큐레이션 테스트."""

    def test_selects_top_items(self):
        from pipeline.newsletter_formatter import curate_newsletter_from_records
        records = [
            {"topic_cluster": "연봉", "views": 10000, "likes": 500, "retweets": 100, "final_rank_score": 85},
            {"topic_cluster": "이직", "views": 8000, "likes": 300, "retweets": 50, "final_rank_score": 78},
            {"topic_cluster": "IT", "views": 500, "likes": 10, "retweets": 2, "final_rank_score": 30},
        ]
        result = curate_newsletter_from_records(records, max_items=2)
        assert len(result) == 2
        assert result[0]["topic_cluster"] == "연봉"  # 최고 성과

    def test_topic_diversity(self):
        from pipeline.newsletter_formatter import curate_newsletter_from_records
        records = [
            {"topic_cluster": "연봉", "views": 10000, "likes": 500, "retweets": 100, "final_rank_score": 85},
            {"topic_cluster": "연봉", "views": 9000, "likes": 400, "retweets": 80, "final_rank_score": 80},
            {"topic_cluster": "연봉", "views": 8000, "likes": 300, "retweets": 60, "final_rank_score": 75},
            {"topic_cluster": "이직", "views": 7000, "likes": 200, "retweets": 40, "final_rank_score": 70},
        ]
        result = curate_newsletter_from_records(records, max_items=3)
        assert len(result) == 3
        # 연봉 최대 2개, 이직 1개
        topic_list = [r["topic_cluster"] for r in result]
        assert topic_list.count("연봉") == 2
        assert "이직" in topic_list

    def test_empty_records(self):
        from pipeline.newsletter_formatter import curate_newsletter_from_records
        result = curate_newsletter_from_records([], max_items=5)
        assert result == []
