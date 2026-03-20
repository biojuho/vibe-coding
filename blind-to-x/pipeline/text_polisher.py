"""텍스트 후처리 모듈 — 맞춤법 교정 + 띄어쓰기 교정 + 가독성 점수.

kiwipiepy를 사용하여 LLM이 생성한 한국어 초안을 후처리합니다.
오프라인으로 동작하며 API 비용 $0입니다.

사용법:
    from pipeline.text_polisher import TextPolisher, polish_text
    polisher = TextPolisher()
    result = polisher.polish("연봉이노무 낮아서화가남")
    print(result.text)        # 교정된 텍스트
    print(result.readability) # 가독성 점수 (0-100)
"""

from __future__ import annotations

import logging
import os
import re
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# kiwipiepy는 optional — 없으면 graceful degradation
_kiwi_instance = None
_kiwi_load_attempted = False


def _get_kiwi():
    """Kiwi 싱글톤 인스턴스를 반환. 로드 실패 시 None."""
    global _kiwi_instance, _kiwi_load_attempted
    if _kiwi_load_attempted:
        return _kiwi_instance
    _kiwi_load_attempted = True
    try:
        from kiwipiepy import Kiwi

        # Windows에서 한국어 사용자명 경로 문제 우회
        model_path = None
        try:
            import kiwipiepy_model

            default_path = os.path.dirname(kiwipiepy_model.__file__)
            if any(ord(c) > 127 for c in default_path):
                # Non-ASCII 경로 → 임시 ASCII 경로로 재귀 복사 (하위 디렉토리 포함)
                import shutil

                ascii_path = os.path.join(os.environ.get("TEMP", "/tmp"), "kiwi_model")
                if not os.path.exists(os.path.join(ascii_path, "extract.mdl")):
                    if os.path.exists(ascii_path):
                        shutil.rmtree(ascii_path)
                    shutil.copytree(default_path, ascii_path)
                    logger.info("Kiwi model tree copied to ASCII path: %s", ascii_path)
                model_path = ascii_path
        except ImportError:
            pass

        if model_path:
            _kiwi_instance = Kiwi(model_path=model_path)
        else:
            _kiwi_instance = Kiwi()
        logger.info("Kiwi morphological analyzer loaded successfully")
    except Exception as exc:
        logger.warning("kiwipiepy load failed (text polishing disabled): %s", exc)
        _kiwi_instance = None
    return _kiwi_instance


@dataclass
class PolishResult:
    """텍스트 후처리 결과."""

    text: str
    original: str
    readability: float = 0.0
    avg_sentence_length: float = 0.0
    corrections_made: int = 0
    sino_korean_ratio: float = 0.0


def _split_sentences(text: str) -> list[str]:
    """문장 분리 (Kiwi 없이도 동작하는 폴백)."""
    kiwi = _get_kiwi()
    if kiwi:
        try:
            return [s.text.strip() for s in kiwi.split_into_sents(text) if s.text.strip()]
        except Exception:
            pass
    # 폴백: 정규식 기반
    return [s.strip() for s in re.split(r"(?<=[.!?。])\s+", text) if s.strip()]


def _fix_spacing(text: str) -> str:
    """kiwipiepy의 space() 메서드로 띄어쓰기 교정."""
    kiwi = _get_kiwi()
    if not kiwi:
        return text
    try:
        return kiwi.space(text)
    except Exception:
        return text


def _fix_typos(text: str) -> str:
    """kiwipiepy의 typo correction으로 맞춤법 교정.

    v0.23.0+에서는 tokenize(typos='basic') → 교정된 형태소 재조합.
    """
    kiwi = _get_kiwi()
    if not kiwi:
        return text
    try:
        # Kiwi의 join()이 교정된 텍스트를 반환
        result = kiwi.join(kiwi.tokenize(text, typos="basic"))
        return result if result else text
    except Exception:
        return text


def _compute_readability(text: str) -> dict:
    """가독성 지표를 산출.

    Returns:
        {readability: 0-100, avg_sentence_length, sino_korean_ratio}
    """
    kiwi = _get_kiwi()
    sentences = _split_sentences(text)
    num_sentences = max(len(sentences), 1)

    # 평균 문장 길이 (글자 수)
    total_chars = sum(len(s) for s in sentences)
    avg_len = total_chars / num_sentences

    # 한자어(Sino-Korean) 비율 — NNG(일반명사) 중 한자어 추정
    sino_ratio = 0.0
    if kiwi:
        try:
            tokens = kiwi.tokenize(text)
            nouns = [t for t in tokens if t.tag.startswith("NN")]
            if nouns:
                # 한자어 추정: 2음절 이상 NNG (한국어 고유어는 1음절이 많음)
                sino_count = sum(1 for t in nouns if len(t.form) >= 2 and t.tag == "NNG")
                sino_ratio = sino_count / len(nouns)
        except Exception:
            pass

    # 가독성 점수 산출 (0-100)
    # 최적: 평균 문장 길이 20-40자, 한자어 비율 30% 이하
    len_score = 100.0
    if avg_len < 10:
        len_score -= (10 - avg_len) * 3  # 너무 짧은 문장 감점
    elif avg_len > 50:
        len_score -= (avg_len - 50) * 2  # 너무 긴 문장 감점

    sino_score = 100.0
    if sino_ratio > 0.5:
        sino_score -= (sino_ratio - 0.5) * 80  # 한자어 과다 감점

    # 문장 수 보너스 (3-10문장이 최적)
    sent_score = 100.0
    if num_sentences < 2:
        sent_score -= 20
    elif num_sentences > 15:
        sent_score -= (num_sentences - 15) * 3

    readability = max(0.0, min(100.0, (len_score * 0.4 + sino_score * 0.3 + sent_score * 0.3)))

    return {
        "readability": float(round(readability, 1)),
        "avg_sentence_length": round(avg_len, 1),
        "sino_korean_ratio": round(sino_ratio, 3),
    }


def polish_text(text: str, fix_spacing: bool = True, fix_typo: bool = True) -> PolishResult:
    """텍스트를 교정하고 가독성 점수를 산출합니다.

    Args:
        text: 원본 텍스트.
        fix_spacing: 띄어쓰기 교정 여부.
        fix_typo: 맞춤법 교정 여부.

    Returns:
        PolishResult: 교정된 텍스트와 가독성 점수.
    """
    if not text or not text.strip():
        return PolishResult(text=text, original=text)

    original = text
    corrections = 0

    # 1. 띄어쓰기 교정
    if fix_spacing:
        spaced = _fix_spacing(text)
        if spaced != text:
            corrections += 1
            text = spaced

    # 2. 맞춤법 교정
    if fix_typo:
        fixed = _fix_typos(text)
        if fixed != text:
            corrections += 1
            text = fixed

    # 3. 가독성 산출
    metrics = _compute_readability(text)

    return PolishResult(
        text=text,
        original=original,
        readability=metrics["readability"],
        avg_sentence_length=metrics["avg_sentence_length"],
        corrections_made=corrections,
        sino_korean_ratio=metrics["sino_korean_ratio"],
    )


class TextPolisher:
    """텍스트 후처리기 클래스 인터페이스."""

    def __init__(self, fix_spacing: bool = True, fix_typo: bool = True):
        self.fix_spacing = fix_spacing
        self.fix_typo = fix_typo
        # 초기화 시 Kiwi 로드 시도
        _get_kiwi()

    def polish(self, text: str) -> PolishResult:
        """텍스트를 교정하고 가독성 점수를 반환."""
        return polish_text(text, fix_spacing=self.fix_spacing, fix_typo=self.fix_typo)

    def compute_readability(self, text: str) -> float:
        """가독성 점수만 반환 (0-100)."""
        return _compute_readability(text)["readability"]

    @property
    def available(self) -> bool:
        """kiwipiepy가 로드되었는지 여부."""
        return _get_kiwi() is not None
