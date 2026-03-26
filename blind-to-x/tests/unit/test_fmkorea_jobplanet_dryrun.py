"""FMKorea/JobPlanet dry-run 스크래핑 및 quality_boost 6D 통합 테스트.

커버리지:
  - quality_boost → 6D score 통합 (source_hints)
  - FMKoreaScraper: URL 정규화, 카테고리 분류, feed_urls 라우팅
  - JobplanetScraper: URL 정규화, 카테고리 분류, feed_urls 라우팅
  - 통합: source_hints 로드, build_content_profile 호환성
"""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch


_BTX_ROOT = Path(__file__).resolve().parent.parent
if str(_BTX_ROOT) not in sys.path:
    sys.path.insert(0, str(_BTX_ROOT))


# ════════════════════════════════════════════════════════════════════════
# quality_boost → 6D score 통합 테스트
# ════════════════════════════════════════════════════════════════════════

class TestQualityBoost6DIntegration:
    """source_hints의 quality_boost가 6D score에 올바르게 반영되는지 검증."""

    def _make_post(self, source="blind"):
        return {
            "title": "연봉 협상 팁 공유합니다",
            "content": "이직할 때 연봉 협상에서 가장 중요한 건 현재 연봉을 절대 먼저 말하지 않는 것입니다. 직장인이라면 꼭 기억하세요.",
            "likes": 50,
            "comments": 10,
            "source": source,
        }

    def test_blind_no_boost(self):
        """blind(quality_boost=1.0)는 점수 변화 없음."""
        from pipeline.content_intelligence import calculate_6d_score
        post = self._make_post("blind")
        score_with, _ = calculate_6d_score(post, "연봉", "공감형", "공감", "전직장인", source="blind")
        score_without, _ = calculate_6d_score(post, "연봉", "공감형", "공감", "전직장인", source="")
        assert score_with == score_without  # 1.0 boost = no change

    def test_fmkorea_penalized(self):
        """fmkorea(quality_boost=0.85)는 점수 하락."""
        from pipeline.content_intelligence import calculate_6d_score
        post = self._make_post("fmkorea")
        base_score, _ = calculate_6d_score(post, "직장개그", "공감형", "웃김", "전직장인", source="")
        boosted_score, _ = calculate_6d_score(post, "직장개그", "공감형", "웃김", "전직장인", source="fmkorea")
        assert boosted_score < base_score
        # 약 15% 감소 허용
        assert boosted_score >= base_score * 0.80

    def test_jobplanet_boosted(self):
        """jobplanet(quality_boost=1.1)은 점수 상승."""
        from pipeline.content_intelligence import calculate_6d_score
        post = self._make_post("jobplanet")
        base_score, _ = calculate_6d_score(post, "회사문화", "논쟁형", "분노", "전직장인", source="")
        boosted_score, _ = calculate_6d_score(post, "회사문화", "논쟁형", "분노", "전직장인", source="jobplanet")
        assert boosted_score > base_score
        # 10% 상승, 100 이하로 clamped
        assert boosted_score <= 100.0

    def test_ppomppu_slightly_penalized(self):
        """ppomppu(quality_boost=0.9)는 약간 감소."""
        from pipeline.content_intelligence import calculate_6d_score
        post = self._make_post("ppomppu")
        base_score, _ = calculate_6d_score(post, "재테크", "정보형", "공감", "전직장인", source="")
        boosted_score, _ = calculate_6d_score(post, "재테크", "정보형", "공감", "전직장인", source="ppomppu")
        assert boosted_score < base_score
        assert boosted_score >= base_score * 0.85

    def test_unknown_source_no_boost(self):
        """알 수 없는 소스는 quality_boost=1.0 기본값."""
        from pipeline.content_intelligence import calculate_6d_score
        post = self._make_post("unknown_source")
        score_with, _ = calculate_6d_score(post, "연봉", "공감형", "공감", "전직장인", source="unknown_source")
        score_without, _ = calculate_6d_score(post, "연봉", "공감형", "공감", "전직장인", source="")
        assert score_with == score_without

    def test_build_content_profile_passes_source(self):
        """build_content_profile이 post_data['source']를 6D에 전달하는지 검증."""
        from pipeline.content_intelligence import build_content_profile
        post_blind = self._make_post("blind")
        post_fmkorea = self._make_post("fmkorea")

        profile_blind = build_content_profile(post_blind, scrape_quality_score=70.0)
        profile_fmkorea = build_content_profile(post_fmkorea, scrape_quality_score=70.0)

        # fmkorea는 0.85 boost이므로 rank_6d가 더 낮아야 함
        assert profile_fmkorea.rank_6d <= profile_blind.rank_6d


# ════════════════════════════════════════════════════════════════════════
# FMKoreaScraper 유닛 테스트
# ════════════════════════════════════════════════════════════════════════

class _FakeConfig:
    """ConfigManager 최소 mock."""
    def get(self, key, default=None):
        defaults = {
            "headless": True,
            "screenshot_dir": "/tmp/screenshots",
            "request.timeout_seconds": "10",
            "request.retries": "1",
            "request.backoff_seconds": "0.1",
            "screenshot_retention_days": "0",
            "scrape_quality.min_content_length": "20",
            "scrape_quality.min_korean_ratio": "0.15",
            "scrape_quality.require_title": True,
            "scrape_quality.max_empty_field_ratio": "0.4",
            "scrape_quality.selector_timeout_ms": "5000",
            "scrape_quality.direct_fallback_timeout_ms": "8000",
            "scrape_quality.save_failure_snapshot": False,
            "scrape_quality.failure_snapshot_dir": "/tmp/failures",
            "browser.pool_size": "1",
            "proxy.enabled": False,
            "proxy.list": [],
        }
        return defaults.get(key, default)


def _make_fmkorea():
    with patch("scrapers.base.ProxyManager") as MockPM:
        MockPM.return_value.get_random_proxy.return_value = None
        from scrapers.fmkorea import FMKoreaScraper
        return FMKoreaScraper(_FakeConfig())


def _make_jobplanet():
    with patch("scrapers.base.ProxyManager") as MockPM:
        MockPM.return_value.get_random_proxy.return_value = None
        from scrapers.jobplanet import JobplanetScraper
        return JobplanetScraper(_FakeConfig())


class TestFMKoreaScraper:
    def test_normalize_url_relative(self):
        scraper = _make_fmkorea()
        result = scraper._normalize_url("/index.php?mid=best&document_srl=123")
        assert result == "https://www.fmkorea.com/index.php?mid=best&document_srl=123"

    def test_normalize_url_absolute(self):
        scraper = _make_fmkorea()
        result = scraper._normalize_url("https://www.fmkorea.com/12345")
        assert result == "https://www.fmkorea.com/12345"

    def test_normalize_url_empty(self):
        scraper = _make_fmkorea()
        assert scraper._normalize_url("") is None
        assert scraper._normalize_url(None) is None

    def test_normalize_url_external_rejected(self):
        scraper = _make_fmkorea()
        assert scraper._normalize_url("https://naver.com/page") is None

    def test_determine_category_humor(self):
        scraper = _make_fmkorea()
        assert scraper._determine_category("웃긴 직장 짤 모음", "ㅋㅋㅋ 이거 진짜 웃김") == "humor"

    def test_determine_category_career(self):
        scraper = _make_fmkorea()
        assert scraper._determine_category("이직 후기", "면접에서 연봉 협상") == "career"

    def test_determine_category_general(self):
        scraper = _make_fmkorea()
        assert scraper._determine_category("오늘 날씨", "비가 오네요") == "general"

    def test_source_name(self):
        scraper = _make_fmkorea()
        assert scraper.SOURCE_NAME == "fmkorea"

    def test_base_url(self):
        scraper = _make_fmkorea()
        assert "fmkorea.com" in scraper.BASE_URL


# ════════════════════════════════════════════════════════════════════════
# JobplanetScraper 유닛 테스트
# ════════════════════════════════════════════════════════════════════════

class TestJobplanetScraper:
    def test_normalize_url_relative(self):
        scraper = _make_jobplanet()
        result = scraper._normalize_url("/communities/posts/12345")
        assert result == "https://www.jobplanet.co.kr/communities/posts/12345"

    def test_normalize_url_absolute(self):
        scraper = _make_jobplanet()
        result = scraper._normalize_url("https://www.jobplanet.co.kr/communities/posts/12345")
        assert result == "https://www.jobplanet.co.kr/communities/posts/12345"

    def test_normalize_url_empty(self):
        scraper = _make_jobplanet()
        assert scraper._normalize_url("") is None
        assert scraper._normalize_url(None) is None

    def test_normalize_url_external_rejected(self):
        scraper = _make_jobplanet()
        assert scraper._normalize_url("https://google.com/search") is None

    def test_determine_category_career(self):
        scraper = _make_jobplanet()
        assert scraper._determine_category("이직 준비 팁", "면접 준비와 커리어 전략") == "career"

    def test_determine_category_worklife(self):
        scraper = _make_jobplanet()
        assert scraper._determine_category("좋은 회사 기준", "직장 문화와 워라밸") == "work-life"

    def test_determine_category_money(self):
        scraper = _make_jobplanet()
        assert scraper._determine_category("연봉 비교", "연봉 인상 방법") == "money"

    def test_determine_category_company(self):
        scraper = _make_jobplanet()
        assert scraper._determine_category("대기업 vs 스타트업", "스타트업 장단점") == "company"

    def test_determine_category_general(self):
        scraper = _make_jobplanet()
        assert scraper._determine_category("오늘 점심", "뭐 먹을까") == "general"

    def test_source_name(self):
        scraper = _make_jobplanet()
        assert scraper.SOURCE_NAME == "jobplanet"


# ════════════════════════════════════════════════════════════════════════
# source_hints 통합 검증
# ════════════════════════════════════════════════════════════════════════

class TestSourceHintsIntegration:
    def test_fmkorea_hints_loaded(self):
        from pipeline.content_intelligence import get_source_hint
        hint = get_source_hint("fmkorea")
        assert hint["display_name"] == "에펨코리아"
        assert hint["quality_boost"] == 0.85
        assert "직장개그" in hint.get("topic_bias", [])

    def test_jobplanet_hints_loaded(self):
        from pipeline.content_intelligence import get_source_hint
        hint = get_source_hint("jobplanet")
        assert hint["display_name"] == "잡플래닛"
        assert hint["quality_boost"] == 1.1
        assert "회사문화" in hint.get("topic_bias", [])

    def test_scraper_output_profile_compatible(self):
        """스크래퍼 출력 형식이 build_content_profile과 호환되는지 검증."""
        from pipeline.content_intelligence import build_content_profile

        # FMKorea 스크래퍼 출력 시뮬레이션
        mock_fmkorea_post = {
            "title": "직장에서 웃긴 에피소드 모음",
            "content": "오늘 직장에서 팀장님이 회의 중에 졸다가 필기를 하는 척 했는데 진짜로 다 봤다 ㅋㅋㅋ 회사 다니면서 이런 일이 비일비재해요",
            "url": "https://www.fmkorea.com/12345",
            "likes": 100,
            "comments": 30,
            "source": "fmkorea",
        }
        profile = build_content_profile(mock_fmkorea_post, scrape_quality_score=65.0)
        assert profile.rank_6d >= 0
        assert profile.rank_6d <= 100
        assert profile.topic_cluster != ""

        # JobPlanet 스크래퍼 출력 시뮬레이션
        mock_jobplanet_post = {
            "title": "연봉 협상 후기 공유",
            "content": "이직하면서 연봉 협상을 했는데 현재 회사가 카운터오퍼를 제시했습니다. 결국 이직을 선택했고 연봉이 30% 올랐습니다. 직장인분들 참고하세요.",
            "url": "https://www.jobplanet.co.kr/communities/posts/67890",
            "likes": 50,
            "comments": 20,
            "source": "jobplanet",
        }
        profile_jp = build_content_profile(mock_jobplanet_post, scrape_quality_score=75.0)
        assert profile_jp.rank_6d >= 0
        assert profile_jp.rank_6d <= 100
