"""P1-B / P2-A / P2-B / P2-D 최적화 검증 단위 테스트 (mock 기반)."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


# ---------------------------------------------------------------------------
# 헬퍼
# ---------------------------------------------------------------------------


class FakeConfig:
    def __init__(self, data: dict):
        self._data = data

    def get(self, key, default=None):
        cur = self._data
        for part in key.split("."):
            if isinstance(cur, dict):
                cur = cur.get(part)
            else:
                return default
        return default if cur is None else cur


# ---------------------------------------------------------------------------
# P1-B: Notion URL 캐시
# ---------------------------------------------------------------------------


class TestNotionURLCache:
    """is_duplicate()가 첫 호출 후 메모리 캐시를 사용하는지 검증."""

    def _make_uploader(self):
        from pipeline.notion_upload import NotionUploader

        cfg = FakeConfig(
            {
                "notion": {"api_key": "test-key", "database_id": "test-db-id", "properties": {}},
                "dedup": {"lookback_days": 14},
            }
        )
        uploader = NotionUploader(cfg)
        # 스키마 준비 완료 상태 시뮬레이션
        uploader._schema_ready = True
        uploader._db_properties = {
            "Source URL": {"type": "url"},
            "콘텐츠": {"type": "title"},
        }
        uploader.props = {
            "url": "Source URL",
            "title": "콘텐츠",
            "memo": "메모",
            "status": "상태",
            "date": "생성일",
            "image_needed": "이미지 필요",
            "tweet_body": "트윗 본문",
            "tweet_url": "트윗 링크",
            "views": "24h 조회수",
            "likes": "24h 좋아요",
            "retweets": "24h 리트윗",
            "source": "원본 소스",
            "feed_mode": "피드 모드",
            "topic_cluster": "토픽 클러스터",
            "hook_type": "훅 타입",
            "emotion_axis": "감정 축",
            "audience_fit": "대상 독자",
            "scrape_quality_score": "스크랩 품질 점수",
            "publishability_score": "발행 적합도 점수",
            "performance_score": "성과 예측 점수",
            "final_rank_score": "최종 랭크 점수",
            "review_note": "검토 메모",
            "chosen_draft_type": "선택 초안 타입",
            "newsletter_body": "뉴스레터 초안",
            "publish_channel": "발행 채널",
            "published_at": "발행 시각",
            "performance_grade": "성과 등급",
        }
        return uploader

    @pytest.mark.asyncio
    async def test_cache_built_once_on_first_call(self):
        """_ensure_url_cache()가 최초 1회만 Notion API를 호출하는지 확인."""
        uploader = self._make_uploader()

        fake_page = {"properties": {"Source URL": {"type": "url", "url": "https://www.teamblind.com/post/test-1"}}}

        call_count = 0

        async def mock_get_recent_pages(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            return [fake_page]

        uploader.get_recent_pages = mock_get_recent_pages

        # 첫 번째 호출 → bulk 조회 실행
        await uploader._ensure_url_cache()
        assert call_count == 1
        assert uploader._url_cache_ready is True

        # 두 번째 호출 → 캐시 히트, API 미호출
        await uploader._ensure_url_cache()
        assert call_count == 1  # 여전히 1회

    @pytest.mark.asyncio
    async def test_is_duplicate_uses_cache(self):
        """is_duplicate()가 캐시에 있는 URL을 True로 반환하는지 확인."""
        uploader = self._make_uploader()
        uploader._url_cache_ready = True
        uploader._url_cache = {"https://www.teamblind.com/post/abc123"}

        result = await uploader.is_duplicate("https://www.teamblind.com/post/abc123")
        assert result is True

    @pytest.mark.asyncio
    async def test_is_duplicate_not_in_cache(self):
        """is_duplicate()가 캐시에 없는 URL을 False로 반환하는지 확인."""
        uploader = self._make_uploader()
        uploader._url_cache_ready = True
        uploader._url_cache = {"https://www.teamblind.com/post/abc123"}

        result = await uploader.is_duplicate("https://www.teamblind.com/post/NEW-url")
        assert result is False

    def test_register_url_in_cache(self):
        """업로드 성공 후 URL이 캐시에 추가되는지 확인."""
        uploader = self._make_uploader()
        uploader._url_cache_ready = True
        uploader._url_cache = set()

        uploader._register_url_in_cache("https://www.teamblind.com/post/new-post")
        assert "https://www.teamblind.com/post/new-post" in uploader._url_cache


# ---------------------------------------------------------------------------
# P2-A: 분류 규칙 YAML 외부화
# ---------------------------------------------------------------------------


class TestClassificationRulesYAML:
    """YAML 파일이 없을 때 fallback 규칙이 사용되는지 검증.

    [QA 수정] _RULES_FILE 속성이 rules_loader 리팩토링으로 제거됨.
    pipeline.rules_loader.load_rules() 반환값을 직접 mock하는 방식으로 교체.
    """

    def _reset_caches(self):
        """content_intelligence와 rules_loader의 캐시를 모두 초기화."""
        import pipeline.content_intelligence as ci
        import pipeline.rules_loader as rl

        ci._loaded_rules = None
        rl._merged_rules_cache = None

    def test_topic_rules_fallback_when_no_yaml(self, monkeypatch):
        """YAML 파일 없을 때 내장 fallback 규칙이 반환되는지 확인.

        [QA 수정] _loaded_rules에 빈 dict를 직접 주입 →
        _yaml_rules_to_tuples()의 get("topic_rules", [])가 []를 반환 →
        fallback(_TOPIC_RULES_FALLBACK)이 사용되는지 검증.
        """
        import pipeline.content_intelligence as ci

        # 빈 dict 주입: topic_rules 키가 없으므로 fallback 사용
        monkeypatch.setattr(ci, "_loaded_rules", {})

        rules = ci.get_topic_rules()
        assert len(rules) > 0
        labels = [r[0] for r in rules]
        assert "연봉" in labels
        assert "이직" in labels

    def test_topic_rules_loaded_from_yaml(self, monkeypatch):
        """YAML에서 로드된 topic_rules가 사용되는지 확인.

        [QA 수정] _loaded_rules에 fake topic_rules를 직접 주입.
        """
        import pipeline.content_intelligence as ci

        fake_rules = {"topic_rules": [{"label": "테스트토픽", "keywords": ["테스트", "키워드"]}]}
        monkeypatch.setattr(ci, "_loaded_rules", fake_rules)

        rules = ci.get_topic_rules()
        assert len(rules) == 1
        assert rules[0][0] == "테스트토픽"
        assert "테스트" in rules[0][1]

    def test_classify_topic_cluster_uses_yaml_rules(self, monkeypatch):
        """classify_topic_cluster()가 주입된 YAML 규칙을 실제로 사용하는지 확인.

        [QA 수정] _loaded_rules에 직접 커스텀 topic_rules 주입.
        """
        import pipeline.content_intelligence as ci

        fake_rules = {"topic_rules": [{"label": "커스텀주제", "keywords": ["커스텀키워드1"]}]}
        monkeypatch.setattr(ci, "_loaded_rules", fake_rules)

        result = ci.classify_topic_cluster("커스텀키워드1 포함된 제목", "내용")
        assert result == "커스텀주제"

    def teardown_method(self):
        """각 테스트 후 캐시 초기화."""
        self._reset_caches()


# ---------------------------------------------------------------------------
# P2-B: LLM 응답 캐싱
# ---------------------------------------------------------------------------


class TestDraftGeneratorCache:
    """동일 콘텐츠에 대해 LLM API가 1회만 호출되는지 검증."""

    def _build_config(self):
        return FakeConfig(
            {
                "llm": {
                    "providers": ["gemini"],
                    "max_retries_per_provider": 1,
                    "request_timeout_seconds": 5,
                    "strategy": "fallback",
                },
                "gemini": {"enabled": True, "api_key": "gemini-key", "model": "gemini-2.5-flash"},
                "tweet_style": {"tone": "테스트", "max_length": 280},
            }
        )

    @pytest.mark.asyncio
    async def test_second_call_uses_cache(self):
        """같은 포스트를 두 번 요청하면 두 번째는 LLM을 호출하지 않아야 한다."""
        from pipeline.draft_cache import DraftCache
        from pipeline.draft_generator import TweetDraftGenerator

        # SQLite 캐시 초기화
        DraftCache().clear()

        gen = TweetDraftGenerator(self._build_config())

        call_count = 0

        async def mock_gemini(_prompt):
            nonlocal call_count
            call_count += 1
            return (
                "<twitter>테스트 트윗</twitter><reply>테스트 댓글</reply><creator_take>테스트 해석</creator_take>",
                100,
                50,
            )

        gen._generate_with_gemini = mock_gemini

        post = {"title": "테스트 제목", "content": "테스트 내용입니다."}

        # 첫 번째 호출 → LLM 실제 호출 (generation + self-scoring)
        result1, _ = await gen.generate_drafts(post)
        call_count_after_first = call_count

        # 두 번째 호출 (동일 콘텐츠) → 캐시 히트 → LLM 추가 호출 없음
        result2, _ = await gen.generate_drafts(post)
        assert call_count == call_count_after_first  # 캐시 히트 → 추가 호출 없음
        assert result1 == result2

    @pytest.mark.asyncio
    async def test_different_content_not_cached(self):
        """다른 내용은 캐시 히트 없이 LLM을 호출해야 한다."""
        from pipeline.draft_cache import DraftCache
        from pipeline.draft_generator import TweetDraftGenerator

        DraftCache().clear()

        gen = TweetDraftGenerator(self._build_config())
        call_count = 0

        async def mock_gemini(_prompt):
            nonlocal call_count
            call_count += 1
            return (
                "<twitter>트윗 내용</twitter><reply>후속 댓글</reply><creator_take>운영자 관점</creator_take>",
                100,
                50,
            )

        gen._generate_with_gemini = mock_gemini

        await gen.generate_drafts({"title": "제목 A", "content": "내용 A"})
        await gen.generate_drafts({"title": "제목 B", "content": "내용 B"})

        # 다른 콘텐츠 → 각각 generation 호출 = 2 posts × 1 call = 2
        assert call_count == 2

    def teardown_method(self):
        from pipeline.draft_cache import DraftCache

        DraftCache().clear()


# ---------------------------------------------------------------------------
# P1-C: DALL-E 비활성화 플래그
# ---------------------------------------------------------------------------


class TestImageGeneratorDALLEFlag:
    """fallback_to_dalle: false 시 DALL-E가 호출되지 않는지 검증."""

    def _make_generator(self, fallback_to_dalle: bool):
        from pipeline.image_generator import ImageGenerator

        cfg = FakeConfig(
            {
                "image": {
                    "provider": "gemini",
                    "fallback_to_pollinations": False,
                    "fallback_to_dalle": fallback_to_dalle,
                },
                "gemini": {"api_key": ""},  # 키 없어서 pollinations으로 fallback
                "openai": {"enabled": True, "api_key": "fake-key", "image_model": "dall-e-3"},
            }
        )
        return ImageGenerator(cfg)

    def test_dalle_disabled_by_default(self):
        """fallback_to_dalle: false 일 때 provider가 dalle가 아닌지 확인."""
        gen = self._make_generator(fallback_to_dalle=False)
        # ImageGenerator doesn't expose fallback_to_dalle; it uses provider field
        assert gen.provider != "dalle"

    @pytest.mark.asyncio
    async def test_gemini_failure_no_dalle_fallback(self):
        """Gemini 실패 시 fallback_to_dalle=False면 None 반환 (DALL-E 미호출)."""
        from pipeline.image_generator import ImageGenerator

        image_cfg = FakeConfig(
            {
                "image": {
                    "provider": "gemini",
                    "fallback_to_pollinations": False,
                    "fallback_to_dalle": False,
                },
                "gemini": {"api_key": "fake-gemini-key"},
            }
        )
        gen = ImageGenerator(image_cfg)
        gen.provider = "gemini"
        gen._gemini_client = MagicMock()
        gen.fallback_to_pollinations = False
        gen.fallback_to_dalle = False

        dalle_call_count = 0

        async def mock_gemini(_prompt):
            return None  # 실패

        async def mock_dalle(_prompt):
            nonlocal dalle_call_count
            dalle_call_count += 1
            return "https://dalle-url.com/image.png"

        gen._generate_gemini = mock_gemini
        gen._generate_dalle = mock_dalle

        result = await gen.generate_image("test prompt")
        assert result is None
        assert dalle_call_count == 0


# ---------------------------------------------------------------------------
# P2-D: Twitter backoff
# ---------------------------------------------------------------------------


class TestTwitterBackoff:
    """429 Rate Limit 시 exponential backoff 재시도 검증."""

    def _make_poster(self):
        from pipeline.twitter_poster import TwitterPoster

        poster = TwitterPoster.__new__(TwitterPoster)
        poster.enabled = True
        poster.api_v1 = MagicMock()
        poster.client_v2 = MagicMock()
        return poster

    @pytest.mark.asyncio
    async def test_rate_limit_retries_then_succeeds(self):
        """첫 번째 429 후 두 번째 시도에서 성공하는지 확인."""
        import tweepy
        from pipeline import twitter_poster as tp

        poster = self._make_poster()
        attempt = 0

        # asyncio.to_thread(func, *args, **kwargs) 형태로 호출되므로 _func으로 수신
        async def mock_to_thread(_func, *args, **kwargs):
            nonlocal attempt
            attempt += 1
            if attempt == 1:
                raise tweepy.TooManyRequests(MagicMock())
            return MagicMock(data={"id": "123456"})

        with patch.object(tp.asyncio, "sleep", new_callable=AsyncMock) as mock_sleep:
            with patch.object(tp.asyncio, "to_thread", side_effect=mock_to_thread):
                result = await poster.post_tweet("테스트 트윗", max_retries=3)

        assert result is not None
        assert "123456" in result
        mock_sleep.assert_called_once()

    @pytest.mark.asyncio
    async def test_rate_limit_max_retries_exhausted(self):
        """모든 재시도 후에도 429면 None 반환."""
        import tweepy
        from pipeline import twitter_poster as tp

        poster = self._make_poster()

        async def mock_always_429(_func, *args, **kwargs):
            raise tweepy.TooManyRequests(MagicMock())

        with patch.object(tp.asyncio, "sleep", new_callable=AsyncMock):
            with patch.object(tp.asyncio, "to_thread", side_effect=mock_always_429):
                result = await poster.post_tweet("테스트 트윗", max_retries=2)

        assert result is None
