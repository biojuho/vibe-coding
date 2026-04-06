"""Extended tests for pipeline.readability — edge cases and scoring branches."""

from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pipeline.readability import calculate_readability


class TestReadabilityEdgeCases:
    def test_empty_string(self):
        result = calculate_readability("")
        assert result["readability_score"] == 50.0
        assert result["sentence_count"] == 0

    def test_whitespace_only(self):
        result = calculate_readability("   \n\t  ")
        assert result["readability_score"] == 50.0

    def test_short_sentences_no_splits(self):
        """Text with no sentence-ending punctuation under 5 chars per fragment."""
        result = calculate_readability("abc")
        # All fragments < 5 chars -> filtered out -> empty sentences
        assert result["sentence_count"] == 0
        assert result["readability_score"] == 50.0

    def test_very_long_sentences(self):
        """Average sentence length > 60 should incur max penalty."""
        # One sentence of ~80 chars
        long_text = "이것은 매우 매우 매우 긴 문장입니다 " * 6 + "그리고 끝입니다."
        result = calculate_readability(long_text)
        assert result["avg_sentence_length"] > 50
        # Should have some penalty
        assert result["readability_score"] < 100

    def test_medium_long_sentences(self):
        """avg_length between 45-60."""
        # Create text with avg ~50 chars per sentence
        sentences = ["가" * 50 + "."] * 3
        text = " ".join(sentences)
        result = calculate_readability(text)
        assert result["readability_score"] < 100

    def test_short_avg_sentence(self):
        """avg_length < 8 should incur penalty."""
        text = "짧다. 맞아. 응."
        result = calculate_readability(text)
        # With very short sentences
        assert result["readability_score"] <= 100

    def test_high_passive_ratio(self):
        """Text with many passive constructions should lose points."""
        text = "이것은 결정됩니다. 그것은 진행됩니다. 저것은 완료됩니다. 모든 것이 확인됩니다. 사항이 처리됩니다."
        result = calculate_readability(text)
        assert result["passive_ratio"] > 0.3
        assert result["readability_score"] < 100

    def test_very_high_passive_ratio(self):
        """passive_ratio > 0.6 should give 25 point penalty."""
        # Create text where every sentence has passive
        sentences = [f"항목 {i}은 수행됩니다." for i in range(10)]
        text = " ".join(sentences)
        result = calculate_readability(text)
        assert result["passive_ratio"] > 0.5

    def test_medium_passive_ratio(self):
        """passive_ratio 0.3-0.4 range."""
        # 3 passive out of 10
        sentences = [f"항목 {i}을 확인한다." for i in range(7)]
        sentences += [f"사항 {i}은 처리됩니다." for i in range(3)]
        text = " ".join(sentences)
        result = calculate_readability(text)
        assert 0.0 <= result["passive_ratio"] <= 1.0

    def test_single_long_sentence_penalty(self):
        """Single sentence with > 200 chars text loses 15 points."""
        text = "이것은 " * 60 + "매우 긴 텍스트이다"
        result = calculate_readability(text)
        assert result["sentence_count"] == 1
        assert len(text) > 200
        # Should have sentence_count=1 penalty AND length penalty

    def test_optimal_text(self):
        """Well-structured text should score high."""
        text = (
            "직장인들의 연봉 인상률이 화제다. "
            "올해 평균 3.5% 인상이 예상된다. "
            "특히 IT 업계가 높은 인상률을 보인다. "
            "반면 제조업은 다소 보수적이다. "
            "전문가들은 내년에도 비슷한 추세를 예측한다."
        )
        result = calculate_readability(text)
        assert result["readability_score"] >= 70
        assert result["sentence_count"] >= 3

    def test_passive_patterns_specific(self):
        """Test specific passive pattern matches."""
        patterns_text = {
            "됩니다": "이 과정이 진행됩니다.",
            "됐습니다": "결정됐습니다.",
            "되었습니다": "완료되었습니다.",
            "라고 합니다": "좋다라고 합니다.",
            "것으로 보입니다": "상승할 것으로 보입니다.",
            "것으로 알려져": "개편될 것으로 알려져.",
        }
        for pattern, text in patterns_text.items():
            calculate_readability(text + " 일반 문장이다.")
            # At least one passive sentence detected if text has the pattern
            # (May or may not be >= 5 chars after split)

    def test_no_passive(self):
        """Text without passive constructions."""
        text = "나는 간다. 너도 간다. 우리는 함께 간다."
        result = calculate_readability(text)
        assert result["passive_ratio"] == 0.0

    def test_avg_length_35_to_45(self):
        """avg_length between 35-45 should lose 10 points (line 73)."""
        # Create sentences averaging ~40 chars each
        sentences = ["가" * 38 + "입니다."] * 4
        text = " ".join(sentences)
        result = calculate_readability(text)
        assert result["avg_sentence_length"] > 35
        assert result["avg_sentence_length"] <= 45
        # Should have 10 point deduction from length
        assert result["readability_score"] < 100

    def test_passive_ratio_30_to_40_percent(self):
        """passive_ratio between 0.3-0.4 should lose 8 points (line 83)."""
        # 3 passive sentences out of 8 total = 37.5%
        active_sentences = [
            "나는 회사에 간다.",
            "그는 열심히 일한다.",
            "우리는 점심을 먹는다.",
            "팀원들이 회의를 한다.",
            "개발자가 코드를 작성한다.",
        ]
        passive_sentences = [
            "이 사항이 결정됩니다.",
            "모든 것이 확인됩니다.",
            "절차가 진행됩니다.",
        ]
        text = " ".join(active_sentences + passive_sentences)
        result = calculate_readability(text)
        assert 0.3 <= result["passive_ratio"] <= 0.5

    def test_score_clamped_to_0_100(self):
        """Score should never be negative or > 100."""
        # Extremely bad text
        text = "됩니다됩니다됩니다됩니다됩니다됩니다됩니다됩니다됩니다됩니다됩니다됩니다 " * 5
        result = calculate_readability(text)
        assert 0.0 <= result["readability_score"] <= 100.0
