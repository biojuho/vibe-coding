"""P2 확장 기능 단위 테스트.

Note: newsletter_formatter.py는 2026-03-16에 삭제되었습니다.
TestNewsletterNewMappings, TestFormatForBlog, TestCurateFromRecords는
해당 모듈에 의존했으므로 제거되었습니다.
Threads/Blog 초안 생성은 이제 draft_generator.py 내에서 LLM이 직접 처리합니다.
"""


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

    def test_title_not_in_prompt(self):
        """한글 제목은 프롬프트에 포함되지 않아야 함 (이미지 텍스트 오타 방지)."""
        from pipeline.image_generator import ImageGenerator
        prompt = ImageGenerator.build_image_prompt(
            topic_cluster="IT",
            title="개발자 연봉 인상 꿀팁 공개",
        )
        # IT 토픽 스타일은 적용되지만 한글 텍스트는 제외
        assert "futuristic" in prompt.lower()
        assert "개발자" not in prompt

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
