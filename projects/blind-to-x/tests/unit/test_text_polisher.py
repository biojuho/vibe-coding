"""텍스트 후처리 모듈 (text_polisher) 유닛 테스트."""

from __future__ import annotations

import sys
from pathlib import Path
import pytest

# blind-to-x 루트를 path에 추가
ROOT = Path(__file__).resolve().parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pipeline.text_polisher as tp  # noqa: E402


@pytest.fixture(autouse=True)
def _reset_kiwi_singleton():
    """각 테스트 전후로 Kiwi 싱글톤 상태를 보존/복원."""
    old_inst = tp._kiwi_instance
    old_attempted = tp._kiwi_load_attempted
    yield
    tp._kiwi_instance = old_inst
    tp._kiwi_load_attempted = old_attempted


def _force_no_kiwi():
    """Kiwi 없는 상태를 강제합니다."""
    tp._kiwi_instance = None
    tp._kiwi_load_attempted = True


def _try_load_kiwi() -> bool:
    """Kiwi 로드를 시도하고 성공 여부를 반환.

    Non-ASCII 경로 환경에서 C 확장 segfault를 방지하기 위해
    ASCII 모델 경로가 이미 존재하는 경우에만 시도합니다.
    """
    import os

    ascii_model = os.path.join(os.environ.get("TEMP", "/tmp"), "kiwi_model")
    if not os.path.isdir(ascii_model):
        return False
    tp._kiwi_instance = None
    tp._kiwi_load_attempted = False
    try:
        return tp._get_kiwi() is not None
    except Exception:
        return False


# ── 가독성 점수 테스트 (Kiwi 없이도 동작) ───────────────────────────
class TestReadabilityFallback:
    """kiwipiepy가 없을 때도 가독성 산출이 동작하는지 확인."""

    def test_empty_text(self):
        _force_no_kiwi()
        result = tp.polish_text("")
        assert result.text == ""
        assert result.readability == 0.0

    def test_basic_readability(self):
        _force_no_kiwi()
        text = "연봉이 5천만원입니다. 이직을 고민하고 있어요. 조언 부탁드립니다."
        metrics = tp._compute_readability(text)
        assert 0 <= metrics["readability"] <= 100
        assert metrics["avg_sentence_length"] > 0

    def test_long_sentences_penalized(self):
        _force_no_kiwi()
        short = "짧은 문장. 좋은 가독성. 읽기 쉽다."
        long_text = (
            "이것은 매우 매우 긴 문장으로서 한 문장 안에 너무 많은 내용을 담고 있어서 "
            "읽기가 상당히 어렵고 독자가 중간에 지쳐서 스크롤을 넘겨버릴 수 있는 "
            "그런 종류의 문장입니다."
        )
        short_r = tp._compute_readability(short)["readability"]
        long_r = tp._compute_readability(long_text)["readability"]
        assert short_r > long_r, "짧은 문장이 긴 문장보다 가독성이 높아야 함"

    def test_multiple_sentences_score(self):
        _force_no_kiwi()
        text = "첫 번째 문장. 두 번째 문장. 세 번째 문장."
        metrics = tp._compute_readability(text)
        assert metrics["readability"] > 50  # 적절한 문장 수 → 높은 점수


class TestPolishResult:
    """PolishResult 데이터클래스 테스트."""

    def test_no_change_preserves_original(self):
        _force_no_kiwi()
        text = "정상적인 한국어 문장입니다."
        result = tp.polish_text(text, fix_spacing=False, fix_typo=False)
        assert result.text == text
        assert result.original == text
        assert result.corrections_made == 0

    def test_polish_returns_dataclass(self):
        _force_no_kiwi()
        result = tp.polish_text("테스트 문장입니다.")
        assert hasattr(result, "text")
        assert hasattr(result, "readability")
        assert hasattr(result, "corrections_made")
        assert hasattr(result, "sino_korean_ratio")


# ── Kiwi 로드 실패 시 graceful degradation ──────────────────────────
class TestGracefulDegradation:
    """kiwipiepy 임포트 실패 시에도 에러 없이 동작해야 함."""

    def test_polish_without_kiwi(self):
        _force_no_kiwi()
        result = tp.polish_text("테스트 문장입니다.", fix_spacing=True, fix_typo=True)
        assert result.text == "테스트 문장입니다."
        assert result.corrections_made == 0

    def test_fix_spacing_without_kiwi(self):
        _force_no_kiwi()
        result = tp._fix_spacing("붙어있는문장입니다")
        assert result == "붙어있는문장입니다"  # 변경 없이 반환

    def test_fix_typos_without_kiwi(self):
        _force_no_kiwi()
        result = tp._fix_typos("오타가있는문장")
        assert result == "오타가있는문장"  # 변경 없이 반환

    def test_split_sentences_without_kiwi(self):
        _force_no_kiwi()
        result = tp._split_sentences("첫 번째. 두 번째. 세 번째.")
        assert len(result) == 3


# ── TextPolisher 클래스 인터페이스 테스트 ─────────────────────────────
class TestTextPolisherClass:
    def test_available_property_no_kiwi(self):
        _force_no_kiwi()
        polisher = tp.TextPolisher()
        assert polisher.available is False

    def test_compute_readability_method(self):
        _force_no_kiwi()
        polisher = tp.TextPolisher(fix_spacing=False, fix_typo=False)
        score = polisher.compute_readability("이것은 테스트 문장입니다. 두 번째 문장이다.")
        assert isinstance(score, float)
        assert 0 <= score <= 100

    def test_polish_method(self):
        _force_no_kiwi()
        polisher = tp.TextPolisher(fix_spacing=False, fix_typo=False)
        result = polisher.polish("테스트 문장입니다.")
        assert isinstance(result, tp.PolishResult)


# ── Kiwi가 로드 가능할 때 추가 테스트 ────────────────────────────────
class TestWithKiwi:
    """Kiwi가 실제로 로드 가능한 환경에서만 실행."""

    @pytest.fixture(autouse=True)
    def _check_kiwi(self):
        if not _try_load_kiwi():
            pytest.skip("kiwipiepy not loadable in this environment")

    def test_spacing_correction(self):
        result = tp._fix_spacing("이건정말대단한발견이다")
        assert " " in result  # 띄어쓰기가 추가되어야 함

    def test_sentence_split_with_kiwi(self):
        sents = tp._split_sentences("안녕하세요. 반갑습니다. 좋은 하루 되세요.")
        assert len(sents) >= 2

    def test_readability_with_kiwi(self):
        metrics = tp._compute_readability(
            "직장인 평균 연봉이 5천만원을 돌파했습니다. 전문가들은 긍정적으로 평가합니다."
        )
        assert metrics["readability"] > 0
        assert "sino_korean_ratio" in metrics


# ── trafilatura 통합 테스트 ──────────────────────────────────────────
class TestTrafilaturaExtraction:
    def test_extract_clean_text_from_html(self):
        from scrapers.base import BaseScraper

        html = """
        <html><body>
        <nav>메뉴바</nav>
        <article>
            <h1>연봉 5천만원 시대</h1>
            <p>직장인들의 평균 연봉이 5천만원을 돌파했다. 이는 전년 대비 10% 상승한 수치다.</p>
            <p>전문가들은 이 추세가 당분간 이어질 것으로 전망한다. 다만 물가 상승분을 감안하면 실질 구매력은 오히려 감소했다는 분석도 있다.</p>
        </article>
        <footer>저작권 정보</footer>
        </body></html>
        """
        result = BaseScraper._extract_clean_text(html)
        # trafilatura가 본문을 추출했는지 확인
        assert len(result) > 0
        assert "연봉" in result or "5천만원" in result

    def test_extract_clean_text_empty_html(self):
        from scrapers.base import BaseScraper

        result = BaseScraper._extract_clean_text("")
        assert result == ""

    def test_extract_clean_text_minimal_html(self):
        from scrapers.base import BaseScraper

        result = BaseScraper._extract_clean_text("<p>짧은 텍스트</p>")
        # 매우 짧은 HTML은 추출 실패할 수 있음 → 빈 문자열 허용
        assert isinstance(result, str)
