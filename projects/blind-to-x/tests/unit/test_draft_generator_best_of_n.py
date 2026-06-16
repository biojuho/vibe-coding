"""Best-of-N 결합 점수 (5축 + 4축 comment_trigger) 회귀 테스트.

Phase 3 enhancement: editorial_reviewer 가 twitter/threads 에 대해 반환하는
`comment_trigger_scores` 4축 평균을 best-of-n 후보 선택에 결합한다.
"""

from __future__ import annotations

import asyncio
import sys
from dataclasses import dataclass, field
from pathlib import Path
from unittest.mock import MagicMock

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pipeline.draft_cache import DraftCache  # noqa: E402
from pipeline.draft_generator import TweetDraftGenerator  # noqa: E402


class FakeConfig:
    def __init__(self, data):
        self.data = data

    def get(self, key, default=None):
        cur = self.data
        for part in key.split("."):
            if isinstance(cur, dict):
                cur = cur.get(part)
            else:
                return default
        return default if cur is None else cur


def _build_generator(extra: dict | None = None) -> TweetDraftGenerator:
    data = {
        "llm": {
            "providers": ["anthropic"],
            "max_retries_per_provider": 1,
            "request_timeout_seconds": 5,
        },
        # These tests validate Best-of-N scoring/selection and monkeypatch
        # generation paths when needed; avoid constructing real provider clients.
        "anthropic": {"enabled": False, "api_key": "k", "model": "claude-sonnet-4-6"},
        "openai": {"enabled": False},
        "gemini": {"enabled": False},
        "xai": {"enabled": False},
        "ollama": {"enabled": False},
        "tweet_style": {"tone": "casual", "max_length": 280},
    }
    if extra:
        for key, value in extra.items():
            cur = data
            parts = key.split(".")
            for part in parts[:-1]:
                cur = cur.setdefault(part, {})
            cur[parts[-1]] = value
    return TweetDraftGenerator(FakeConfig(data))


@dataclass
class FakeEditorialResult:
    avg_score: float = 0.0
    comment_trigger_scores: dict[str, float] = field(default_factory=dict)


def test_combined_score_uses_only_avg_when_no_comment_trigger():
    gen = _build_generator()
    result = FakeEditorialResult(avg_score=7.5)

    combined, breakdown = gen._combined_candidate_score(result, ["twitter"])

    assert combined == 7.5
    assert breakdown["avg_score"] == 7.5
    assert breakdown["comment_trigger_avg"] == 0.0
    assert breakdown["comment_weight"] == 0.0


def test_combined_score_uses_only_avg_for_naver_blog():
    """naver_blog 출력은 댓글 트리거 4축이 적용되지 않으므로 결합 가중 0."""
    gen = _build_generator()
    result = FakeEditorialResult(
        avg_score=6.0,
        comment_trigger_scores={"twitter": 9.0},
    )

    combined, breakdown = gen._combined_candidate_score(result, ["naver_blog"])

    assert combined == 6.0
    assert breakdown["comment_weight"] == 0.0


def test_combined_score_blends_twitter_with_default_weight():
    gen = _build_generator()
    result = FakeEditorialResult(
        avg_score=8.0,
        comment_trigger_scores={"twitter": 6.0},
    )

    combined, breakdown = gen._combined_candidate_score(result, ["twitter"])

    # 기본 weight 0.5: (8.0 * 0.5) + (6.0 * 0.5) = 7.0
    assert combined == 7.0
    assert breakdown["comment_trigger_avg"] == 6.0
    assert breakdown["comment_weight"] == 0.5


def test_combined_score_averages_multiple_comment_trigger_platforms():
    gen = _build_generator()
    result = FakeEditorialResult(
        avg_score=8.0,
        comment_trigger_scores={"twitter": 4.0, "threads": 6.0, "naver_blog": 9.9},
    )

    combined, breakdown = gen._combined_candidate_score(result, ["twitter", "threads"])

    # ct_avg = (4 + 6) / 2 = 5.0; 0.5 * 8.0 + 0.5 * 5.0 = 6.5
    assert combined == 6.5
    assert breakdown["comment_trigger_avg"] == 5.0


def test_combined_score_weight_zero_ignores_comment_trigger():
    gen = _build_generator({"llm.best_of_n_comment_weight": 0.0})
    result = FakeEditorialResult(avg_score=5.0, comment_trigger_scores={"twitter": 9.5})

    combined, breakdown = gen._combined_candidate_score(result, ["twitter"])

    assert combined == 5.0
    assert breakdown["comment_weight"] == 0.0


def test_combined_score_weight_one_ignores_avg():
    gen = _build_generator({"llm.best_of_n_comment_weight": 1.0})
    result = FakeEditorialResult(avg_score=2.0, comment_trigger_scores={"twitter": 9.0})

    combined, breakdown = gen._combined_candidate_score(result, ["twitter"])

    assert combined == 9.0
    assert breakdown["comment_weight"] == 1.0


def test_combined_score_clamps_weight_below_zero_and_above_one():
    too_low = _build_generator({"llm.best_of_n_comment_weight": -2.5})
    too_high = _build_generator({"llm.best_of_n_comment_weight": 17.0})
    result = FakeEditorialResult(avg_score=4.0, comment_trigger_scores={"twitter": 8.0})

    combined_low, low_break = too_low._combined_candidate_score(result, ["twitter"])
    combined_high, high_break = too_high._combined_candidate_score(result, ["twitter"])

    assert combined_low == 4.0  # weight clamped to 0
    assert low_break["comment_weight"] == 0.0
    assert combined_high == 8.0  # weight clamped to 1
    assert high_break["comment_weight"] == 1.0


def test_combined_score_handles_garbage_weight_config():
    gen = _build_generator({"llm.best_of_n_comment_weight": "not-a-number"})
    result = FakeEditorialResult(avg_score=6.0, comment_trigger_scores={"twitter": 8.0})

    combined, breakdown = gen._combined_candidate_score(result, ["twitter"])

    # falls back to default 0.5: (6 + 8) / 2 = 7.0
    assert combined == 7.0
    assert breakdown["comment_weight"] == 0.5


def test_quality_weight_clamps_bad_config():
    too_low = _build_generator({"llm.best_of_n_quality_weight": -3.0})
    too_high = _build_generator({"llm.best_of_n_quality_weight": 99.0})
    garbage = _build_generator({"llm.best_of_n_quality_weight": "bad"})

    assert too_low._best_of_n_quality_weight() == 0.0
    assert too_high._best_of_n_quality_weight() == 1.0
    assert garbage._best_of_n_quality_weight() == TweetDraftGenerator._DEFAULT_BEST_OF_N_QUALITY_WEIGHT


def test_combined_score_picks_higher_combined_not_higher_avg():
    """이 테스트가 핵심: avg 가 살짝 낮지만 댓글 트리거가 훨씬 높은 후보가 이긴다."""
    gen = _build_generator()  # weight 0.5
    candidate_a = FakeEditorialResult(avg_score=8.5, comment_trigger_scores={"twitter": 4.0})
    candidate_b = FakeEditorialResult(avg_score=7.5, comment_trigger_scores={"twitter": 8.5})

    combined_a, _ = gen._combined_candidate_score(candidate_a, ["twitter"])
    combined_b, _ = gen._combined_candidate_score(candidate_b, ["twitter"])

    assert combined_a == 6.25  # (8.5 + 4.0) / 2
    assert combined_b == 8.0  # (7.5 + 8.5) / 2
    assert combined_b > combined_a
    # 5축만 봤다면 A가 이겼겠지만 결합 점수에선 B가 이긴다.
    assert candidate_a.avg_score > candidate_b.avg_score


def test_combined_score_ignores_non_numeric_comment_trigger_entry():
    gen = _build_generator()
    result = FakeEditorialResult(
        avg_score=6.0,
        comment_trigger_scores={"twitter": "high", "threads": 8.0},
    )

    combined, breakdown = gen._combined_candidate_score(result, ["twitter", "threads"])

    # twitter 항목은 string 이라 무시, threads 만 유효: ct_avg = 8.0
    # 0.5 * 6.0 + 0.5 * 8.0 = 7.0
    assert combined == 7.0
    assert breakdown["comment_trigger_avg"] == 8.0


def test_best_of_n_picker_stashes_comment_trigger_avg_into_drafts_dict():
    """T-1107: Best-of-N selected candidate 의 ct_avg 가 persist_stage 에서 읽을 수 있도록
    drafts_dict["_comment_trigger_avg"] 에 영속화되어야 한다.
    소스 수준 contract 잠금 (전체 generate_drafts 모킹 비용 회피)."""
    source = (ROOT / "pipeline" / "draft_generator.py").read_text(encoding="utf-8")
    # 키는 underscore-prefix 컨벤션 (다른 _hook_score / _virality_score / _fit_score 와 정합)
    assert 'drafts_dict["_comment_trigger_avg"]' in source
    # 값은 best_breakdown["comment_trigger_avg"] 에서 직접 추출
    assert 'best_breakdown or {}).get("comment_trigger_avg", 0.0)' in source


def test_select_best_of_n_candidate_persists_comment_trigger_avg(monkeypatch):
    gen = _build_generator()

    @dataclass
    class FakeSelectionResult:
        polished_drafts: dict[str, object]
        avg_score: float
        comment_trigger_scores: dict[str, float]

    class FakeReviewer:
        def __init__(self, config):
            self.config = config

        async def review_and_polish(self, drafts_dict, _post_data):
            scores = {
                "avg-winner": (8.5, {"twitter": 4.0}),
                "comment-winner": (7.5, {"twitter": 8.5}),
            }
            avg_score, comment_scores = scores[drafts_dict["id"]]
            return FakeSelectionResult(
                polished_drafts=drafts_dict,
                avg_score=avg_score,
                comment_trigger_scores=comment_scores,
            )

    monkeypatch.setattr("pipeline.editorial_reviewer.EditorialReviewer", FakeReviewer)

    selected_drafts, image_prompt = asyncio.run(
        gen._select_best_of_n_candidate(
            [
                ({"id": "avg-winner", "_provider_used": "anthropic"}, "image-a"),
                ({"id": "comment-winner", "_provider_used": "anthropic"}, "image-b"),
            ],
            {"title": "연봉 이야기"},
            ["twitter"],
        )
    )

    assert selected_drafts["id"] == "comment-winner"
    assert selected_drafts["_comment_trigger_avg"] == 8.5
    assert image_prompt == "image-b"


def test_select_best_of_n_candidate_prefers_publishable_distinct_output(monkeypatch):
    """A directly usable, less repetitive draft should beat a flashier near-duplicate."""
    cache = DraftCache()
    cache.clear()
    repeated_text = "회의실 문 닫히자마자 다들 연봉 얘기를 멈췄다. 숫자보다 침묵이 더 오래 남았다."
    cache.set("recent-repeat", {"twitter": repeated_text}, None)

    gen = _build_generator({"llm.best_of_n_quality_weight": 0.35})

    @dataclass
    class FakeSelectionResult:
        polished_drafts: dict[str, object]
        avg_score: float
        comment_trigger_scores: dict[str, float]

    class FakeReviewer:
        def __init__(self, config):
            self.config = config

        async def review_and_polish(self, drafts_dict, _post_data):
            scores = {
                "flashy-repeat": (9.5, {"twitter": 9.5}),
                "usable-distinct": (8.0, {"twitter": 8.0}),
            }
            avg_score, comment_scores = scores[drafts_dict["id"]]
            return FakeSelectionResult(
                polished_drafts=drafts_dict,
                avg_score=avg_score,
                comment_trigger_scores=comment_scores,
            )

    monkeypatch.setattr("pipeline.editorial_reviewer.EditorialReviewer", FakeReviewer)

    selected_drafts, image_prompt = asyncio.run(
        gen._select_best_of_n_candidate(
            [
                (
                    {
                        "id": "flashy-repeat",
                        "twitter": repeated_text,
                        "_provider_used": "anthropic",
                    },
                    "image-repeat",
                ),
                (
                    {
                        "id": "usable-distinct",
                        "twitter": "7년 차 동료가 회의 끝나고 한 말이 더 오래 남았다. 이직보다 먼저 확인할 건 연봉표가 아니라 협상 가능한 기준이었다.",
                        "_provider_used": "anthropic",
                    },
                    "image-distinct",
                ),
            ],
            {"title": "연봉 협상 이야기", "content": ""},
            ["twitter"],
        )
    )

    assert selected_drafts["id"] == "usable-distinct"
    assert selected_drafts["_quality_gate_score"] >= 9.0
    assert selected_drafts["_quality_gate_failures"] == 0
    assert selected_drafts["_max_semantic_similarity"] < 0.70
    assert selected_drafts["_best_of_n_selection_score"] > 8.0
    assert image_prompt == "image-distinct"
    cache.clear()


def test_generate_drafts_single_candidate_caches_generated_result(monkeypatch):
    gen = _build_generator({"llm.best_of_n": 1})
    gen.draft_cache = MagicMock()
    gen.draft_cache.get.return_value = None
    monkeypatch.setattr(gen, "_build_prompt", lambda _post_data, _top_tweets, _output_formats: "prompt")
    monkeypatch.setattr(gen, "_available_providers_after_recent_failures", lambda: ["anthropic"])

    async def _fake_generate_once(prompt, providers, output_formats, allow_partial):
        assert prompt == "prompt"
        assert providers == ["anthropic"]
        assert output_formats == ["twitter"]
        assert allow_partial is False
        return {"twitter": "fresh draft", "_provider_used": "anthropic"}, "image prompt"

    monkeypatch.setattr(gen, "_generate_drafts_once", _fake_generate_once)
    post_data = {"title": "제목", "content": "본문"}

    drafts, image_prompt = asyncio.run(gen.generate_drafts(post_data, output_formats=["twitter"]))

    assert drafts["twitter"] == "fresh draft"
    assert image_prompt == "image prompt"
    gen.draft_cache.set.assert_called_once()
    cache_args, cache_kwargs = gen.draft_cache.set.call_args
    assert cache_args[0] == gen._make_cache_key(post_data, ["twitter"])
    assert cache_args[1] is drafts
    assert cache_args[2] == "image prompt"
    assert cache_kwargs["provider"] == "anthropic"


def test_generate_drafts_best_of_n_reviewer_failure_caches_first_candidate(monkeypatch):
    gen = _build_generator({"llm.best_of_n": 2})
    gen.draft_cache = MagicMock()
    gen.draft_cache.get.return_value = None
    monkeypatch.setattr(gen, "_build_prompt", lambda _post_data, _top_tweets, _output_formats: "prompt")
    monkeypatch.setattr(gen, "_available_providers_after_recent_failures", lambda: ["anthropic"])
    generated_ids: list[str] = []

    async def _fake_generate_once(_prompt, _providers, _output_formats, _allow_partial):
        draft_id = "first" if not generated_ids else "second"
        generated_ids.append(draft_id)
        return {"id": draft_id, "_provider_used": "anthropic"}, f"image-{draft_id}"

    async def _fail_selection(_candidates, _post_data, _output_formats):
        raise RuntimeError("reviewer unavailable")

    monkeypatch.setattr(gen, "_generate_drafts_once", _fake_generate_once)
    monkeypatch.setattr(gen, "_select_best_of_n_candidate", _fail_selection)

    drafts, image_prompt = asyncio.run(
        gen.generate_drafts({"title": "제목", "content": "본문"}, output_formats=["twitter"])
    )

    assert generated_ids == ["first", "second"]
    assert drafts["id"] == "first"
    assert image_prompt == "image-first"
    gen.draft_cache.set.assert_called_once()
    cache_args, cache_kwargs = gen.draft_cache.set.call_args
    assert cache_args[1] is drafts
    assert cache_kwargs["provider"] == "anthropic"


def test_combined_score_handles_missing_avg_attribute_gracefully():
    gen = _build_generator()

    class Bare:
        comment_trigger_scores = {"twitter": 9.0}

    combined, breakdown = gen._combined_candidate_score(Bare(), ["twitter"])

    # avg=0.0, ct_avg=9.0, weight=0.5 → 4.5
    assert combined == 4.5
    assert breakdown["avg_score"] == 0.0


# ── BON-PFE: ProviderFallbackError diagnostics preserved in Best-of-N ────────


def test_generate_best_of_n_candidates_collects_provider_failures(monkeypatch):
    """BON-PFE001: 각 후보 생성 실패 시 ProviderFallbackError.failures 가 누적돼야 한다."""
    from pipeline.draft_generator import ProviderFallbackError

    gen = _build_generator()

    failures_a = [{"provider": "anthropic", "error_preview": "timeout"}]
    failures_b = [{"provider": "openai", "error_preview": "rate_limit"}]

    call_count = [0]

    async def _always_fail(_prompt, _providers, _output_formats, _allow_partial):
        call_count[0] += 1
        exc = ProviderFallbackError("all providers failed", failures_a if call_count[0] == 1 else failures_b)
        raise exc

    monkeypatch.setattr(gen, "_generate_drafts_once", _always_fail)

    candidates, all_failures = asyncio.run(
        gen._generate_best_of_n_candidates(
            best_of_n=2,
            prompt="테스트 프롬프트",
            providers=["anthropic", "openai"],
            output_formats=["twitter"],
            allow_partial=False,
        )
    )

    assert candidates == []
    assert len(all_failures) == 2
    providers_in_failures = {f["provider"] for f in all_failures}
    assert "anthropic" in providers_in_failures
    assert "openai" in providers_in_failures


def test_generate_drafts_all_bon_fail_surfaces_provider_failures(monkeypatch):
    """BON-PFE002: Best-of-N 전체 실패 시 _provider_failures 가 결과 dict 에 포함돼야 한다."""
    from pipeline.draft_generator import ProviderFallbackError

    gen = _build_generator({"llm.best_of_n": 2})
    gen.draft_cache = MagicMock(spec=DraftCache)
    gen.draft_cache.get.return_value = None

    failures = [{"provider": "anthropic", "error_preview": "overloaded"}]

    async def _always_fail(_prompt, _providers, _output_formats, _allow_partial):
        raise ProviderFallbackError("providers exhausted", failures)

    monkeypatch.setattr(gen, "_generate_drafts_once", _always_fail)
    # Override provider availability so the early-exit "no providers" guard is bypassed
    monkeypatch.setattr(gen, "_available_providers_after_recent_failures", lambda: ["anthropic"])

    result_dict, image_prompt = asyncio.run(
        gen.generate_drafts({"title": "제목", "content": "본문"}, output_formats=["twitter"])
    )

    assert result_dict.get("_generation_failed") is True
    assert "_provider_failures" in result_dict, "Provider failures must be surfaced for Notion triage"
    assert result_dict["_provider_failures"][0]["provider"] == "anthropic"
    assert image_prompt is None
