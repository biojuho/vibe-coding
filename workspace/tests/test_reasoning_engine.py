"""
귀납적 추론 엔진 단위 테스트.

모든 LLM 호출을 mock하여 비용 없이 실행합니다.
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock


WORKSPACE_ROOT = Path(__file__).resolve().parents[1]
if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT))

from execution.reasoning_engine import (
    FactFragment,
    Hypothesis,
    ReasoningAdapter,
    _get_connection,
    _robust_json_parse,
    _strength_for_count,
)


# ── _robust_json_parse 테스트 ─────────────────────────────────


class TestRobustJsonParse:
    """5단계 견고 파서 테스트."""

    def test_stage1_markdown_fence(self):
        """마크다운 펜스 제거 후 파싱."""
        text = '```json\n[{"fact_text": "hello", "why": "test"}]\n```'
        result = _robust_json_parse(text)
        assert len(result) == 1
        assert result[0]["fact_text"] == "hello"

    def test_stage2_direct_parse(self):
        """정상 JSON 직접 파싱."""
        text = '[{"a": 1}, {"a": 2}]'
        result = _robust_json_parse(text)
        assert len(result) == 2

    def test_stage3_newline_in_value(self):
        """값 내부 줄바꿈 치환."""
        text = '[{"text": "line1\nline2", "key": "ok"}]'
        result = _robust_json_parse(text)
        assert len(result) == 1
        assert "line1" in result[0]["text"]

    def test_stage4_collapse_newlines(self):
        """전체 줄바꿈 collapse."""
        text = '[\n{"a":\n"hello"}\n]'
        result = _robust_json_parse(text)
        assert len(result) == 1

    def test_stage5_regex_extraction(self):
        """개별 객체 regex 추출."""
        text = 'Some text {"a": 1} more text {"b": 2} end'
        result = _robust_json_parse(text)
        assert len(result) == 2
        assert result[0]["a"] == 1
        assert result[1]["b"] == 2

    def test_empty_input(self):
        """빈 입력."""
        assert _robust_json_parse("") == []
        assert _robust_json_parse("   ") == []

    def test_dict_wrapped_in_list(self):
        """단일 dict → 리스트 래핑."""
        text = '{"fact_text": "single"}'
        result = _robust_json_parse(text)
        assert len(result) == 1
        assert result[0]["fact_text"] == "single"

    def test_total_garbage(self):
        """완전한 쓰레기 입력."""
        result = _robust_json_parse("not json at all, just random text!!!")
        assert result == []


# ── _strength_for_count 테스트 ────────────────────────────────


class TestStrengthForCount:
    def test_emerging(self):
        assert _strength_for_count(1) == "emerging"
        assert _strength_for_count(2) == "emerging"

    def test_moderate(self):
        assert _strength_for_count(3) == "moderate"
        assert _strength_for_count(4) == "moderate"

    def test_strong(self):
        assert _strength_for_count(5) == "strong"
        assert _strength_for_count(100) == "strong"


# ── DB 스키마 테스트 ──────────────────────────────────────────


class TestDBSchema:
    def test_tables_created(self, tmp_path):
        """3개 테이블이 정상 생성되는지 확인."""
        db_path = tmp_path / "test_reasoning.db"
        conn = _get_connection(db_path)
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        tables = [row["name"] for row in cursor.fetchall()]
        conn.close()
        assert "fact_fragments" in tables
        assert "hypotheses" in tables
        assert "reasoning_patterns" in tables


# ── ReasoningAdapter 테스트 ───────────────────────────────────


def _make_adapter(tmp_path) -> ReasoningAdapter:
    """테스트용 어댑터 생성 (LLM mock)."""
    mock_llm = MagicMock()
    adapter = ReasoningAdapter(
        db_path=tmp_path / "test.db",
        llm_client=mock_llm,
    )
    return adapter


class TestStep1ExtractFacts:
    def test_basic_extraction(self, tmp_path):
        adapter = _make_adapter(tmp_path)
        adapter.llm.generate_json.return_value = [
            {"fact_text": "AI 시장이 2025년 300조에 도달했다.", "why_question": "시장 성장"},
            {"fact_text": "Google이 Gemini 3를 발표했다.", "why_question": "경쟁 구도 변화"},
        ]

        facts = adapter.step1_extract_facts(
            "테스트 콘텐츠",
            report_id="test-001",
            category="AI_테크",
        )

        assert len(facts) == 2
        assert facts[0].fact_id == "F-test-001-1"
        assert facts[0].category == "AI_테크"
        adapter.llm.generate_json.assert_called_once()

    def test_dict_with_facts_key(self, tmp_path):
        """LLM이 {'facts': [...]} 형태로 응답하는 경우."""
        adapter = _make_adapter(tmp_path)
        adapter.llm.generate_json.return_value = {"facts": [{"fact_text": "사실1", "why_question": "질문1"}]}

        facts = adapter.step1_extract_facts(
            "content",
            report_id="r1",
            category="test",
        )
        assert len(facts) == 1

    def test_empty_facts_skipped(self, tmp_path):
        """빈 fact_text는 건너뛰기."""
        adapter = _make_adapter(tmp_path)
        adapter.llm.generate_json.return_value = [
            {"fact_text": "", "why_question": "skip"},
            {"fact_text": "valid fact", "why_question": "keep"},
        ]
        facts = adapter.step1_extract_facts(
            "content",
            report_id="r2",
            category="test",
        )
        assert len(facts) == 1
        assert facts[0].fact_text == "valid fact"


class TestStep2Hypothesize:
    def test_basic_hypothesis(self, tmp_path):
        adapter = _make_adapter(tmp_path)
        adapter.llm.generate_json.return_value = [
            {
                "hypothesis": "AI 시장 성장과 대형 모델 발표는 양의 상관관계",
                "based_on": ["F-test-1", "F-test-2"],
                "pattern": "대형 모델 출시 → 시장 급등",
            }
        ]

        facts = [
            FactFragment("F-test-1", "r1", "사실1", "왜1", "AI", "", ""),
            FactFragment("F-test-2", "r1", "사실2", "왜2", "AI", "", ""),
        ]

        hypotheses = adapter.step2_hypothesize(facts, category="AI")
        assert len(hypotheses) == 1
        assert hypotheses[0].status == "pending"
        assert "F-test-1" in hypotheses[0].based_on_facts


class TestStep3Falsify:
    def test_survived_creates_pattern(self, tmp_path):
        adapter = _make_adapter(tmp_path)
        adapter.llm.generate_json.return_value = [
            {
                "hypothesis_id": "H-test1",
                "hypothesis": "가설 예시",
                "status": "survived",
                "counter": "반증 시도했으나 근거 충분",
                "new_pattern": "AI 대형 모델 출시 → 시장 급등",
            }
        ]

        hypotheses = [
            Hypothesis(
                hypothesis_id="H-test1",
                hypothesis_text="테스트 가설",
                based_on_facts=["F-1"],
                status="pending",
            )
        ]

        patterns = adapter.step3_falsify(hypotheses, category="AI")
        assert len(patterns) == 1
        assert patterns[0]["action"] == "created"
        assert patterns[0]["strength"] == "emerging"

    def test_falsified_no_pattern(self, tmp_path):
        adapter = _make_adapter(tmp_path)
        adapter.llm.generate_json.return_value = [
            {
                "hypothesis_id": "H-test2",
                "hypothesis": "반증된 가설",
                "status": "falsified",
                "counter": "외부 변수 존재",
                "new_pattern": "",
            }
        ]

        hypotheses = [Hypothesis(hypothesis_id="H-test2", hypothesis_text="falsified", status="pending")]

        patterns = adapter.step3_falsify(hypotheses, category="AI")
        assert len(patterns) == 0


class TestPatternStrengthPromotion:
    def test_pattern_strengthens_over_runs(self, tmp_path):
        """동일 패턴 반복 생존 시 strength 상승."""
        adapter = _make_adapter(tmp_path)
        adapter.llm.generate_json.return_value = [
            {
                "hypothesis_id": "H-run",
                "hypothesis": "반복 가설",
                "status": "survived",
                "counter": "견딤",
                "new_pattern": "반복 패턴",
            }
        ]

        # 5회 반복 실행
        for i in range(5):
            h = Hypothesis(
                hypothesis_id="H-run",
                hypothesis_text="반복 가설",
                based_on_facts=[f"F-{i}"],
                status="pending",
            )
            adapter.step3_falsify([h], category="test_promo")

        # DB에서 패턴 확인
        conn = _get_connection(adapter.db_path)
        row = conn.execute(
            "SELECT survival_count, strength FROM reasoning_patterns WHERE pattern_text = '반복 패턴'"
        ).fetchone()
        conn.close()

        assert row is not None
        assert row["survival_count"] == 5
        assert row["strength"] == "strong"


class TestFullReasoning:
    def test_full_pipeline(self, tmp_path):
        """3단계 통합 테스트."""
        adapter = _make_adapter(tmp_path)

        # Step 1 응답
        step1_response = [
            {"fact_text": "사실1", "why_question": "왜1"},
            {"fact_text": "사실2", "why_question": "왜2"},
        ]
        # Step 2 응답
        step2_response = [
            {"hypothesis": "가설1", "based_on": ["F-full-1"], "pattern": "패턴1"},
        ]
        # Step 3 응답
        step3_response = [
            {
                "hypothesis_id": "",  # unknown ID — adapter handles gracefully
                "hypothesis": "가설1",
                "status": "survived",
                "counter": "견딤",
                "new_pattern": "새 패턴",
            }
        ]

        adapter.llm.generate_json.side_effect = [
            step1_response,
            step2_response,
            step3_response,
        ]

        result = adapter.run_full_reasoning(
            report_id="full-test",
            category="통합",
            content_text="테스트 콘텐츠 텍스트",
        )

        assert result["report_id"] == "full-test"
        assert result["category"] == "통합"
        assert len(result["facts"]) == 2
        assert len(result["hypotheses"]) == 1
        assert len(result["new_patterns"]) == 1
        assert result["stats"]["patterns_created"] == 1
        assert adapter.llm.generate_json.call_count == 3

    def test_no_facts_early_return(self, tmp_path):
        """사실 없으면 조기 종료."""
        adapter = _make_adapter(tmp_path)
        adapter.llm.generate_json.return_value = []

        result = adapter.run_full_reasoning(
            report_id="empty",
            category="없음",
            content_text="아무 내용",
        )

        assert result["facts"] == []
        assert result["hypotheses"] == []
        assert adapter.llm.generate_json.call_count == 1


class TestGetPatternStats:
    def test_empty_stats(self, tmp_path):
        adapter = _make_adapter(tmp_path)
        stats = adapter.get_pattern_stats()
        assert stats["total_patterns"] == 0
        assert stats["total_facts"] == 0


class TestIsAvailable:
    def test_available(self, tmp_path):
        adapter = _make_adapter(tmp_path)
        adapter.llm.enabled_providers.return_value = ["google"]
        assert adapter.is_available()

    def test_unavailable(self, tmp_path):
        adapter = _make_adapter(tmp_path)
        adapter.llm.enabled_providers.return_value = []
        assert not adapter.is_available()
