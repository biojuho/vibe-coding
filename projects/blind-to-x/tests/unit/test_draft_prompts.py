"""Tests for pipeline.draft_prompts pure helpers."""

from __future__ import annotations

from unittest.mock import patch

from pipeline.draft_prompts import (
    _ANTHROPIC_USER_BLOCK_KEYS,
    _ANTHROPIC_USER_OUTPUT_BLOCK_KEYS,
    _ANTHROPIC_USER_PROMPT_TAIL_KEYS,
    _ANTHROPIC_USER_REFERENCE_BLOCK_KEYS,
    _AUXILIARY_OUTPUT_BLOCK_KEYS,
    _DEFAULT_IMAGE_PROMPT_BLOCK,
    _DEFAULT_THINKING_BLOCK,
    _LONGFORM_OUTPUT_BLOCK_KEYS,
    _PLATFORM_OUTPUT_BLOCK_KEYS,
    _PROMPT_COMPONENT_BLOCK_KEYS,
    _PROMPT_CONTEXT_KEYS,
    _REGULATION_OUTPUT_BLOCK_KEYS,
    _REGULATION_SUPPORTED_OUTPUT_FORMATS,
    _SHORTFORM_OUTPUT_BLOCK_KEYS,
    DraftPrompt,
    DraftPromptsMixin,
    _AnthropicPromptResultRequest,
    _AnthropicUserPromptRequest,
    _OutputBlockRequest,
    _OutputFormatBlockGroups,
    _PromptComponentBlockGroups,
    _PromptComponentRequest,
    _PromptPreparation,
)


class TestResolveTone:
    def _make_instance(self):
        obj = object.__new__(DraftPromptsMixin)
        obj.tone = "default tone"
        return obj

    @patch("pipeline.draft_prompts._load_draft_rules", return_value={"tone_mapping": {"salary": "salary tone"}})
    def test_resolve_tone_prefers_topic_mapping(self, mock_rules):
        obj = self._make_instance()

        assert obj._resolve_tone({"content_profile": {"topic_cluster": "salary"}, "category": "money"}) == (
            "salary tone"
        )

    @patch("pipeline.draft_prompts._load_draft_rules", return_value={"tone_mapping": {}})
    def test_resolve_tone_uses_category_fallback(self, mock_rules):
        obj = self._make_instance()

        assert obj._resolve_tone({"category": "work-life"}) == "직장 밈과 현실 공감을 섞은 톤"

    @patch("pipeline.draft_prompts._load_draft_rules", return_value={"tone_mapping": {"기타": "generic tone"}})
    def test_resolve_tone_uses_generic_or_instance_default(self, mock_rules):
        obj = self._make_instance()

        assert obj._resolve_tone({"category": "unknown"}) == "generic tone"

        with patch("pipeline.draft_prompts._load_draft_rules", return_value={"tone_mapping": {}}):
            assert obj._resolve_tone({"category": "unknown"}) == "default tone"


# ── _extract_content_essence (static, no LLM) ───────────────────────────────


class TestExtractContentEssence:
    """Tests for the deterministic content essence extractor."""

    def test_numbers_with_context(self):
        post = {"content": "연봉이 5000만원인데 3개월만에 50배 올랐다"}
        result = DraftPromptsMixin._extract_content_essence(post)
        assert len(result["key_numbers"]) >= 1
        # At least one number snippet should contain a digit
        assert any(c.isdigit() for snippet in result["key_numbers"] for c in snippet)

    def test_quotes_extraction(self):
        post = {"content": "그는 \"일이 사람을 만든다\"라고 말했다. 또한 '포기하지 마'라는 격언도 있다."}
        result = DraftPromptsMixin._extract_content_essence(post)
        assert len(result["quotes"]) >= 1

    def test_quotes_korean_brackets(self):
        post = {"content": "기사에서 「경제 위기」와 『생존 전략』을 다루었다."}
        result = DraftPromptsMixin._extract_content_essence(post)
        assert len(result["quotes"]) >= 1

    def test_empty_content(self):
        result = DraftPromptsMixin._extract_content_essence({})
        assert result["key_numbers"] == []
        assert result["quotes"] == []
        assert result["emotional_peaks"] == []
        assert result["opening"] == ""
        assert result["closing"] == ""

    def test_title_preserved(self):
        post = {"title": "연봉 협상 꿀팁", "content": "본문입니다."}
        result = DraftPromptsMixin._extract_content_essence(post)
        assert result["title"] == "연봉 협상 꿀팁"

    def test_opening_closing(self):
        post = {"content": "첫 문장은 이렇게 시작합니다. 중간 문장이 있습니다. 마지막으로 결론을 맺습니다."}
        result = DraftPromptsMixin._extract_content_essence(post)
        assert "첫 문장" in result["opening"]
        assert "결론" in result["closing"]

    def test_max_numbers_cap(self):
        # Generate content with many numbers
        numbers = " ".join(f"{i * 100}만원" for i in range(1, 20))
        post = {"content": numbers}
        result = DraftPromptsMixin._extract_content_essence(post)
        assert len(result["key_numbers"]) <= 8

    def test_max_quotes_cap(self):
        quotes = " ".join(f'"인용구 번호 {i}입니다 충분히 긴 문장"' for i in range(10))
        post = {"content": quotes}
        result = DraftPromptsMixin._extract_content_essence(post)
        assert len(result["quotes"]) <= 5


class TestPromptContent:
    def test_short_content_is_preserved(self):
        assert DraftPromptsMixin._prompt_content({"content": "short post"}) == "short post"

    def test_long_content_is_capped_with_ellipsis(self):
        result = DraftPromptsMixin._prompt_content({"content": "x" * 705})
        assert result == ("x" * 700) + "..."

    def test_missing_content_defaults_to_empty_string(self):
        assert DraftPromptsMixin._prompt_content({}) == ""


class TestContentSentences:
    def test_content_sentences_splits_supported_boundaries_and_filters_short_parts(self):
        result = DraftPromptsMixin._content_sentences(
            "short. this sentence is long enough!\nsecond long sentence? tiny"
        )

        assert result == ["this sentence is long enough", "second long sentence"]

    def test_content_sentences_allows_custom_min_length(self):
        result = DraftPromptsMixin._content_sentences("short. medium", min_length=5)

        assert result == ["medium"]


class TestContentKeyNumbers:
    def test_content_key_numbers_extracts_context_and_deduplicates(self):
        content = "앞뒤맥락 5000만원 필요. 다른 문장 5000만원 필요. 3개월 뒤 회복."

        result = DraftPromptsMixin._content_key_numbers(content, context_chars=4)

        assert len(result) == 3
        assert all(any(char.isdigit() for char in snippet) for snippet in result)

        duplicate_result = DraftPromptsMixin._content_key_numbers("5000만원 5000만원", context_chars=0)
        assert duplicate_result == ["5000만"]

    def test_content_key_numbers_caps_results(self):
        content = " ".join(f"{i}개월" for i in range(12))

        result = DraftPromptsMixin._content_key_numbers(content, limit=3, context_chars=0)

        assert result == ["0개", "1개", "2개"]


class TestContentQuotes:
    def test_content_quotes_extracts_supported_quote_marks(self):
        content = "\"quoted text\" 그리고 「다른 인용문입니다」 그리고 'short'"

        result = DraftPromptsMixin._content_quotes(content)

        assert result == ["quoted text", "다른 인용문입니다", "short"]

    def test_content_quotes_applies_existing_length_and_count_limits(self):
        content = " ".join(f'"valid quote {i}"' for i in range(7))

        result = DraftPromptsMixin._content_quotes(content, limit=3)

        assert result == ["valid quote 0", "valid quote 1", "valid quote 2"]
        assert DraftPromptsMixin._content_quotes('"tiny"') == []


class TestContentEmotionalPeaks:
    def test_content_emotional_peaks_selects_matching_sentences_in_order(self):
        sentences = ["calm opening", "angry middle", "surprised turn", "angry closing"]

        result = DraftPromptsMixin._content_emotional_peaks(sentences, ["angry", "surprised"], limit=2)

        assert result == ["angry middle", "surprised turn"]

    def test_content_emotional_peaks_returns_empty_without_keywords_or_matches(self):
        assert DraftPromptsMixin._content_emotional_peaks(["calm opening"], []) == []
        assert DraftPromptsMixin._content_emotional_peaks(["calm opening"], ["angry"]) == []


class TestContentSignalExamples:
    def test_content_signal_examples_combines_numbers_quotes_and_emotional_peaks(self):
        content = '연봉 5000만원이라고 했다. 그는 "퇴사가 답이다"라고 말했다.'
        sentences = ["연봉 5000만원이라고 했다", "퇴사가 답이다라고 말했다"]

        signals = DraftPromptsMixin._content_signal_examples(content, sentences, ["퇴사"])

        assert any("5000" in snippet for snippet in signals["key_numbers"])
        assert signals["quotes"] == ["퇴사가 답이다"]
        assert signals["emotional_peaks"] == ["퇴사가 답이다라고 말했다"]


class TestContentBookends:
    def test_content_bookends_return_empty_values_for_missing_sentences(self):
        assert DraftPromptsMixin._content_bookends([]) == ("", "")

    def test_content_bookends_keep_single_sentence_as_opening_only(self):
        assert DraftPromptsMixin._content_bookends(["only sentence"]) == ("only sentence", "")

    def test_content_bookends_return_first_and_last_sentence(self):
        assert DraftPromptsMixin._content_bookends(["first", "middle", "last"]) == ("first", "last")


class TestEmotionKeywords:
    def test_emotion_keywords_flattens_rule_keywords_in_order(self):
        result = DraftPromptsMixin._emotion_keywords(
            {
                "emotion_rules": [
                    {"keywords": ["angry", "sad"]},
                    {"keywords": ["surprised"]},
                    {},
                ],
            }
        )

        assert result == ["angry", "sad", "surprised"]

    def test_emotion_keywords_returns_empty_without_rules(self):
        assert DraftPromptsMixin._emotion_keywords({}) == []


class TestEssenceBlock:
    def test_essence_block_includes_available_parts(self):
        block = DraftPromptsMixin._build_essence_block(
            {
                "key_numbers": ["5000만원", "3개월"],
                "quotes": ["일이 사람을 만든다"],
                "emotional_peaks": ["너무 억울했다", "다시 시작했다"],
                "opening": "첫 문장",
                "closing": "마지막 문장",
            }
        )

        assert "[원문 핵심 추출 — 초안에 반드시 활용]" in block
        assert "핵심 수치: 5000만원 | 3개월" in block
        assert "인용/발언: 일이 사람을 만든다" in block
        assert "감정 고조점: 너무 억울했다 / 다시 시작했다" in block
        assert "원문 도입부: 첫 문장" in block
        assert "원문 결론부: 마지막 문장" in block

    def test_essence_block_omits_closing_when_same_as_opening(self):
        block = DraftPromptsMixin._build_essence_block(
            {
                "key_numbers": ["5000만원"],
                "quotes": [],
                "emotional_peaks": [],
                "opening": "same",
                "closing": "same",
            }
        )

        assert "원문 도입부: same" in block
        assert "원문 결론부" not in block

    def test_essence_block_returns_empty_without_core_extracts(self):
        block = DraftPromptsMixin._build_essence_block(
            {
                "key_numbers": [],
                "quotes": [],
                "emotional_peaks": [],
                "opening": "first sentence",
                "closing": "last sentence",
            }
        )

        assert block == ""


class TestTopicStrategyBlock:
    def test_topic_strategy_lines_include_present_fields_in_prompt_order(self):
        assert DraftPromptsMixin._topic_strategy_lines(
            "salary",
            {
                "emphasis": "use numbers",
                "avoid": "generic takes",
                "hook_template": "number plus reversal",
                "example_structure": "hook then concrete contrast",
            },
        ) == [
            "[토픽별 작성 전략 — salary]",
            "강조: use numbers",
            "피하기: generic takes",
            "훅 구조: number plus reversal",
            "글 구조: hook then concrete contrast",
        ]

    def test_topic_strategy_block_includes_configured_lines(self):
        rules = {
            "topic_prompt_strategies": {
                "salary": {
                    "emphasis": "use numbers",
                    "avoid": "generic takes",
                    "hook_template": "number plus reversal",
                    "example_structure": "hook then concrete contrast",
                },
            },
        }

        block = DraftPromptsMixin._build_topic_strategy_block(rules, "salary")

        assert "[토픽별 작성 전략 — salary]" in block
        assert "강조: use numbers" in block
        assert "피하기: generic takes" in block
        assert "훅 구조: number plus reversal" in block
        assert "글 구조: hook then concrete contrast" in block

    def test_topic_strategy_block_returns_empty_for_missing_topic(self):
        assert DraftPromptsMixin._build_topic_strategy_block({"topic_prompt_strategies": {}}, "missing") == ""


class TestAntiExamplesBlock:
    def test_selected_anti_examples_prefers_topic_examples_and_caps_at_three(self):
        anti_examples = {
            "salary": [{"text": "topic 1"}, {"text": "topic 2"}],
            "generic_bad": [{"text": "generic 1"}, {"text": "generic 2"}],
        }

        assert DraftPromptsMixin._selected_anti_examples(anti_examples, "salary") == [
            {"text": "topic 1"},
            {"text": "topic 2"},
            {"text": "generic 1"},
        ]

    def test_anti_example_lines_include_reason_when_present(self):
        assert DraftPromptsMixin._anti_example_lines(
            [
                {"text": "topic bad 1", "reason": "too vague"},
                {"text": "topic bad 2"},
            ]
        ) == [
            "\n[나쁜 예시 — 이렇게 쓰지 마세요]",
            "- 나쁜 예시 1: topic bad 1",
            "  이유: too vague",
            "- 나쁜 예시 2: topic bad 2",
        ]

    def test_anti_examples_block_prefers_topic_examples_and_caps_at_three(self):
        rules = {
            "anti_examples": {
                "salary": [
                    {"text": "topic bad 1", "reason": "too vague"},
                    {"text": "topic bad 2"},
                ],
                "generic_bad": [
                    {"text": "generic bad 1"},
                    {"text": "generic bad 2"},
                ],
            },
        }

        block = DraftPromptsMixin._build_anti_examples_block(rules, "salary")

        assert "[나쁜 예시 — 이렇게 쓰지 마세요]" in block
        assert "- 나쁜 예시 1: topic bad 1" in block
        assert "  이유: too vague" in block
        assert "- 나쁜 예시 2: topic bad 2" in block
        assert "- 나쁜 예시 3: generic bad 1" in block
        assert "generic bad 2" not in block

    def test_anti_examples_block_returns_empty_when_no_examples_exist(self):
        assert DraftPromptsMixin._build_anti_examples_block({"anti_examples": {}}, "missing") == ""


class TestSelectionBriefBlock:
    def test_selection_brief_values_use_profile_values_and_essence_fallback(self):
        assert DraftPromptsMixin._selection_brief_values(
            {
                "selection_summary": "strong reason",
                "audience_need": "reader need",
                "emotion_lane": "emotion lane",
                "empathy_anchor": "profile anchor",
                "spinoff_angle": "spin angle",
            },
            {"opening": "essence opening"},
        ) == {
            "selection_summary": "strong reason",
            "audience_need": "reader need",
            "emotion_lane": "emotion lane",
            "empathy_anchor": "profile anchor",
            "spinoff_angle": "spin angle",
        }
        assert DraftPromptsMixin._selection_brief_values({}, {"opening": "essence opening"}) == {
            "selection_summary": "직장인이 자기 일처럼 반응할 이유가 있는 글",
            "audience_need": "직장인 현실 비교 욕구",
            "emotion_lane": "공감과 웃음의 균형",
            "empathy_anchor": "essence opening",
            "spinoff_angle": "현실 비교, 자기 경험",
        }

    def test_selection_brief_lines_add_twitter_rule_only_for_twitter(self):
        values = {
            "selection_summary": "strong reason",
            "audience_need": "reader need",
            "emotion_lane": "emotion lane",
            "empathy_anchor": "profile anchor",
            "spinoff_angle": "spin angle",
        }

        twitter_lines = DraftPromptsMixin._selection_brief_lines(values, ["twitter"])
        threads_lines = DraftPromptsMixin._selection_brief_lines(values, ["threads"])

        assert twitter_lines[:6] == [
            "[X 편집 브리프]",
            "왜 고름: strong reason",
            "독자 욕구: reader need",
            "감정선: emotion lane",
            "공감 앵커: profile anchor",
            "파생각: spin angle",
        ]
        assert twitter_lines[-1] == "7. <twitter> 안에는 1개 안만 작성 (3안 묶음 금지)"
        assert all("7. <twitter>" not in line for line in threads_lines)

    def test_selection_brief_uses_profile_values_and_twitter_rule(self):
        block = DraftPromptsMixin._build_selection_brief_block(
            {
                "selection_summary": "strong reason",
                "audience_need": "reader need",
                "emotion_lane": "emotion lane",
                "empathy_anchor": "profile anchor",
                "spinoff_angle": "spin angle",
            },
            {"opening": "essence opening"},
            ["twitter"],
        )

        assert "왜 고름: strong reason" in block
        assert "독자 욕구: reader need" in block
        assert "감정선: emotion lane" in block
        assert "공감 앵커: profile anchor" in block
        assert "파생각: spin angle" in block
        assert "7. <twitter> 안에는 1개 안만 작성 (3안 묶음 금지)" in block

    def test_selection_brief_falls_back_to_essence_opening_and_omits_twitter_rule(self):
        block = DraftPromptsMixin._build_selection_brief_block({}, {"opening": "essence opening"}, ["threads"])

        assert "공감 앵커: essence opening" in block
        assert "7. <twitter>" not in block


class TestResearchContextBlock:
    def test_research_context_block_includes_fields_and_high_risk_note(self):
        block = DraftPromptsMixin._build_research_context_block(
            {
                "research_context": {
                    "source_frame": "source frame",
                    "real_issue": "real issue",
                    "universal_value": "universal value",
                    "killer_sentence": "killer sentence",
                    "closure": "closed",
                    "anchor": "anchor text",
                    "conflict_risk": 0.91,
                },
            }
        )

        assert "[오토리서치 컨텍스트 - 반드시 반영]" in block
        assert "- 원문 프레임: source frame" in block
        assert "- 진짜 쟁점: real issue" in block
        assert "- 핵심 사실: universal value" in block
        assert "- 반드시 포함할 킬러 문장: killer sentence" in block
        assert "- 결말 방식: closed" in block
        assert "- 근거 앵커: anchor text" in block
        assert "갈등 위험 높음" in block
        # 쥬팍식: 가치 선언/동어반복은 강제가 아니라 금지로 전환됨
        assert '"이건 ~가 아니라 ~입니다" 식 가치 선언' in block
        assert "느낌점은 1인칭 직설 구어체로, 마지막 줄은 펀치라인으로 끝내세요" in block

    def test_research_conflict_risk_note_handles_high_invalid_and_boundary_values(self):
        assert DraftPromptsMixin._research_conflict_risk_note({"conflict_risk": 0.91}).startswith("\n-")
        assert DraftPromptsMixin._research_conflict_risk_note({"conflict_risk": "bad"}) == ""
        assert DraftPromptsMixin._research_conflict_risk_note({"conflict_risk": 0.8}) == ""

    def test_research_context_block_values_apply_prompt_defaults(self):
        assert DraftPromptsMixin._research_context_block_values({}) == {
            "source_frame": "N/A",
            "real_issue": "N/A",
            "universal_value": "N/A",
            "killer_sentence": "N/A",
            "closure": "open",
            "anchor": "N/A",
        }

    def test_research_context_block_values_keep_present_values(self):
        assert DraftPromptsMixin._research_context_block_values(
            {
                "source_frame": "source",
                "real_issue": "issue",
                "universal_value": "value",
                "killer_sentence": "killer",
                "closure": "closed",
                "anchor": "anchor",
            }
        ) == {
            "source_frame": "source",
            "real_issue": "issue",
            "universal_value": "value",
            "killer_sentence": "killer",
            "closure": "closed",
            "anchor": "anchor",
        }

    def test_research_context_from_post_returns_mapping_context_only(self):
        context = {"source_frame": "source"}

        assert DraftPromptsMixin._research_context_from_post({"research_context": context}) is context
        assert DraftPromptsMixin._research_context_from_post({}) == {}
        assert DraftPromptsMixin._research_context_from_post({"research_context": "invalid"}) == {}

    def test_format_research_context_block_includes_values_and_risk_note(self):
        block = DraftPromptsMixin._format_research_context_block(
            {
                "source_frame": "source",
                "real_issue": "issue",
                "universal_value": "value",
                "killer_sentence": "killer",
                "closure": "closed",
                "anchor": "anchor",
            },
            "\n- risk note",
        )

        assert "- 원문 프레임: source" in block
        assert "- 진짜 쟁점: issue" in block
        assert "- 핵심 사실: value" in block
        assert "- 반드시 포함할 킬러 문장: killer" in block
        assert "- 결말 방식: closed" in block
        assert "- 근거 앵커: anchor\n- risk note" in block
        assert "느낌점은 1인칭 직설 구어체로, 마지막 줄은 펀치라인으로 끝내세요" in block

    def test_research_context_block_uses_defaults_and_ignores_bad_risk(self):
        block = DraftPromptsMixin._build_research_context_block({"research_context": {"conflict_risk": "bad"}})

        assert "- 원문 프레임: N/A" in block
        assert "- 결말 방식: open" in block
        assert "갈등 위험 높음" not in block

    def test_research_context_block_returns_empty_for_missing_or_non_dict_context(self):
        assert DraftPromptsMixin._build_research_context_block({}) == ""
        assert DraftPromptsMixin._build_research_context_block({"research_context": "invalid"}) == ""


class TestAnthropicSystemPrompt:
    def test_system_prompt_parts_trim_and_skip_empty_optional_blocks(self):
        assert DraftPromptsMixin._anthropic_system_prompt_parts(" role ", " ", " memory ") == [
            "role",
            "아래 게시글을 기반으로 발행 가능한 초안을 작성하세요.",
            "memory",
        ]

    def test_system_prompt_joins_role_instruction_voice_and_memory(self):
        block = DraftPromptsMixin._build_anthropic_system_prompt(" role ", " voice ", " memory ")

        assert block == "role\n\n아래 게시글을 기반으로 발행 가능한 초안을 작성하세요.\n\nvoice\n\nmemory"

    def test_system_prompt_skips_empty_optional_blocks(self):
        block = DraftPromptsMixin._build_anthropic_system_prompt("", " ", "")

        assert block == "아래 게시글을 기반으로 발행 가능한 초안을 작성하세요."


class TestReferenceBlocks:
    def test_reference_seed_from_context_uses_title_and_selection_summary(self):
        seed = DraftPromptsMixin._reference_seed_from_context(
            {"title": "title"},
            {"profile": {"selection_summary": "summary"}},
        )

        assert seed == "title|summary"

    def test_reference_seed_from_context_uses_existing_empty_defaults(self):
        assert DraftPromptsMixin._reference_seed_from_context({}, {"profile": {}}) == "|"

    def test_reference_blocks_from_context_uses_title_and_selection_summary_seed(self):
        top_examples = [{"text": "example"}]
        context = {"topic_cluster": "salary", "profile": {"selection_summary": "summary"}}

        with patch.object(DraftPromptsMixin, "_build_reference_blocks", return_value={"examples": "block"}) as build:
            blocks = DraftPromptsMixin._build_reference_blocks_from_context(
                {"title": "title"},
                top_examples,
                context,
            )

        assert blocks == {"examples": "block"}
        build.assert_called_once_with(top_examples, topic_cluster="salary", seed_text="title|summary")

    def test_reference_blocks_delegates_to_example_and_memory_formatters(self):
        top_examples = [{"text": "example"}]

        with (
            patch.object(DraftPromptsMixin, "_format_examples", return_value="examples block") as format_examples,
            patch.object(DraftPromptsMixin, "_format_reviewer_memory", return_value="memory block") as format_memory,
        ):
            blocks = DraftPromptsMixin._build_reference_blocks(top_examples, "salary", "seed text")

        assert blocks == {"examples": "examples block", "reviewer_memory": "memory block"}
        format_examples.assert_called_once_with(top_examples, topic_cluster="salary", seed_text="seed text")
        format_memory.assert_called_once_with(top_examples)


class TestAnthropicUserBlocks:
    def test_user_output_block_values_selects_prompt_output_blocks(self):
        output_blocks = {
            "regulation_context": "regulation context",
            "twitter": "twitter",
            "threads": "threads",
            "newsletter": "newsletter",
            "naver_blog": "naver",
            "image": "image",
            "regulation_check": "regulation check",
            "ignored": "ignored",
        }

        blocks = DraftPromptsMixin._anthropic_user_output_block_values(output_blocks)

        assert blocks == {
            "regulation_context": "regulation context",
            "twitter": "twitter",
            "threads": "threads",
            "newsletter": "newsletter",
            "naver_blog": "naver",
            "image": "image",
            "regulation_check": "regulation check",
        }
        assert list(blocks) == list(_ANTHROPIC_USER_OUTPUT_BLOCK_KEYS)

    def test_user_reference_block_values_selects_prompt_reference_blocks(self):
        reference_blocks = {"examples": "examples", "reviewer_memory": "memory", "ignored": "ignored"}

        blocks = DraftPromptsMixin._anthropic_user_reference_block_values(reference_blocks)

        assert blocks == {"examples": "examples"}
        assert list(blocks) == list(_ANTHROPIC_USER_REFERENCE_BLOCK_KEYS)

    def test_anthropic_user_prompt_values_select_context_fields(self):
        profile = {"profile": True}

        assert DraftPromptsMixin._anthropic_user_prompt_values(
            {
                "content": "content",
                "source": "source",
                "tone": "tone",
                "profile": profile,
                "topic_cluster": "topic",
                "recommended_draft_type": "type",
                "ignored": "ignored",
            }
        ) == {
            "content": "content",
            "source": "source",
            "tone": "tone",
            "profile": profile,
            "topic_cluster": "topic",
            "recommended_draft_type": "type",
        }

    def test_user_blocks_combines_guidance_output_and_reference_blocks(self):
        output_blocks = {
            "regulation_context": "regulation context",
            "twitter": "twitter",
            "threads": "threads",
            "newsletter": "newsletter",
            "naver_blog": "naver",
            "image": "image",
            "regulation_check": "regulation check",
        }
        reference_blocks = {"examples": "examples", "reviewer_memory": "memory"}

        blocks = DraftPromptsMixin._build_anthropic_user_blocks(
            essence_block="essence",
            selection_brief_block="selection",
            comment_trigger_block="comment",
            research_block="research",
            topic_strategy_block="topic",
            thinking_block="thinking",
            anti_examples_block="anti",
            output_blocks=output_blocks,
            reference_blocks=reference_blocks,
        )

        assert blocks == {
            "essence": "essence",
            "selection_brief": "selection",
            "comment_trigger": "comment",
            "research": "research",
            "topic_strategy": "topic",
            "regulation_context": "regulation context",
            "thinking": "thinking",
            "examples": "examples",
            "anti_examples": "anti",
            "twitter": "twitter",
            "threads": "threads",
            "newsletter": "newsletter",
            "naver_blog": "naver",
            "image": "image",
            "regulation_check": "regulation check",
        }
        assert list(blocks) == list(_ANTHROPIC_USER_BLOCK_KEYS)


class TestGuidanceBlocks:
    def test_guidance_context_values_select_prompt_guidance_fields(self):
        essence = {"essence": True}
        profile = {"profile": True}

        assert DraftPromptsMixin._guidance_context_values(
            {
                "essence": essence,
                "profile": profile,
                "topic_cluster": "salary",
                "ignored": "ignored",
            }
        ) == {
            "essence": essence,
            "profile": profile,
            "topic_cluster": "salary",
        }

    def test_guidance_blocks_from_context_delegates_normalized_context(self):
        rules = {"rules": True}
        templates = {"templates": True}
        post_data = {"post": True}
        essence = {"essence": True}
        profile = {"profile": True}
        context = {"essence": essence, "profile": profile, "topic_cluster": "salary"}

        with patch.object(DraftPromptsMixin, "_build_guidance_blocks", return_value={"voice": "block"}) as guidance:
            blocks = DraftPromptsMixin._build_guidance_blocks_from_context(
                rules,
                templates,
                post_data,
                ["twitter"],
                context,
            )

        assert blocks == {"voice": "block"}
        guidance.assert_called_once_with(rules, templates, post_data, essence, profile, ["twitter"], "salary")

    def test_build_guidance_blocks_delegates_to_guidance_block_values(self):
        rules = {"rules": True}
        templates = {"templates": True}
        post_data = {"post": True}
        essence = {"essence": True}
        profile = {"profile": True}
        output_formats = ["twitter"]

        with patch.object(DraftPromptsMixin, "_guidance_block_values", return_value={"voice": "block"}) as values:
            blocks = DraftPromptsMixin._build_guidance_blocks(
                rules,
                templates,
                post_data,
                essence,
                profile,
                output_formats,
                "salary",
            )

        assert blocks == {"voice": "block"}
        values.assert_called_once_with(rules, templates, post_data, essence, profile, output_formats, "salary")

    def test_guidance_blocks_delegates_to_guidance_helpers(self):
        rules = {"rules": True}
        templates = {"templates": True}
        post_data = {"post": True}
        essence = {"essence": True}
        profile = {"profile": True}
        output_formats = ["twitter"]

        with (
            patch.object(DraftPromptsMixin, "_build_voice_block", return_value="voice") as voice,
            patch.object(DraftPromptsMixin, "_build_essence_block", return_value="essence") as essence_block,
            patch.object(DraftPromptsMixin, "_build_research_context_block", return_value="research") as research,
            patch.object(DraftPromptsMixin, "_build_thinking_block", return_value="thinking") as thinking,
            patch.object(DraftPromptsMixin, "_build_topic_strategy_block", return_value="topic") as topic,
            patch.object(DraftPromptsMixin, "_build_anti_examples_block", return_value="anti") as anti,
            patch.object(DraftPromptsMixin, "_build_selection_brief_block", return_value="selection") as selection,
            patch.object(DraftPromptsMixin, "_build_comment_trigger_block", return_value="comment") as comment,
        ):
            blocks = DraftPromptsMixin._build_guidance_blocks(
                rules,
                templates,
                post_data,
                essence,
                profile,
                output_formats,
                "salary",
            )

        assert blocks == {
            "voice": "voice",
            "essence": "essence",
            "research": "research",
            "thinking": "thinking",
            "topic_strategy": "topic",
            "anti_examples": "anti",
            "selection_brief": "selection",
            "comment_trigger": "comment",
        }
        voice.assert_called_once_with(rules)
        essence_block.assert_called_once_with(essence)
        research.assert_called_once_with(post_data)
        thinking.assert_called_once_with(templates)
        topic.assert_called_once_with(rules, "salary")
        anti.assert_called_once_with(rules, "salary")
        selection.assert_called_once_with(profile, essence, output_formats)
        comment.assert_called_once_with(output_formats)


class TestPromptComponentBlocks:
    def test_prompt_component_request_preserves_component_parameters(self):
        post_data = {"title": "title"}
        top_examples = [{"text": "example"}]
        output_formats = ["twitter"]
        context = {"context": True}
        rules = {"rules": True}
        templates = {"templates": True}

        request = DraftPromptsMixin._build_prompt_component_request(
            post_data=post_data,
            top_examples=top_examples,
            output_formats=output_formats,
            draft_format="standard",
            context=context,
            rules=rules,
            templates=templates,
        )

        assert request == _PromptComponentRequest(
            post_data=post_data,
            top_examples=top_examples,
            output_formats=output_formats,
            draft_format="standard",
            context=context,
            rules=rules,
            templates=templates,
        )

    def test_prompt_component_request_from_context_delegates_to_component_request_factory(self):
        post_data = {"title": "title"}
        top_examples = [{"text": "example"}]
        output_formats = ["twitter"]
        context = {"context": True}
        rules = {"rules": True}
        templates = {"templates": True}

        request = DraftPromptsMixin._build_prompt_component_request_from_context(
            post_data=post_data,
            top_examples=top_examples,
            output_formats=output_formats,
            draft_format="standard",
            context=context,
            rules=rules,
            templates=templates,
        )

        assert request == _PromptComponentRequest(
            post_data=post_data,
            top_examples=top_examples,
            output_formats=output_formats,
            draft_format="standard",
            context=context,
            rules=rules,
            templates=templates,
        )

    def test_prompt_component_blocks_combines_prepared_block_groups(self):
        obj = object.__new__(DraftPromptsMixin)
        post_data = {"title": "title"}
        top_examples = [{"text": "example"}]
        context = {"context": True}
        rules = {"rules": True}
        templates = {"templates": True}

        with (
            patch.object(obj, "_build_output_format_blocks_from_context", return_value={"twitter": "output"}) as output,
            patch.object(obj, "_build_guidance_blocks_from_context", return_value={"voice": "guidance"}) as guidance,
            patch.object(obj, "_build_reference_blocks_from_context", return_value={"examples": "reference"}) as refs,
        ):
            blocks = obj._build_prompt_component_blocks(
                post_data=post_data,
                top_examples=top_examples,
                output_formats=["twitter"],
                draft_format="standard",
                context=context,
                rules=rules,
                templates=templates,
            )

        assert blocks == {
            "output": {"twitter": "output"},
            "guidance": {"voice": "guidance"},
            "reference": {"examples": "reference"},
        }
        assert list(blocks) == list(_PROMPT_COMPONENT_BLOCK_KEYS)
        output.assert_called_once_with(templates, rules, ["twitter"], "standard", context)
        guidance.assert_called_once_with(rules, templates, post_data, ["twitter"], context)
        refs.assert_called_once_with(post_data, top_examples, context)

    def test_prompt_component_block_values_build_prepared_block_groups(self):
        obj = object.__new__(DraftPromptsMixin)
        request = _PromptComponentRequest(
            post_data={"title": "title"},
            top_examples=[{"text": "example"}],
            output_formats=["twitter"],
            draft_format="standard",
            context={"context": True},
            rules={"rules": True},
            templates={"templates": True},
        )

        with (
            patch.object(obj, "_build_output_format_blocks_from_context", return_value={"twitter": "output"}) as output,
            patch.object(obj, "_build_guidance_blocks_from_context", return_value={"voice": "guidance"}) as guidance,
            patch.object(obj, "_build_reference_blocks_from_context", return_value={"examples": "reference"}) as refs,
        ):
            blocks = obj._prompt_component_block_values(request)

        assert blocks == {
            "output": {"twitter": "output"},
            "guidance": {"voice": "guidance"},
            "reference": {"examples": "reference"},
        }
        output.assert_called_once_with(
            request.templates,
            request.rules,
            request.output_formats,
            request.draft_format,
            request.context,
        )
        guidance.assert_called_once_with(
            request.rules,
            request.templates,
            request.post_data,
            request.output_formats,
            request.context,
        )
        refs.assert_called_once_with(request.post_data, request.top_examples, request.context)

    def test_prompt_component_block_groups_build_named_block_groups(self):
        obj = object.__new__(DraftPromptsMixin)
        request = _PromptComponentRequest(
            post_data={"title": "title"},
            top_examples=[{"text": "example"}],
            output_formats=["twitter"],
            draft_format="standard",
            context={"context": True},
            rules={"rules": True},
            templates={"templates": True},
        )

        with (
            patch.object(obj, "_build_output_format_blocks_from_context", return_value={"twitter": "output"}) as output,
            patch.object(obj, "_build_guidance_blocks_from_context", return_value={"voice": "guidance"}) as guidance,
            patch.object(obj, "_build_reference_blocks_from_context", return_value={"examples": "reference"}) as refs,
        ):
            groups = obj._prompt_component_block_groups(request)

        assert groups == _PromptComponentBlockGroups(
            output_blocks={"twitter": "output"},
            guidance_blocks={"voice": "guidance"},
            reference_blocks={"examples": "reference"},
        )
        output.assert_called_once_with(
            request.templates,
            request.rules,
            request.output_formats,
            request.draft_format,
            request.context,
        )
        guidance.assert_called_once_with(
            request.rules,
            request.templates,
            request.post_data,
            request.output_formats,
            request.context,
        )
        refs.assert_called_once_with(request.post_data, request.top_examples, request.context)

    def test_prompt_component_blocks_from_request_combines_prepared_block_groups(self):
        obj = object.__new__(DraftPromptsMixin)
        request = _PromptComponentRequest(
            post_data={"title": "title"},
            top_examples=[{"text": "example"}],
            output_formats=["twitter"],
            draft_format="standard",
            context={"context": True},
            rules={"rules": True},
            templates={"templates": True},
        )

        with (
            patch.object(obj, "_build_output_format_blocks_from_context", return_value={"twitter": "output"}) as output,
            patch.object(obj, "_build_guidance_blocks_from_context", return_value={"voice": "guidance"}) as guidance,
            patch.object(obj, "_build_reference_blocks_from_context", return_value={"examples": "reference"}) as refs,
        ):
            blocks = obj._build_prompt_component_blocks_from_request(request)

        assert blocks == {
            "output": {"twitter": "output"},
            "guidance": {"voice": "guidance"},
            "reference": {"examples": "reference"},
        }
        assert list(blocks) == list(_PROMPT_COMPONENT_BLOCK_KEYS)
        output.assert_called_once_with(
            request.templates,
            request.rules,
            request.output_formats,
            request.draft_format,
            request.context,
        )
        guidance.assert_called_once_with(
            request.rules,
            request.templates,
            request.post_data,
            request.output_formats,
            request.context,
        )
        refs.assert_called_once_with(request.post_data, request.top_examples, request.context)


class TestPromptTemplateConfig:
    @patch("pipeline.draft_prompts._load_draft_rules")
    def test_load_prompt_template_config_returns_rules_templates_and_configured_role(self, mock_rules):
        mock_rules.return_value = {"prompt_templates": {"system_role": "configured role"}}

        rules, templates, system_role = DraftPromptsMixin._load_prompt_template_config()

        assert rules == {"prompt_templates": {"system_role": "configured role"}}
        assert templates == {"system_role": "configured role"}
        assert system_role == "configured role"

    @patch("pipeline.draft_prompts._load_draft_rules", return_value={})
    def test_load_prompt_template_config_uses_existing_default_role(self, mock_rules):
        rules, templates, system_role = DraftPromptsMixin._load_prompt_template_config()

        assert rules == {}
        assert templates == {}
        assert system_role == "당신은 직장인 대상 콘텐츠를 큐레이션하는 시니어 에디터입니다."


class TestCommentTriggerBlock:
    def test_comment_trigger_prompt_contains_trigger_contract(self):
        prompt = DraftPromptsMixin._comment_trigger_prompt()

        assert "[독자가 댓글을 달고 싶어지는 4가지 트리거" in prompt
        assert "식별감 (Identifiability)" in prompt
        assert "입장 (Stance)" in prompt
        assert "오픈루프 마무리 (Open Loop)" in prompt
        assert "구체 앵커 (Anchor)" in prompt

    def test_comment_trigger_block_only_for_short_social_formats(self):
        assert DraftPromptsMixin._build_comment_trigger_block(["newsletter"]) == ""
        assert (
            DraftPromptsMixin._build_comment_trigger_block(["twitter"]) == DraftPromptsMixin._comment_trigger_prompt()
        )
        assert (
            DraftPromptsMixin._build_comment_trigger_block(["threads"]) == DraftPromptsMixin._comment_trigger_prompt()
        )


class TestBuildPromptContext:
    def _make_instance(self):
        obj = object.__new__(DraftPromptsMixin)
        obj.tone = "default tone"
        return obj

    def test_content_profile_returns_existing_mapping_or_empty_default(self):
        profile = {"topic_cluster": "salary"}

        assert DraftPromptsMixin._content_profile({"content_profile": profile}) is profile
        assert DraftPromptsMixin._content_profile({}) == {}
        assert DraftPromptsMixin._content_profile({"content_profile": None}) == {}

    def test_prompt_profile_values_apply_existing_defaults(self):
        assert DraftPromptsMixin._prompt_profile_values({}) == {
            "topic_cluster": "기타",
            "recommended_draft_type": "공감형",
            "empathy_anchor": "",
            "spinoff_angle": "",
        }

    def test_prompt_profile_values_keep_present_profile_fields(self):
        assert DraftPromptsMixin._prompt_profile_values(
            {
                "topic_cluster": "salary",
                "recommended_draft_type": "정보형",
                "empathy_anchor": "anchor",
                "spinoff_angle": "spin",
            }
        ) == {
            "topic_cluster": "salary",
            "recommended_draft_type": "정보형",
            "empathy_anchor": "anchor",
            "spinoff_angle": "spin",
        }

    @patch("pipeline.draft_prompts._load_draft_rules", return_value={"tone_mapping": {"salary": "salary tone"}})
    def test_prompt_base_values_keep_existing_content_source_and_tone_contract(self, mock_rules):
        obj = self._make_instance()

        values = obj._prompt_base_values(
            {
                "source": "custom",
                "content": "body",
                "content_profile": {"topic_cluster": "salary"},
            }
        )

        assert values == {
            "content": "body",
            "source": "custom",
            "tone": "salary tone",
        }

    @patch("pipeline.draft_prompts._load_draft_rules", return_value={"tone_mapping": {}})
    def test_prompt_base_values_apply_existing_source_default(self, mock_rules):
        obj = self._make_instance()

        assert obj._prompt_base_values({"content": "body"}) == {
            "content": "body",
            "source": "블라인드",
            "tone": "default tone",
        }

    def test_prompt_context_values_merge_essence_profile_base_and_profile_values(self):
        essence = {"essence": True}
        profile = {"profile": True}

        assert DraftPromptsMixin._prompt_context_values(
            essence=essence,
            profile=profile,
            profile_values={
                "topic_cluster": "salary",
                "recommended_draft_type": "정보형",
                "empathy_anchor": "anchor",
                "spinoff_angle": "spin",
            },
            base_values={"content": "body", "source": "custom", "tone": "tone"},
        ) == {
            "essence": essence,
            "content": "body",
            "source": "custom",
            "tone": "tone",
            "profile": profile,
            "topic_cluster": "salary",
            "recommended_draft_type": "정보형",
            "empathy_anchor": "anchor",
            "spinoff_angle": "spin",
        }

    @patch("pipeline.draft_prompts._load_draft_rules", return_value={"tone_mapping": {}, "emotion_rules": []})
    def test_prompt_context_uses_defaults_for_missing_profile(self, mock_rules):
        obj = self._make_instance()

        context = obj._build_prompt_context({"content": "short content"})

        assert list(context) == list(_PROMPT_CONTEXT_KEYS)
        assert context["content"] == "short content"
        assert context["source"] == "블라인드"
        assert context["tone"] == "default tone"
        assert context["profile"] == {}
        assert context["topic_cluster"] == "기타"
        assert context["recommended_draft_type"] == "공감형"
        assert context["empathy_anchor"] == ""
        assert context["spinoff_angle"] == ""
        assert context["essence"]["key_numbers"] == []

    @patch("pipeline.draft_prompts._load_draft_rules", return_value={"tone_mapping": {"salary": "salary tone"}})
    def test_prompt_context_uses_profile_values_and_topic_tone(self, mock_rules):
        obj = self._make_instance()
        profile = {
            "topic_cluster": "salary",
            "recommended_draft_type": "정보형",
            "empathy_anchor": "anchor",
            "spinoff_angle": "spin",
        }

        context = obj._build_prompt_context({"source": "custom", "content": "body", "content_profile": profile})

        assert context["source"] == "custom"
        assert context["tone"] == "salary tone"
        assert context["profile"] is profile
        assert context["topic_cluster"] == "salary"
        assert context["recommended_draft_type"] == "정보형"
        assert context["empathy_anchor"] == "anchor"
        assert context["spinoff_angle"] == "spin"


class TestAnthropicUserPrompt:
    def _blocks(self):
        return {
            "essence": "essence block",
            "selection_brief": "selection block",
            "comment_trigger": "comment block",
            "research": "research block",
            "topic_strategy": "topic strategy block",
            "regulation_context": "regulation context",
            "thinking": "thinking block",
            "examples": "examples block",
            "anti_examples": "anti examples block",
            "twitter": "twitter block",
            "threads": "threads block",
            "newsletter": "newsletter block",
            "naver_blog": "naver blog block",
            "image": "image block",
            "regulation_check": "regulation check block",
        }

    def test_post_info_section_values_apply_existing_defaults(self):
        assert DraftPromptsMixin._post_info_section_values({}, content="content text", source="blind") == {
            "source": "blind",
            "title": "",
            "content": "content text",
            "category": "general",
            "likes": 0,
            "comments": 0,
        }

    def test_post_info_section_values_keep_present_metadata(self):
        assert DraftPromptsMixin._post_info_section_values(
            {"title": "title", "category": "money", "likes": 7, "comments": 3},
            content="content text",
            source="blind",
        ) == {
            "source": "blind",
            "title": "title",
            "content": "content text",
            "category": "money",
            "likes": 7,
            "comments": 3,
        }

    def test_post_info_section_lines_include_metadata_and_essence(self):
        assert DraftPromptsMixin._post_info_section_lines(
            {
                "source": "blind",
                "title": "title",
                "content": "content text",
                "category": "money",
                "likes": 7,
                "comments": 3,
            },
            "essence block",
        ) == [
            "[게시글 정보]",
            "출처: blind",
            "제목: title",
            "본문: content text",
            "카테고리: money",
            "공감수: 7 | 댓글수: 3",
            "essence block",
        ]

    def test_format_post_info_section_includes_values_and_essence(self):
        section = DraftPromptsMixin._format_post_info_section(
            {
                "source": "blind",
                "title": "title",
                "content": "content text",
                "category": "money",
                "likes": 7,
                "comments": 3,
            },
            "essence block",
        )

        assert section == (
            "[게시글 정보]\n"
            "출처: blind\n"
            "제목: title\n"
            "본문: content text\n"
            "카테고리: money\n"
            "공감수: 7 | 댓글수: 3\n"
            "essence block"
        )

    def test_post_info_section_includes_source_metadata_and_essence(self):
        section = DraftPromptsMixin._build_post_info_section(
            post_data={"title": "title", "category": "money", "likes": 7, "comments": 3},
            content="content text",
            source="blind",
            essence_block="essence block",
        )

        assert section == (
            "[게시글 정보]\n"
            "출처: blind\n"
            "제목: title\n"
            "본문: content text\n"
            "카테고리: money\n"
            "공감수: 7 | 댓글수: 3\n"
            "essence block"
        )

    def test_content_profile_section_values_apply_defaults_and_scores(self):
        assert DraftPromptsMixin._content_profile_section_values(
            {"hook_type": "hook", "audience_fit": "직장인", "publishability_score": 83},
            topic_cluster="salary",
            recommended_draft_type="공감형",
        ) == {
            "topic_cluster": "salary",
            "hook_type": "hook",
            "emotion_axis": "공감",
            "audience_fit": "직장인",
            "recommended_draft_type": "공감형",
            "publishability_score": 83,
            "performance_score": "N/A",
        }

    def test_content_profile_section_lines_include_values_in_prompt_order(self):
        assert DraftPromptsMixin._content_profile_section_lines(
            {
                "topic_cluster": "salary",
                "hook_type": "hook",
                "emotion_axis": "공감",
                "audience_fit": "직장인",
                "recommended_draft_type": "공감형",
                "publishability_score": 83,
                "performance_score": 0,
            }
        ) == [
            "[콘텐츠 프로필]",
            "토픽 클러스터: salary",
            "훅 타입: hook",
            "감정 축: 공감",
            "대상 독자: 직장인",
            "추천 초안 타입: 공감형",
            "발행 적합도 점수: 83",
            "성과 예측 점수: 0",
        ]

    def test_format_content_profile_section_includes_values(self):
        section = DraftPromptsMixin._format_content_profile_section(
            {
                "topic_cluster": "salary",
                "hook_type": "hook",
                "emotion_axis": "공감",
                "audience_fit": "직장인",
                "recommended_draft_type": "공감형",
                "publishability_score": 83,
                "performance_score": 0,
            }
        )

        assert section == (
            "[콘텐츠 프로필]\n"
            "토픽 클러스터: salary\n"
            "훅 타입: hook\n"
            "감정 축: 공감\n"
            "대상 독자: 직장인\n"
            "추천 초안 타입: 공감형\n"
            "발행 적합도 점수: 83\n"
            "성과 예측 점수: 0"
        )

    def test_content_profile_section_includes_profile_defaults_and_scores(self):
        section = DraftPromptsMixin._build_content_profile_section(
            profile={"hook_type": "hook", "audience_fit": "직장인", "publishability_score": 83},
            topic_cluster="salary",
            recommended_draft_type="공감형",
        )

        assert section == (
            "[콘텐츠 프로필]\n"
            "토픽 클러스터: salary\n"
            "훅 타입: hook\n"
            "감정 축: 공감\n"
            "대상 독자: 직장인\n"
            "추천 초안 타입: 공감형\n"
            "발행 적합도 점수: 83\n"
            "성과 예측 점수: N/A"
        )

    def test_user_prompt_block_tail_parts_preserve_order(self):
        assert list(_ANTHROPIC_USER_PROMPT_TAIL_KEYS) == [
            "selection_brief",
            "comment_trigger",
            "research",
            "topic_strategy",
            "regulation_context",
            "thinking",
            "examples",
            "anti_examples",
            "twitter",
            "threads",
            "newsletter",
            "naver_blog",
            "image",
            "regulation_check",
        ]
        assert DraftPromptsMixin._user_prompt_block_tail_parts(self._blocks()) == [
            "selection block",
            "comment block",
            "research block",
            "topic strategy block",
            "regulation context",
            "thinking block",
            "examples block",
            "anti examples block",
            "twitter block",
            "threads block",
            "newsletter block",
            "naver blog block",
            "image block",
            "regulation check block",
        ]

    def test_user_prompt_block_tail_preserves_order(self):
        tail = DraftPromptsMixin._build_user_prompt_block_tail(self._blocks())

        assert tail.splitlines() == [
            "selection block",
            "comment block",
            "research block",
            "topic strategy block",
            "regulation context",
            "thinking block",
            "examples block",
            "anti examples block",
            "twitter block",
            "threads block",
            "newsletter block",
            "naver blog block",
            "image block",
            "regulation check block",
        ]

    def test_anthropic_user_prompt_parts_include_separators_and_tone_header(self):
        assert DraftPromptsMixin._anthropic_user_prompt_parts(
            post_info_section="post info",
            content_profile_section="profile",
            block_tail="blocks",
            tone="tone guide",
        ) == ["post info", "", "profile", "blocks", "[톤 가이드]", "tone guide", ""]

    def test_format_anthropic_user_prompt_joins_sections_and_tone(self):
        prompt = DraftPromptsMixin._format_anthropic_user_prompt(
            post_info_section="post info",
            content_profile_section="profile",
            block_tail="blocks",
            tone="tone guide",
        )

        assert prompt == "post info\n\nprofile\nblocks\n[톤 가이드]\ntone guide\n"

    def test_anthropic_user_prompt_section_values_delegate_to_section_builders(self):
        post_data = {"post": True}
        profile = {"profile": True}
        blocks = {**self._blocks(), "essence": "essence block"}

        with (
            patch.object(DraftPromptsMixin, "_build_post_info_section", return_value="post info") as post_info,
            patch.object(DraftPromptsMixin, "_build_content_profile_section", return_value="profile") as profile_build,
            patch.object(DraftPromptsMixin, "_build_user_prompt_block_tail", return_value="blocks") as tail,
        ):
            sections = DraftPromptsMixin._anthropic_user_prompt_section_values(
                post_data=post_data,
                content="content text",
                source="blind",
                profile=profile,
                topic_cluster="salary",
                recommended_draft_type="공감형",
                blocks=blocks,
            )

        assert sections == {"post_info": "post info", "content_profile": "profile", "block_tail": "blocks"}
        post_info.assert_called_once_with(post_data, "content text", "blind", "essence block")
        profile_build.assert_called_once_with(profile, "salary", "공감형")
        tail.assert_called_once_with(blocks)

    def test_user_prompt_includes_post_metadata_profile_defaults_and_blocks(self):
        prompt = DraftPromptsMixin._build_anthropic_user_prompt(
            post_data={"title": "title", "content": "ignored", "likes": 7, "comments": 3},
            content="content text",
            source="blind",
            tone="tone guide",
            profile={},
            topic_cluster="salary",
            recommended_draft_type="공감형",
            blocks=self._blocks(),
        )

        assert prompt.startswith("[게시글 정보]\n출처: blind")
        assert "제목: title" in prompt
        assert "본문: content text" in prompt
        assert "카테고리: general" in prompt
        assert "공감수: 7 | 댓글수: 3" in prompt
        assert "훅 타입: 공감형" in prompt
        assert "감정 축: 공감" in prompt
        assert "대상 독자: 범용" in prompt
        assert "추천 초안 타입: 공감형" in prompt
        assert "성과 예측 점수: N/A" in prompt
        assert prompt.endswith("[톤 가이드]\ntone guide\n")

    def test_user_prompt_preserves_block_order(self):
        prompt = DraftPromptsMixin._build_anthropic_user_prompt(
            post_data={},
            content="content",
            source="source",
            tone="tone",
            profile={},
            topic_cluster="topic",
            recommended_draft_type="type",
            blocks=self._blocks(),
        )

        ordered = [
            "essence block",
            "selection block",
            "comment block",
            "research block",
            "topic strategy block",
            "regulation context",
            "thinking block",
            "examples block",
            "anti examples block",
            "twitter block",
            "threads block",
            "newsletter block",
            "naver blog block",
            "image block",
            "regulation check block",
        ]
        positions = [prompt.index(item) for item in ordered]
        assert positions == sorted(positions)


class TestAnthropicPromptResult:
    def test_anthropic_prompt_result_request_preserves_prompt_inputs(self):
        post_data = {"title": "title"}
        context = {"content": "content text"}
        guidance_blocks = {"voice": "voice block"}
        output_blocks = {"twitter": "twitter block"}
        reference_blocks = {"examples": "examples block"}

        request = DraftPromptsMixin._build_anthropic_prompt_result_request(
            post_data=post_data,
            context=context,
            system_role="system role",
            guidance_blocks=guidance_blocks,
            output_blocks=output_blocks,
            reference_blocks=reference_blocks,
        )

        assert request == _AnthropicPromptResultRequest(
            post_data=post_data,
            context=context,
            system_role="system role",
            guidance_blocks=guidance_blocks,
            output_blocks=output_blocks,
            reference_blocks=reference_blocks,
        )

    def test_anthropic_prompt_result_request_from_components_uses_component_groups(self):
        post_data = {"title": "title"}
        context = {"content": "content text"}
        component_blocks = {
            "guidance": {"voice": "voice block"},
            "output": {"twitter": "twitter block"},
            "reference": {"reviewer_memory": "memory block"},
        }

        request = DraftPromptsMixin._build_anthropic_prompt_result_request_from_components(
            post_data=post_data,
            context=context,
            system_role="system role",
            component_blocks=component_blocks,
        )

        assert request == _AnthropicPromptResultRequest(
            post_data=post_data,
            context=context,
            system_role="system role",
            guidance_blocks={"voice": "voice block"},
            output_blocks={"twitter": "twitter block"},
            reference_blocks={"reviewer_memory": "memory block"},
        )

    def test_anthropic_prompt_result_from_components_delegates_result_request(self):
        obj = object.__new__(DraftPromptsMixin)
        post_data = {"title": "title"}
        context = {"content": "content text"}
        component_blocks = {
            "guidance": {"voice": "voice block"},
            "output": {"twitter": "twitter block"},
            "reference": {"reviewer_memory": "memory block"},
        }

        with patch.object(obj, "_build_anthropic_prompt_result_from_request", return_value="prompt") as result_builder:
            prompt = obj._build_anthropic_prompt_result_from_components(
                post_data=post_data,
                context=context,
                system_role="system role",
                component_blocks=component_blocks,
            )

        assert prompt == "prompt"
        result_builder.assert_called_once_with(
            _AnthropicPromptResultRequest(
                post_data=post_data,
                context=context,
                system_role="system role",
                guidance_blocks={"voice": "voice block"},
                output_blocks={"twitter": "twitter block"},
                reference_blocks={"reviewer_memory": "memory block"},
            )
        )

    def test_combined_anthropic_prompt_text_joins_system_and_user_prompt(self):
        assert DraftPromptsMixin._combined_anthropic_prompt_text("system prompt", "user prompt") == (
            "system prompt\n\nuser prompt"
        )
        assert DraftPromptsMixin._combined_anthropic_prompt_text("", "user prompt") == "user prompt"

    def test_prompt_result_from_request_builds_split_prompt_metadata(self):
        obj = object.__new__(DraftPromptsMixin)
        request = _AnthropicPromptResultRequest(
            post_data={"title": "title"},
            context={"content": "content text"},
            system_role="system role",
            guidance_blocks={"voice": "voice block"},
            output_blocks={"twitter": "twitter block"},
            reference_blocks={"reviewer_memory": "memory block"},
        )

        with (
            patch.object(obj, "_build_anthropic_system_prompt", return_value="system prompt") as system_prompt,
            patch.object(obj, "_build_anthropic_user_prompt_from_request", return_value="user prompt") as user_prompt,
        ):
            prompt = obj._build_anthropic_prompt_result_from_request(request)

        assert isinstance(prompt, DraftPrompt)
        assert str(prompt) == "system prompt\n\nuser prompt"
        assert prompt.anthropic_system_prompt == "system prompt"
        assert prompt.anthropic_user_prompt == "user prompt"
        system_prompt.assert_called_once_with("system role", "voice block", "memory block")
        user_prompt.assert_called_once_with(
            _AnthropicUserPromptRequest(
                post_data={"title": "title"},
                context={"content": "content text"},
                guidance_blocks={"voice": "voice block"},
                output_blocks={"twitter": "twitter block"},
                reference_blocks={"reviewer_memory": "memory block"},
            )
        )

    def test_system_prompt_from_request_uses_system_role_voice_and_memory(self):
        obj = object.__new__(DraftPromptsMixin)
        request = _AnthropicPromptResultRequest(
            post_data={"title": "title"},
            context={"content": "content text"},
            system_role="system role",
            guidance_blocks={"voice": "voice block"},
            output_blocks={"twitter": "twitter block"},
            reference_blocks={"reviewer_memory": "memory block"},
        )

        with patch.object(obj, "_build_anthropic_system_prompt", return_value="system prompt") as build_system:
            prompt = obj._build_anthropic_system_prompt_from_request(request)

        assert prompt == "system prompt"
        build_system.assert_called_once_with("system role", "voice block", "memory block")

    def test_anthropic_user_prompt_request_preserves_prompt_inputs(self):
        post_data = {"title": "title"}
        context = {"content": "content text"}
        guidance_blocks = {"voice": "voice block"}
        output_blocks = {"twitter": "twitter block"}
        reference_blocks = {"examples": "examples block"}

        request = DraftPromptsMixin._build_anthropic_user_prompt_request(
            post_data=post_data,
            context=context,
            guidance_blocks=guidance_blocks,
            output_blocks=output_blocks,
            reference_blocks=reference_blocks,
        )

        assert request == _AnthropicUserPromptRequest(
            post_data=post_data,
            context=context,
            guidance_blocks=guidance_blocks,
            output_blocks=output_blocks,
            reference_blocks=reference_blocks,
        )

    def test_user_blocks_from_request_maps_guidance_output_and_reference_blocks(self):
        obj = object.__new__(DraftPromptsMixin)
        request = _AnthropicUserPromptRequest(
            post_data={"title": "title"},
            context={"content": "content text"},
            guidance_blocks={
                "essence": "essence block",
                "selection_brief": "selection block",
                "comment_trigger": "comment block",
                "research": "research block",
                "topic_strategy": "topic block",
                "thinking": "thinking block",
                "anti_examples": "anti block",
            },
            output_blocks={"twitter": "twitter block"},
            reference_blocks={"examples": "examples block"},
        )

        with patch.object(obj, "_build_anthropic_user_blocks", return_value={"tail": "block"}) as build_blocks:
            blocks = obj._build_anthropic_user_blocks_from_request(request)

        assert blocks == {"tail": "block"}
        build_blocks.assert_called_once_with(
            essence_block="essence block",
            selection_brief_block="selection block",
            comment_trigger_block="comment block",
            research_block="research block",
            topic_strategy_block="topic block",
            thinking_block="thinking block",
            anti_examples_block="anti block",
            output_blocks={"twitter": "twitter block"},
            reference_blocks={"examples": "examples block"},
        )

    def test_user_prompt_from_request_combines_guidance_output_and_reference_blocks(self):
        obj = object.__new__(DraftPromptsMixin)
        request = _AnthropicUserPromptRequest(
            post_data={"title": "title"},
            context={
                "content": "content text",
                "source": "blind",
                "tone": "tone guide",
                "profile": {},
                "topic_cluster": "salary",
                "recommended_draft_type": "empathy",
            },
            guidance_blocks={
                "essence": "essence block",
                "selection_brief": "selection block",
                "comment_trigger": "comment block",
                "research": "research block",
                "topic_strategy": "topic block",
                "thinking": "thinking block",
                "anti_examples": "anti block",
            },
            output_blocks={
                "regulation_context": "regulation context",
                "twitter": "twitter block",
                "threads": "threads block",
                "newsletter": "newsletter block",
                "naver_blog": "naver blog block",
                "image": "image block",
                "regulation_check": "regulation check",
            },
            reference_blocks={"examples": "examples block", "reviewer_memory": "memory block"},
        )

        prompt = obj._build_anthropic_user_prompt_from_request(request)

        assert "blind" in prompt
        assert "title" in prompt
        assert "selection block" in prompt
        assert "twitter block" in prompt
        assert "examples block" in prompt
        assert "tone guide" in prompt

    def test_user_prompt_from_blocks_combines_guidance_output_and_reference_blocks(self):
        obj = object.__new__(DraftPromptsMixin)
        prompt = obj._build_anthropic_user_prompt_from_blocks(
            post_data={"title": "title"},
            context={
                "content": "content text",
                "source": "blind",
                "tone": "tone guide",
                "profile": {},
                "topic_cluster": "salary",
                "recommended_draft_type": "공감형",
            },
            guidance_blocks={
                "essence": "essence block",
                "selection_brief": "selection block",
                "comment_trigger": "comment block",
                "research": "research block",
                "topic_strategy": "topic block",
                "thinking": "thinking block",
                "anti_examples": "anti block",
            },
            output_blocks={
                "regulation_context": "regulation context",
                "twitter": "twitter block",
                "threads": "threads block",
                "newsletter": "newsletter block",
                "naver_blog": "naver blog block",
                "image": "image block",
                "regulation_check": "regulation check",
            },
            reference_blocks={"examples": "examples block", "reviewer_memory": "memory block"},
        )

        assert prompt.startswith("[게시글 정보]\n출처: blind")
        assert "selection block" in prompt
        assert "twitter block" in prompt
        assert "examples block" in prompt
        assert prompt.endswith("[톤 가이드]\ntone guide\n")

    def test_prompt_result_preserves_combined_text_and_split_metadata(self):
        obj = object.__new__(DraftPromptsMixin)
        context = {
            "content": "content text",
            "source": "blind",
            "tone": "tone guide",
            "profile": {"hook_type": "hook"},
            "topic_cluster": "salary",
            "recommended_draft_type": "공감형",
        }
        guidance_blocks = {
            "voice": "voice block",
            "essence": "essence block",
            "selection_brief": "selection block",
            "comment_trigger": "comment block",
            "research": "research block",
            "topic_strategy": "topic block",
            "thinking": "thinking block",
            "anti_examples": "anti block",
        }
        output_blocks = {
            "regulation_context": "regulation context",
            "twitter": "twitter block",
            "threads": "threads block",
            "newsletter": "newsletter block",
            "naver_blog": "naver blog block",
            "image": "image block",
            "regulation_check": "regulation check",
        }
        reference_blocks = {"examples": "examples block", "reviewer_memory": "memory block"}

        prompt = obj._build_anthropic_prompt_result(
            post_data={"title": "title"},
            context=context,
            system_role="system role",
            guidance_blocks=guidance_blocks,
            output_blocks=output_blocks,
            reference_blocks=reference_blocks,
        )

        assert isinstance(prompt, DraftPrompt)
        assert prompt.anthropic_system_prompt == (
            "system role\n\n아래 게시글을 기반으로 발행 가능한 초안을 작성하세요.\n\nvoice block\n\nmemory block"
        )
        assert prompt.anthropic_user_prompt.startswith("[게시글 정보]\n출처: blind")
        assert "훅 타입: hook" in prompt.anthropic_user_prompt
        assert "selection block" in prompt.anthropic_user_prompt
        assert "regulation check" in prompt.anthropic_user_prompt
        assert str(prompt) == f"{prompt.anthropic_system_prompt}\n\n{prompt.anthropic_user_prompt}".strip()


class TestThinkingBlock:
    def test_thinking_block_prefers_configured_template(self):
        assert DraftPromptsMixin._build_thinking_block({"thinking_framework": "configured thinking"}) == (
            "configured thinking"
        )

    def test_thinking_block_uses_default_when_template_missing(self):
        block = DraftPromptsMixin._build_thinking_block({})

        assert block == _DEFAULT_THINKING_BLOCK
        assert "[사고 과정 — <thinking> 태그 안에 작성]" in block
        assert "반드시 <thinking> 와 </thinking> 태그 안에만 작성하세요." in block


class TestVoiceBlock:
    def test_brand_voice_bullet_lines_formats_indented_bullets(self):
        assert DraftPromptsMixin._brand_voice_bullet_lines(["plain", "specific"]) == "  - plain\n  - specific"
        assert DraftPromptsMixin._brand_voice_bullet_lines([]) == ""

    def test_brand_voice_block_values_format_present_values(self):
        assert DraftPromptsMixin._brand_voice_block_values(
            {
                "persona": "editor",
                "voice_traits": ["plain", "specific"],
                "forbidden_expressions": ["viral"],
                "examples": {"good": "good copy", "bad": "bad copy"},
            }
        ) == {
            "persona": "editor",
            "traits": "  - plain\n  - specific",
            "forbidden": "  - viral",
            "good_example": "good copy",
            "bad_example": "bad copy",
        }

    def test_brand_voice_block_values_apply_existing_defaults(self):
        assert DraftPromptsMixin._brand_voice_block_values({}) == {
            "persona": "",
            "traits": "",
            "forbidden": "",
            "good_example": "",
            "bad_example": "",
        }

    def test_format_brand_voice_block_includes_values(self):
        block = DraftPromptsMixin._format_brand_voice_block(
            {
                "persona": "editor",
                "traits": "  - plain",
                "forbidden": "  - viral",
                "good_example": "good copy",
                "bad_example": "bad copy",
            }
        )

        assert "[보이스 가이드 — 반드시 준수]" in block
        assert "페르소나: editor" in block
        assert "말투 규칙:\n  - plain" in block
        assert "좋은 예: good copy" in block
        assert "나쁜 예: bad copy" in block
        assert "아래 표현은 AI스럽거나 상투적이므로 절대 사용하지 마세요:\n  - viral" in block

    def test_brand_voice_block_returns_empty_without_config(self):
        assert DraftPromptsMixin._build_brand_voice_block({}) == ""

    def test_brand_voice_block_includes_configured_fields(self):
        block = DraftPromptsMixin._build_brand_voice_block(
            {
                "persona": "editor",
                "voice_traits": ["plain", "specific"],
                "forbidden_expressions": ["viral"],
                "examples": {"good": "good copy", "bad": "bad copy"},
            }
        )

        assert "[보이스 가이드 — 반드시 준수]" in block
        assert "페르소나: editor" in block
        assert "  - plain" in block
        assert "  - viral" in block
        assert "좋은 예: good copy" in block
        assert "나쁜 예: bad copy" in block

    def test_cliche_watchlist_lines_format_and_cap_entries(self):
        lines = DraftPromptsMixin._cliche_watchlist_lines([f"cliche {i}" for i in range(25)])

        assert '  - "cliche 0"' in lines
        assert '  - "cliche 19"' in lines
        assert '  - "cliche 20"' not in lines
        assert DraftPromptsMixin._cliche_watchlist_lines([]) == ""

    def test_format_cliche_watchlist_block_includes_lines(self):
        block = DraftPromptsMixin._format_cliche_watchlist_block('  - "cliche"')

        assert "[절대 사용 금지 — 클리셰 목록]" in block
        assert "아래 표현을 하나라도 사용하면 재생성 대상입니다:" in block
        assert '  - "cliche"' in block

    def test_cliche_watchlist_block_returns_empty_without_cliches(self):
        assert DraftPromptsMixin._build_cliche_watchlist_block([]) == ""

    def test_cliche_watchlist_block_caps_entries_at_twenty(self):
        block = DraftPromptsMixin._build_cliche_watchlist_block([f"cliche {i}" for i in range(25)])

        assert "[절대 사용 금지 — 클리셰 목록]" in block
        assert '  - "cliche 0"' in block
        assert '  - "cliche 19"' in block
        assert '  - "cliche 20"' not in block

    def test_voice_block_includes_brand_voice_fields(self):
        block = DraftPromptsMixin._build_voice_block(
            {
                "brand_voice": {
                    "persona": "editor",
                    "voice_traits": ["plain", "specific"],
                    "forbidden_expressions": ["viral"],
                    "examples": {"good": "good copy", "bad": "bad copy"},
                },
            }
        )

        assert "[보이스 가이드 — 반드시 준수]" in block
        assert "페르소나: editor" in block
        assert "  - plain" in block
        assert "  - specific" in block
        assert "좋은 예: good copy" in block
        assert "나쁜 예: bad copy" in block
        assert "  - viral" in block

    def test_voice_block_includes_cliche_watchlist_without_brand_voice(self):
        block = DraftPromptsMixin._build_voice_block({"cliche_watchlist": ["cliche one", "cliche two"]})

        assert "[보이스 가이드 — 반드시 준수]" not in block
        assert "[절대 사용 금지 — 클리셰 목록]" in block
        assert '  - "cliche one"' in block
        assert '  - "cliche two"' in block

    def test_voice_block_caps_cliche_watchlist_at_twenty(self):
        block = DraftPromptsMixin._build_voice_block({"cliche_watchlist": [f"cliche {i}" for i in range(25)]})

        assert '  - "cliche 19"' in block
        assert '  - "cliche 20"' not in block


class TestImagePromptBlock:
    def test_image_prompt_block_prefers_configured_template(self):
        assert DraftPromptsMixin._build_image_prompt_block({"image_prompt": "configured image prompt"}) == (
            "configured image prompt"
        )

    def test_image_prompt_block_uses_default_when_template_missing(self):
        block = DraftPromptsMixin._build_image_prompt_block({})

        assert block == _DEFAULT_IMAGE_PROMPT_BLOCK
        assert "[이미지 프롬프트 작성 조건]" in block
        assert "반드시 <image_prompt> 와 </image_prompt> 태그 안에만 작성하세요." in block


class TestTwitterBlock:
    def _make_instance(self):
        obj = object.__new__(DraftPromptsMixin)
        obj.max_length = 280
        return obj

    def test_twitter_block_returns_empty_when_not_requested(self):
        obj = self._make_instance()

        assert obj._build_twitter_block({}, ["threads"], "standard", "blind", "공감형", {}) == ""

    def test_twitter_block_ignores_thread_format_and_uses_standard(self):
        """스레드 포맷 폐기(2026-06-18): draft_format='thread' 여도 standard(쥬팍 4단)를 쓴다."""
        obj = self._make_instance()

        block = obj._build_twitter_block(
            {"twitter": {"standard": "standard {max_length} {source} {recommended_draft_type}"}},
            ["twitter"],
            "thread",
            "blind",
            "thread type",
            {},
        )

        assert block == "standard 280 blind thread type"

    def test_twitter_block_uses_standard_template_with_limits(self):
        obj = self._make_instance()

        block = obj._build_twitter_block(
            {"twitter": {"standard": "standard {max_length} {source} {recommended_draft_type}"}},
            ["twitter"],
            "standard",
            "blind",
            "standard type",
            {},
        )

        assert block == "standard 280 blind standard type"

    def test_twitter_block_from_request_uses_request_fields(self):
        obj = self._make_instance()
        request = _OutputBlockRequest(
            templates={"twitter": {"standard": "standard {max_length} {source} {recommended_draft_type}"}},
            rules={},
            output_formats=["twitter"],
            draft_format="standard",
            source="blind",
            recommended_draft_type="standard type",
            profile={},
            topic_cluster="salary",
            empathy_anchor="anchor",
            spinoff_angle="spin",
        )

        block = obj._build_twitter_block_from_request(request)

        assert block == "standard 280 blind standard type"

    def test_twitter_analysis_values_apply_existing_defaults(self):
        assert DraftPromptsMixin._twitter_analysis_values({}) == {
            "audience_need": "",
            "emotion_lane": "",
            "empathy_anchor": "",
            "spinoff_angle": "",
        }

    def test_twitter_analysis_values_keep_present_profile_fields(self):
        assert DraftPromptsMixin._twitter_analysis_values(
            {
                "audience_need": "reader need",
                "emotion_lane": "quiet emotion",
                "empathy_anchor": "anchor point",
                "spinoff_angle": "follow-up angle",
            }
        ) == {
            "audience_need": "reader need",
            "emotion_lane": "quiet emotion",
            "empathy_anchor": "anchor point",
            "spinoff_angle": "follow-up angle",
        }

    def test_twitter_analysis_lines_include_values_in_prompt_order(self):
        assert DraftPromptsMixin._twitter_analysis_lines(
            {
                "audience_need": "reader need",
                "emotion_lane": "quiet emotion",
                "empathy_anchor": "anchor point",
                "spinoff_angle": "follow-up angle",
            }
        ) == [
            "[콘텐츠 분석 데이터]",
            "- 타겟 니즈: reader need",
            "- 감정선: quiet emotion",
            "- 킬링 포인트(Anchor): anchor point",
            "- 확장 가능성(Spinoff): follow-up angle",
        ]

    def test_format_twitter_analysis_block_includes_values(self):
        block = DraftPromptsMixin._format_twitter_analysis_block(
            {
                "audience_need": "reader need",
                "emotion_lane": "quiet emotion",
                "empathy_anchor": "anchor point",
                "spinoff_angle": "follow-up angle",
            }
        )

        assert block == (
            "[콘텐츠 분석 데이터]\n"
            "- 타겟 니즈: reader need\n"
            "- 감정선: quiet emotion\n"
            "- 킬링 포인트(Anchor): anchor point\n"
            "- 확장 가능성(Spinoff): follow-up angle"
        )

    def test_twitter_analysis_block_formats_profile_context(self):
        block = DraftPromptsMixin._build_twitter_analysis_block(
            {
                "audience_need": "reader need",
                "emotion_lane": "quiet emotion",
                "empathy_anchor": "anchor point",
                "spinoff_angle": "follow-up angle",
            }
        )

        assert block == (
            "[콘텐츠 분석 데이터]\n"
            "- 타겟 니즈: reader need\n"
            "- 감정선: quiet emotion\n"
            "- 킬링 포인트(Anchor): anchor point\n"
            "- 확장 가능성(Spinoff): follow-up angle"
        )

    def test_twitter_misc_lines_include_recommended_tone(self):
        assert DraftPromptsMixin._twitter_misc_lines("공감형") == [
            "[기타]",
            "- 본문에 링크나 해시태그는 넣지 마세요 (답글에 넣을 것).",
            "- 1개의 안만 작성하세요. 추천 톤: '공감형'.",
            "- 이모지는 기본 없음. 정말 의미 있을 때만 1개 이하.",
            "- 반드시 <twitter> 와 </twitter> 태그 안에만 작성.",
            "- 답글(원문 링크 포함)은 <reply> 와 </reply> 태그 안에 작성.",
        ]

    def test_format_twitter_misc_block_includes_recommended_tone(self):
        block = DraftPromptsMixin._format_twitter_misc_block("공감형")

        assert "추천 톤: '공감형'" in block
        assert "반드시 <twitter> 와 </twitter> 태그 안에만 작성." in block
        assert "답글(원문 링크 포함)은 <reply> 와 </reply> 태그 안에 작성." in block

    def test_twitter_misc_block_formats_constraints_and_recommended_tone(self):
        block = DraftPromptsMixin._build_twitter_misc_block("공감형")

        assert block == (
            "[기타]\n"
            "- 본문에 링크나 해시태그는 넣지 마세요 (답글에 넣을 것).\n"
            "- 1개의 안만 작성하세요. 추천 톤: '공감형'.\n"
            "- 이모지는 기본 없음. 정말 의미 있을 때만 1개 이하.\n"
            "- 반드시 <twitter> 와 </twitter> 태그 안에만 작성.\n"
            "- 답글(원문 링크 포함)은 <reply> 와 </reply> 태그 안에 작성."
        )

    def test_twitter_fallback_values_collect_block_inputs(self):
        assert DraftPromptsMixin._twitter_fallback_values(
            source="blind",
            profile={"empathy_anchor": "anchor point"},
            max_length=280,
            analysis_block="analysis",
            misc_block="misc",
        ) == {
            "source": "blind",
            "max_length": 280,
            "analysis_block": "analysis",
            "misc_block": "misc",
            "empathy_anchor": "anchor point",
        }

    def test_twitter_fallback_values_default_missing_anchor(self):
        assert DraftPromptsMixin._twitter_fallback_values("blind", {}, 280, "analysis", "misc")["empathy_anchor"] == ""

    def test_twitter_fallback_instruction_lines_include_anchor_limit_and_source(self):
        lines = DraftPromptsMixin._twitter_fallback_instruction_lines(
            {"empathy_anchor": "anchor point", "max_length": 280, "source": "blind"}
        )

        assert lines[0] == "[작성 지침 — 쥬팍식 4단 구조]"
        assert "anchor point" in lines[3]
        assert "280자 이내" in lines[5]
        assert "출처 'blind' 표기는 선택" in lines[5]

    def test_format_twitter_fallback_block_includes_values(self):
        block = DraftPromptsMixin._format_twitter_fallback_block(
            {
                "source": "blind",
                "max_length": 280,
                "analysis_block": "analysis",
                "misc_block": "misc",
                "empathy_anchor": "anchor point",
            }
        )

        assert block.startswith("\n[트위터(X) 본문 — 쥬팍식 4단 구조]")
        assert "\nanalysis\n\n[작성 지침 — 쥬팍식 4단 구조]" in block
        assert "핵심 숫자·고유명사(anchor point)를 그대로 살리세요" in block
        assert "형식: X 가중 280자 이내" in block
        assert "출처 'blind' 표기는 선택" in block
        assert block.endswith("\nmisc\n")

    def test_twitter_block_uses_fallback_with_profile_context(self):
        obj = self._make_instance()

        block = obj._build_twitter_block(
            {},
            ["twitter"],
            "standard",
            "blind",
            "공감형",
            {
                "audience_need": "reader need",
                "emotion_lane": "quiet emotion",
                "empathy_anchor": "anchor point",
                "spinoff_angle": "follow-up angle",
            },
        )

        assert "[트위터(X) 본문 — 쥬팍식 4단 구조]" in block
        assert "- 타겟 니즈: reader need" in block
        assert "- 감정선: quiet emotion" in block
        assert "핵심 숫자·고유명사(anchor point)를 그대로 살리세요" in block
        assert "형식: X 가중 280자 이내" in block
        assert "추천 톤: '공감형'" in block
        assert "반드시 <twitter> 와 </twitter> 태그 안에만 작성." in block

    def test_twitter_fallback_block_uses_profile_context_and_limits(self):
        obj = self._make_instance()

        block = obj._build_twitter_fallback_block(
            "blind",
            "공감형",
            {
                "audience_need": "reader need",
                "emotion_lane": "quiet emotion",
                "empathy_anchor": "anchor point",
                "spinoff_angle": "follow-up angle",
            },
        )

        assert "- 타겟 니즈: reader need" in block
        assert "- 감정선: quiet emotion" in block
        assert "- 확장 가능성(Spinoff): follow-up angle" in block
        assert "핵심 숫자·고유명사(anchor point)를 그대로 살리세요" in block
        assert "형식: X 가중 280자 이내" in block
        assert "출처 'blind' 표기는 선택" in block


class TestNewsletterBlock:
    def test_newsletter_block_returns_empty_when_not_requested(self):
        assert DraftPromptsMixin._build_newsletter_block({}, ["twitter"], "anchor", "spin") == ""

    def test_newsletter_block_prefers_configured_template(self):
        block = DraftPromptsMixin._build_newsletter_block(
            {"newsletter": "configured newsletter"},
            ["newsletter"],
            "anchor",
            "spin",
        )

        assert block == "configured newsletter"

    def test_newsletter_block_from_request_uses_request_fields(self):
        request = _OutputBlockRequest(
            templates={"newsletter": "configured newsletter"},
            rules={},
            output_formats=["newsletter"],
            draft_format="standard",
            source="blind",
            recommended_draft_type="newsletter type",
            profile={},
            topic_cluster="salary",
            empathy_anchor="anchor",
            spinoff_angle="spin",
        )

        block = DraftPromptsMixin._build_newsletter_block_from_request(request)

        assert block == "configured newsletter"

    def test_newsletter_fallback_lines_include_context_and_tag_contract(self):
        lines = DraftPromptsMixin._newsletter_fallback_lines("anchor point", "follow-up angle")

        assert lines[0] == ""
        assert lines[1] == "[뉴스레터 초안 — 심층 큐레이션 및 인사이트]"
        assert "anchor point를 중심으로 한 심층 분석 및 follow-up angle 제언" in lines[6]
        assert lines[-2] == "5. 반드시 <newsletter> 와 </newsletter> 태그 안에만 작성하세요."
        assert lines[-1] == ""

    def test_format_newsletter_fallback_block_includes_context(self):
        block = DraftPromptsMixin._format_newsletter_fallback_block("anchor point", "follow-up angle")

        assert "[뉴스레터 초안 — 심층 큐레이션 및 인사이트]" in block
        assert "에디터의 시선: anchor point를 중심으로 한 심층 분석 및 follow-up angle 제언" in block
        assert "450자 이상 900자 이하" in block
        assert "반드시 <newsletter> 와 </newsletter> 태그 안에만 작성하세요." in block

    def test_newsletter_block_uses_fallback_with_context(self):
        block = DraftPromptsMixin._build_newsletter_block({}, ["newsletter"], "anchor point", "follow-up angle")

        assert "[뉴스레터 초안 — 심층 큐레이션 및 인사이트]" in block
        assert "에디터의 시선: anchor point를 중심으로 한 심층 분석 및 follow-up angle 제언" in block
        assert "450자 이상 900자 이하" in block
        assert "반드시 <newsletter> 와 </newsletter> 태그 안에만 작성하세요." in block


class TestResolvedTopicTone:
    def test_resolved_topic_tone_prefers_topic_then_generic_then_default(self):
        rules = {"tone_mapping_threads": {"salary": "salary tone", "기타": "generic tone"}}

        assert DraftPromptsMixin._resolved_topic_tone(rules, "tone_mapping_threads", "salary", "default") == (
            "salary tone"
        )
        assert DraftPromptsMixin._resolved_topic_tone(rules, "tone_mapping_threads", "unknown", "default") == (
            "generic tone"
        )
        assert DraftPromptsMixin._resolved_topic_tone({}, "tone_mapping_threads", "unknown", "default") == "default"


class TestFormatTemplateOrRaw:
    def test_format_template_or_raw_formats_known_placeholders(self):
        assert DraftPromptsMixin._format_template_or_raw("{tone} {source}", tone="calm", source="blind") == (
            "calm blind"
        )

    def test_format_template_or_raw_preserves_template_when_placeholders_drift(self):
        assert DraftPromptsMixin._format_template_or_raw("{missing}", tone="calm") == "{missing}"
        assert DraftPromptsMixin._format_template_or_raw("{0}", tone="calm") == "{0}"


class TestThreadsBlock:
    def _make_instance(self):
        obj = object.__new__(DraftPromptsMixin)
        obj.threads_tone = "default threads tone"
        obj.threads_max_length = 500
        obj.threads_hashtags_count = 2
        return obj

    def test_resolve_threads_tone_uses_topic_mapping_and_instance_default(self):
        obj = self._make_instance()

        assert obj._resolve_threads_tone({"tone_mapping_threads": {"salary": "salary tone"}}, "salary") == (
            "salary tone"
        )
        assert obj._resolve_threads_tone({}, "unknown") == "default threads tone"

    def test_threads_block_returns_empty_when_not_requested(self):
        obj = self._make_instance()

        assert obj._build_threads_block({}, {}, ["twitter"], "기타", "blind", "공감형", "anchor", "spin") == ""

    def test_threads_block_formats_configured_template_with_topic_tone(self):
        obj = self._make_instance()

        block = obj._build_threads_block(
            {"threads": "{threads_tone} {source} {recommended_draft_type}"},
            {"tone_mapping_threads": {"salary": "salary tone"}},
            ["threads"],
            "salary",
            "blind",
            "story type",
            "anchor",
            "spin",
        )

        assert block == "salary tone blind story type"

    def test_threads_block_from_request_uses_request_fields(self):
        obj = self._make_instance()
        request = _OutputBlockRequest(
            templates={"threads": "{threads_tone} {source} {recommended_draft_type}"},
            rules={"tone_mapping_threads": {"salary": "salary tone"}},
            output_formats=["threads"],
            draft_format="standard",
            source="blind",
            recommended_draft_type="story type",
            profile={},
            topic_cluster="salary",
            empathy_anchor="anchor",
            spinoff_angle="spin",
        )

        block = obj._build_threads_block_from_request(request)

        assert block == "salary tone blind story type"

    def test_threads_block_returns_raw_template_when_format_contract_is_invalid(self):
        obj = self._make_instance()

        block = obj._build_threads_block(
            {"threads": "{missing_key}"},
            {"tone_mapping_threads": {"기타": "fallback tone"}},
            ["threads"],
            "unknown",
            "blind",
            "story type",
            "anchor",
            "spin",
        )

        assert block == "{missing_key}"

    def test_threads_fallback_values_collect_block_inputs(self):
        assert DraftPromptsMixin._threads_fallback_values(
            resolved_threads_tone="warm tone",
            source="blind",
            empathy_anchor="anchor point",
            spinoff_angle="follow-up angle",
            max_length=500,
            hashtags_count=2,
        ) == {
            "resolved_threads_tone": "warm tone",
            "source": "blind",
            "empathy_anchor": "anchor point",
            "spinoff_angle": "follow-up angle",
            "max_length": 500,
            "hashtags_count": 2,
        }

    def test_threads_fallback_lines_include_context_limits_tone_and_tags(self):
        lines = DraftPromptsMixin._threads_fallback_lines(
            {
                "resolved_threads_tone": "warm tone",
                "source": "blind",
                "empathy_anchor": "anchor point",
                "spinoff_angle": "follow-up angle",
                "max_length": 500,
                "hashtags_count": 2,
            }
        )

        assert lines[0] == ""
        assert lines[1] == "[Threads 초안 — 친근한 스토리텔링 및 공감]"
        assert "anchor point를 내 이야기처럼 자연스럽게 풀어서 시작하세요." in lines[4]
        assert "follow-up angle을 활용해 독자의 개인적인 경험을 묻는 질문으로 마무리하세요." in lines[6]
        assert lines[8] == "   - 500자 이내."
        assert lines[9] == "   - 해시태그 2개 이내."
        assert lines[10] == "   - 출처 'blind'를 문맥에 맞게 언급."
        assert lines[11] == "4. 참고 톤: 'warm tone'"
        assert lines[-2] == "5. 반드시 <threads> 와 </threads> 태그 안에만 작성하세요."
        assert lines[-1] == ""

    def test_format_threads_fallback_block_includes_values(self):
        block = DraftPromptsMixin._format_threads_fallback_block(
            {
                "resolved_threads_tone": "warm tone",
                "source": "blind",
                "empathy_anchor": "anchor point",
                "spinoff_angle": "follow-up angle",
                "max_length": 500,
                "hashtags_count": 2,
            }
        )

        assert block.startswith("\n[Threads 초안 — 친근한 스토리텔링 및 공감]")
        assert "anchor point를 내 이야기처럼 자연스럽게 풀어서 시작하세요." in block
        assert "follow-up angle을 활용해 독자의 개인적인 경험을 묻는 질문으로 마무리하세요." in block
        assert "- 500자 이내." in block
        assert "해시태그 2개 이내." in block
        assert "출처 'blind'를 문맥에 맞게 언급." in block
        assert "참고 톤: 'warm tone'" in block

    def test_threads_block_uses_fallback_with_default_tone_and_limits(self):
        obj = self._make_instance()

        block = obj._build_threads_block(
            {},
            {"tone_mapping_threads": {"기타": "fallback tone"}},
            ["threads"],
            "unknown",
            "blind",
            "story type",
            "anchor point",
            "follow-up angle",
        )

        assert "[Threads 초안 — 친근한 스토리텔링 및 공감]" in block
        assert "anchor point를 내 이야기처럼 자연스럽게 풀어서 시작하세요." in block
        assert "follow-up angle을 활용해 독자의 개인적인 경험을 묻는 질문" in block
        assert "500자 이내" in block
        assert "해시태그 2개 이내" in block
        assert "참고 톤: 'fallback tone'" in block
        assert "반드시 <threads> 와 </threads> 태그 안에만 작성하세요." in block

    def test_threads_fallback_block_uses_context_limits_tone_and_source(self):
        obj = self._make_instance()

        block = obj._build_threads_fallback_block(
            "fallback tone",
            "blind",
            "anchor point",
            "follow-up angle",
        )

        assert "[Threads 초안 — 친근한 스토리텔링 및 공감]" in block
        assert "anchor point를 내 이야기처럼 자연스럽게 풀어서 시작하세요." in block
        assert "follow-up angle을 활용해 독자의 개인적인 경험을 묻는 질문" in block
        assert "500자 이내" in block
        assert "해시태그 2개 이내" in block
        assert "출처 'blind'를 문맥에 맞게 언급" in block
        assert "참고 톤: 'fallback tone'" in block


class TestNaverBlogBlock:
    def _make_instance(self):
        obj = object.__new__(DraftPromptsMixin)
        obj.blog_tone = "default blog tone"
        obj.blog_min_length = 450
        obj.blog_max_length = 900
        obj.blog_seo_tags_count = 3
        return obj

    def test_resolve_naver_blog_tone_uses_topic_mapping_and_instance_default(self):
        obj = self._make_instance()

        assert obj._resolve_naver_blog_tone({"tone_mapping_naver_blog": {"salary": "salary blog tone"}}, "salary") == (
            "salary blog tone"
        )
        assert obj._resolve_naver_blog_tone({}, "unknown") == "default blog tone"

    def test_naver_blog_block_returns_empty_when_not_requested(self):
        obj = self._make_instance()

        assert obj._build_naver_blog_block({}, {}, ["twitter"], "기타", "blind", "공감형") == ""

    def test_naver_blog_block_formats_configured_template_with_topic_tone(self):
        obj = self._make_instance()

        block = obj._build_naver_blog_block(
            {"naver_blog": "{naver_blog_tone} {source} {recommended_draft_type}"},
            {"tone_mapping_naver_blog": {"salary": "salary blog tone"}},
            ["naver_blog"],
            "salary",
            "blind",
            "blog type",
        )

        assert block == "salary blog tone blind blog type"

    def test_naver_blog_block_from_request_uses_request_fields(self):
        obj = self._make_instance()
        request = _OutputBlockRequest(
            templates={"naver_blog": "{naver_blog_tone} {source} {recommended_draft_type}"},
            rules={"tone_mapping_naver_blog": {"salary": "salary blog tone"}},
            output_formats=["naver_blog"],
            draft_format="standard",
            source="blind",
            recommended_draft_type="blog type",
            profile={},
            topic_cluster="salary",
            empathy_anchor="anchor",
            spinoff_angle="spin",
        )

        block = obj._build_naver_blog_block_from_request(request)

        assert block == "salary blog tone blind blog type"

    def test_naver_blog_block_returns_raw_template_when_format_contract_is_invalid(self):
        obj = self._make_instance()

        block = obj._build_naver_blog_block(
            {"naver_blog": "{missing_key}"},
            {"tone_mapping_naver_blog": {"기타": "fallback blog tone"}},
            ["naver_blog"],
            "unknown",
            "blind",
            "blog type",
        )

        assert block == "{missing_key}"

    def test_naver_blog_fallback_values_collect_block_inputs(self):
        assert DraftPromptsMixin._naver_blog_fallback_values(
            resolved_blog_tone="warm blog tone",
            source="blind",
            min_length=450,
            max_length=900,
            seo_tags_count=3,
        ) == {
            "resolved_blog_tone": "warm blog tone",
            "source": "blind",
            "min_length": 450,
            "max_length": 900,
            "seo_tags_count": 3,
        }

    def test_naver_blog_fallback_lines_include_limits_tone_source_and_tags(self):
        lines = DraftPromptsMixin._naver_blog_fallback_lines(
            {
                "resolved_blog_tone": "warm blog tone",
                "source": "blind",
                "min_length": 450,
                "max_length": 900,
                "seo_tags_count": 3,
            }
        )

        assert lines[0] == ""
        assert lines[1] == "[네이버 블로그 — 해설형 큐레이션 초안 작성 조건]"
        assert lines[3] == "1. 450자 이상 900자 이하로 작성하세요."
        assert lines[14] == "4. SEO 해시태그를 3개 글 끝에 추가하세요."
        assert lines[15] == "5. 정중하지만 위트 있는 해설자 톤을 유지하세요. 참고 톤: 'warm blog tone'"
        assert lines[17] == "7. 원문 'blind'을 서두 또는 본문에서 간접적으로 언급하세요."
        assert lines[-2] == "8. 반드시 <naver_blog> 와 </naver_blog> 태그 안에만 작성하세요."
        assert lines[-1] == ""

    def test_format_naver_blog_fallback_block_includes_values(self):
        block = DraftPromptsMixin._format_naver_blog_fallback_block(
            {
                "resolved_blog_tone": "warm blog tone",
                "source": "blind",
                "min_length": 450,
                "max_length": 900,
                "seo_tags_count": 3,
            }
        )

        assert block.startswith("\n[네이버 블로그 — 해설형 큐레이션 초안 작성 조건]")
        assert "450자 이상 900자 이하" in block
        assert "SEO 해시태그를 3개 글 끝에 추가하세요." in block
        assert "참고 톤: 'warm blog tone'" in block
        assert "원문 'blind'을 서두 또는 본문에서 간접적으로 언급하세요." in block
        assert "반드시 <naver_blog> 와 </naver_blog> 태그 안에만 작성하세요." in block

    def test_naver_blog_block_uses_fallback_with_limits_and_default_tone(self):
        obj = self._make_instance()

        block = obj._build_naver_blog_block(
            {},
            {"tone_mapping_naver_blog": {"기타": "fallback blog tone"}},
            ["naver_blog"],
            "unknown",
            "blind",
            "blog type",
        )

        assert "[네이버 블로그 — 해설형 큐레이션 초안 작성 조건]" in block
        assert "450자 이상 900자 이하" in block
        assert "SEO 해시태그를 3개 글 끝에 추가하세요." in block
        assert "참고 톤: 'fallback blog tone'" in block
        assert "원문 'blind'을 서두 또는 본문에서 간접적으로 언급하세요." in block
        assert "반드시 <naver_blog> 와 </naver_blog> 태그 안에만 작성하세요." in block

    def test_naver_blog_fallback_block_uses_limits_tone_and_source(self):
        obj = self._make_instance()

        block = obj._build_naver_blog_fallback_block("fallback blog tone", "blind")

        assert "[네이버 블로그 — 해설형 큐레이션 초안 작성 조건]" in block
        assert "450자 이상 900자 이하" in block
        assert "SEO 해시태그를 3개 글 끝에 추가하세요." in block
        assert "참고 톤: 'fallback blog tone'" in block
        assert "원문 'blind'을 서두 또는 본문에서 간접적으로 언급하세요." in block


class TestOutputFormatBlocks:
    def _make_instance(self):
        obj = object.__new__(DraftPromptsMixin)
        obj.max_length = 280
        obj.threads_tone = "default threads tone"
        obj.threads_max_length = 500
        obj.threads_hashtags_count = 2
        obj.blog_tone = "default blog tone"
        obj.blog_min_length = 450
        obj.blog_max_length = 900
        obj.blog_seo_tags_count = 3

        class _RegulationChecker:
            def __init__(self):
                self.platforms = None

            def build_regulation_context(self, platforms):
                self.platforms = platforms
                return "regulation context"

        obj.regulation_checker = _RegulationChecker()
        return obj

    def test_output_block_request_preserves_output_parameters(self):
        templates = {"templates": True}
        rules = {"rules": True}
        profile = {"profile": True}

        request = DraftPromptsMixin._build_output_block_request(
            templates,
            rules,
            ["twitter"],
            "standard",
            "blind",
            "공감형",
            profile,
            "salary",
            "anchor",
            "spin",
        )

        assert request == _OutputBlockRequest(
            templates=templates,
            rules=rules,
            output_formats=["twitter"],
            draft_format="standard",
            source="blind",
            recommended_draft_type="공감형",
            profile=profile,
            topic_cluster="salary",
            empathy_anchor="anchor",
            spinoff_angle="spin",
        )

    def test_shortform_output_blocks_builds_twitter_and_threads_only(self):
        obj = self._make_instance()

        blocks = obj._build_shortform_output_blocks(
            templates={
                "twitter": {"standard": "twitter {max_length} {source} {recommended_draft_type}"},
                "threads": "threads {threads_tone} {source} {recommended_draft_type}",
            },
            rules={"tone_mapping_threads": {"salary": "threads salary tone"}},
            output_formats=["twitter", "threads"],
            draft_format="standard",
            source="blind",
            recommended_draft_type="공감형",
            profile={},
            topic_cluster="salary",
            empathy_anchor="anchor",
            spinoff_angle="spin",
        )

        assert list(blocks) == list(_SHORTFORM_OUTPUT_BLOCK_KEYS)
        assert blocks["twitter"] == "twitter 280 blind 공감형"
        assert blocks["threads"] == "threads threads salary tone blind 공감형"

    def test_shortform_output_block_values_build_twitter_and_threads(self):
        obj = self._make_instance()
        request = _OutputBlockRequest(
            templates={},
            rules={},
            output_formats=["twitter", "threads"],
            draft_format="standard",
            source="blind",
            recommended_draft_type="공감형",
            profile={},
            topic_cluster="salary",
            empathy_anchor="anchor",
            spinoff_angle="spin",
        )

        with (
            patch.object(obj, "_build_twitter_block_from_request", return_value="twitter") as twitter,
            patch.object(obj, "_build_threads_block_from_request", return_value="threads") as threads,
        ):
            blocks = obj._shortform_output_block_values(request)

        assert blocks == {"twitter": "twitter", "threads": "threads"}
        twitter.assert_called_once_with(request)
        threads.assert_called_once_with(request)

    def test_shortform_output_blocks_from_request_builds_twitter_and_threads_only(self):
        obj = self._make_instance()
        request = _OutputBlockRequest(
            templates={
                "twitter": {"standard": "twitter {max_length} {source} {recommended_draft_type}"},
                "threads": "threads {threads_tone} {source} {recommended_draft_type}",
            },
            rules={"tone_mapping_threads": {"salary": "threads salary tone"}},
            output_formats=["twitter", "threads"],
            draft_format="standard",
            source="blind",
            recommended_draft_type="공감형",
            profile={},
            topic_cluster="salary",
            empathy_anchor="anchor",
            spinoff_angle="spin",
        )

        blocks = obj._build_shortform_output_blocks_from_request(request)

        assert list(blocks) == list(_SHORTFORM_OUTPUT_BLOCK_KEYS)
        assert blocks["twitter"] == "twitter 280 blind 공감형"
        assert blocks["threads"] == "threads threads salary tone blind 공감형"

    def test_longform_output_blocks_builds_newsletter_and_naver_blog_only(self):
        obj = self._make_instance()

        blocks = obj._build_longform_output_blocks(
            templates={
                "newsletter": "newsletter configured",
                "naver_blog": "blog {naver_blog_tone} {source} {recommended_draft_type}",
            },
            rules={"tone_mapping_naver_blog": {"salary": "blog salary tone"}},
            output_formats=["newsletter", "naver_blog"],
            source="blind",
            recommended_draft_type="공감형",
            topic_cluster="salary",
            empathy_anchor="anchor",
            spinoff_angle="spin",
        )

        assert list(blocks) == list(_LONGFORM_OUTPUT_BLOCK_KEYS)
        assert blocks["newsletter"] == "newsletter configured"
        assert blocks["naver_blog"] == "blog blog salary tone blind 공감형"

    def test_longform_output_block_values_build_newsletter_and_naver_blog(self):
        obj = self._make_instance()
        request = _OutputBlockRequest(
            templates={},
            rules={},
            output_formats=["newsletter", "naver_blog"],
            draft_format="standard",
            source="blind",
            recommended_draft_type="공감형",
            profile={},
            topic_cluster="salary",
            empathy_anchor="anchor",
            spinoff_angle="spin",
        )

        with (
            patch.object(obj, "_build_newsletter_block_from_request", return_value="newsletter") as newsletter,
            patch.object(obj, "_build_naver_blog_block_from_request", return_value="naver blog") as naver_blog,
        ):
            blocks = obj._longform_output_block_values(request)

        assert blocks == {"newsletter": "newsletter", "naver_blog": "naver blog"}
        newsletter.assert_called_once_with(request)
        naver_blog.assert_called_once_with(request)

    def test_longform_output_blocks_from_request_builds_newsletter_and_naver_blog_only(self):
        obj = self._make_instance()
        request = _OutputBlockRequest(
            templates={
                "newsletter": "newsletter configured",
                "naver_blog": "blog {naver_blog_tone} {source} {recommended_draft_type}",
            },
            rules={"tone_mapping_naver_blog": {"salary": "blog salary tone"}},
            output_formats=["newsletter", "naver_blog"],
            draft_format="standard",
            source="blind",
            recommended_draft_type="공감형",
            profile={},
            topic_cluster="salary",
            empathy_anchor="anchor",
            spinoff_angle="spin",
        )

        blocks = obj._build_longform_output_blocks_from_request(request)

        assert list(blocks) == list(_LONGFORM_OUTPUT_BLOCK_KEYS)
        assert blocks["newsletter"] == "newsletter configured"
        assert blocks["naver_blog"] == "blog blog salary tone blind 공감형"

    def test_merge_platform_output_blocks_preserves_historical_prompt_order(self):
        blocks = DraftPromptsMixin._merge_platform_output_blocks(
            {"twitter": "twitter block", "threads": "threads block"},
            {"newsletter": "newsletter block", "naver_blog": "naver blog block"},
        )

        assert list(blocks) == list(_PLATFORM_OUTPUT_BLOCK_KEYS)
        assert blocks == {
            "twitter": "twitter block",
            "newsletter": "newsletter block",
            "threads": "threads block",
            "naver_blog": "naver blog block",
        }

    def test_platform_output_blocks_from_request_merges_shortform_and_longform_blocks(self):
        obj = self._make_instance()
        request = _OutputBlockRequest(
            templates={},
            rules={},
            output_formats=["twitter"],
            draft_format="standard",
            source="blind",
            recommended_draft_type="공감형",
            profile={},
            topic_cluster="salary",
            empathy_anchor="anchor",
            spinoff_angle="spin",
        )

        with (
            patch.object(
                obj,
                "_build_shortform_output_blocks_from_request",
                return_value={"twitter": "twitter", "threads": "threads"},
            ) as shortform,
            patch.object(
                obj,
                "_build_longform_output_blocks_from_request",
                return_value={"newsletter": "newsletter", "naver_blog": "naver_blog"},
            ) as longform,
        ):
            blocks = obj._build_platform_output_blocks_from_request(request)

        assert blocks == {
            "twitter": "twitter",
            "newsletter": "newsletter",
            "threads": "threads",
            "naver_blog": "naver_blog",
        }
        shortform.assert_called_once_with(request)
        longform.assert_called_once_with(request)

    def test_platform_output_blocks_builds_text_platforms_only(self):
        obj = self._make_instance()

        blocks = obj._build_platform_output_blocks(
            templates={
                "twitter": {"standard": "twitter {max_length} {source} {recommended_draft_type}"},
                "newsletter": "newsletter configured",
                "threads": "threads {threads_tone} {source} {recommended_draft_type}",
                "naver_blog": "blog {naver_blog_tone} {source} {recommended_draft_type}",
                "image_prompt": "image configured",
            },
            rules={
                "tone_mapping_threads": {"salary": "threads salary tone"},
                "tone_mapping_naver_blog": {"salary": "blog salary tone"},
            },
            output_formats=["twitter", "newsletter", "threads", "naver_blog"],
            draft_format="standard",
            source="blind",
            recommended_draft_type="공감형",
            profile={},
            topic_cluster="salary",
            empathy_anchor="anchor",
            spinoff_angle="spin",
        )

        assert list(blocks) == ["twitter", "newsletter", "threads", "naver_blog"]
        assert blocks["twitter"] == "twitter 280 blind 공감형"
        assert blocks["newsletter"] == "newsletter configured"
        assert blocks["threads"] == "threads threads salary tone blind 공감형"
        assert blocks["naver_blog"] == "blog blog salary tone blind 공감형"

    def test_output_format_blocks_from_context_delegates_normalized_context(self):
        obj = self._make_instance()
        templates = {"templates": True}
        rules = {"rules": True}
        profile = {"profile": True}
        context = {
            "source": "blind",
            "recommended_draft_type": "공감형",
            "profile": profile,
            "topic_cluster": "salary",
            "empathy_anchor": "anchor",
            "spinoff_angle": "spin",
        }

        with patch.object(
            obj,
            "_build_output_format_blocks_from_request",
            return_value={"twitter": "block"},
        ) as build_blocks:
            blocks = obj._build_output_format_blocks_from_context(
                templates,
                rules,
                ["twitter"],
                "standard",
                context,
            )

        assert blocks == {"twitter": "block"}
        build_blocks.assert_called_once_with(
            _OutputBlockRequest(
                templates=templates,
                rules=rules,
                output_formats=["twitter"],
                draft_format="standard",
                source="blind",
                recommended_draft_type="공감형",
                profile=profile,
                topic_cluster="salary",
                empathy_anchor="anchor",
                spinoff_angle="spin",
            )
        )

    def test_output_request_context_values_map_normalized_context(self):
        profile = {"profile": True}

        assert DraftPromptsMixin._output_request_context_values(
            {
                "source": "blind",
                "recommended_draft_type": "공감형",
                "profile": profile,
                "topic_cluster": "salary",
                "empathy_anchor": "anchor",
                "spinoff_angle": "spin",
            }
        ) == {
            "source": "blind",
            "recommended_draft_type": "공감형",
            "profile": profile,
            "topic_cluster": "salary",
            "empathy_anchor": "anchor",
            "spinoff_angle": "spin",
        }

    def test_output_block_request_from_context_maps_normalized_context(self):
        obj = self._make_instance()
        templates = {"templates": True}
        rules = {"rules": True}
        profile = {"profile": True}

        request = obj._build_output_block_request_from_context(
            templates,
            rules,
            ["twitter"],
            "standard",
            {
                "source": "blind",
                "recommended_draft_type": "공감형",
                "profile": profile,
                "topic_cluster": "salary",
                "empathy_anchor": "anchor",
                "spinoff_angle": "spin",
            },
        )

        assert request == _OutputBlockRequest(
            templates=templates,
            rules=rules,
            output_formats=["twitter"],
            draft_format="standard",
            source="blind",
            recommended_draft_type="공감형",
            profile=profile,
            topic_cluster="salary",
            empathy_anchor="anchor",
            spinoff_angle="spin",
        )

    def test_auxiliary_output_blocks_append_image_and_regulation_blocks(self):
        obj = self._make_instance()

        blocks = obj._build_auxiliary_output_blocks(
            {"image_prompt": "image configured"},
            {"regulation_context": "regulation context", "regulation_check": "regulation check"},
        )

        assert list(blocks) == list(_AUXILIARY_OUTPUT_BLOCK_KEYS)
        assert blocks == {
            "image": "image configured",
            "regulation_context": "regulation context",
            "regulation_check": "regulation check",
        }

    def test_auxiliary_output_block_values_build_image_and_regulation_values(self):
        obj = self._make_instance()
        templates = {"image_prompt": "image configured"}
        regulation_blocks = {"regulation_context": "regulation context", "regulation_check": "regulation check"}

        with patch.object(obj, "_build_image_prompt_block", return_value="image") as image:
            blocks = obj._auxiliary_output_block_values(templates, regulation_blocks)

        assert blocks == {
            "image": "image",
            "regulation_context": "regulation context",
            "regulation_check": "regulation check",
        }
        image.assert_called_once_with(templates)

    def test_merge_output_format_blocks_combines_platform_and_auxiliary_blocks(self):
        assert DraftPromptsMixin._merge_output_format_blocks(
            {"twitter": "twitter", "newsletter": "newsletter"},
            {"image": "image", "regulation_check": "check"},
        ) == {
            "twitter": "twitter",
            "newsletter": "newsletter",
            "image": "image",
            "regulation_check": "check",
        }

    def test_output_format_blocks_from_request_combines_platform_and_auxiliary_blocks(self):
        obj = self._make_instance()
        request = _OutputBlockRequest(
            templates={"image_prompt": "image"},
            rules={},
            output_formats=["twitter"],
            draft_format="standard",
            source="blind",
            recommended_draft_type="공감형",
            profile={},
            topic_cluster="salary",
            empathy_anchor="anchor",
            spinoff_angle="spin",
        )

        with (
            patch.object(obj, "_build_platform_output_blocks_from_request", return_value={"twitter": "twitter"}),
            patch.object(
                obj,
                "_build_regulation_output_blocks",
                return_value={"regulation_context": "context", "regulation_check": "check"},
            ) as regulation,
            patch.object(obj, "_build_auxiliary_output_blocks", return_value={"image": "image", "reg": "reg"}) as aux,
        ):
            blocks = obj._build_output_format_blocks_from_request(request)

        assert blocks == {"twitter": "twitter", "image": "image", "reg": "reg"}
        regulation.assert_called_once_with(["twitter"])
        aux.assert_called_once_with(
            {"image_prompt": "image"}, {"regulation_context": "context", "regulation_check": "check"}
        )

    def test_output_format_block_groups_build_platform_and_auxiliary_groups(self):
        obj = self._make_instance()
        request = _OutputBlockRequest(
            templates={"image_prompt": "image"},
            rules={},
            output_formats=["twitter"],
            draft_format="standard",
            source="blind",
            recommended_draft_type="공감형",
            profile={},
            topic_cluster="salary",
            empathy_anchor="anchor",
            spinoff_angle="spin",
        )

        with (
            patch.object(
                obj,
                "_build_platform_output_blocks_from_request",
                return_value={"twitter": "twitter"},
            ) as platform,
            patch.object(
                obj,
                "_build_regulation_output_blocks",
                return_value={"regulation_context": "context", "regulation_check": "check"},
            ) as regulation,
            patch.object(obj, "_build_auxiliary_output_blocks", return_value={"image": "image", "reg": "reg"}) as aux,
        ):
            groups = obj._output_format_block_groups(request)

        assert groups == _OutputFormatBlockGroups(
            platform_blocks={"twitter": "twitter"},
            auxiliary_blocks={"image": "image", "reg": "reg"},
        )
        platform.assert_called_once_with(request)
        regulation.assert_called_once_with(["twitter"])
        aux.assert_called_once_with(
            {"image_prompt": "image"}, {"regulation_context": "context", "regulation_check": "check"}
        )

    def test_output_format_blocks_builds_requested_platforms_and_regulation_pair(self):
        obj = self._make_instance()

        blocks = obj._build_output_format_blocks(
            templates={
                "twitter": {"standard": "twitter {max_length} {source} {recommended_draft_type}"},
                "newsletter": "newsletter configured",
                "threads": "threads {threads_tone} {source} {recommended_draft_type}",
                "naver_blog": "blog {naver_blog_tone} {source} {recommended_draft_type}",
                "image_prompt": "image configured",
            },
            rules={
                "tone_mapping_threads": {"salary": "threads salary tone"},
                "tone_mapping_naver_blog": {"salary": "blog salary tone"},
            },
            output_formats=["twitter", "newsletter", "threads", "naver_blog"],
            draft_format="standard",
            source="blind",
            recommended_draft_type="공감형",
            profile={},
            topic_cluster="salary",
            empathy_anchor="anchor",
            spinoff_angle="spin",
        )

        assert blocks["twitter"] == "twitter 280 blind 공감형"
        assert blocks["newsletter"] == "newsletter configured"
        assert blocks["threads"] == "threads threads salary tone blind 공감형"
        assert blocks["naver_blog"] == "blog blog salary tone blind 공감형"
        assert blocks["image"] == "image configured"
        assert blocks["regulation_context"] == "regulation context"
        assert "[자체 규제 검증 리포트 작성 조건]" in blocks["regulation_check"]
        assert obj.regulation_checker.platforms == ["twitter", "threads", "naver_blog"]

    def test_output_format_blocks_keeps_unrequested_platform_blocks_empty(self):
        obj = self._make_instance()

        blocks = obj._build_output_format_blocks(
            templates={"image_prompt": "image configured"},
            rules={},
            output_formats=["newsletter"],
            draft_format="standard",
            source="blind",
            recommended_draft_type="공감형",
            profile={},
            topic_cluster="기타",
            empathy_anchor="anchor",
            spinoff_angle="spin",
        )

        assert blocks["twitter"] == ""
        assert blocks["threads"] == ""
        assert blocks["naver_blog"] == ""
        assert blocks["newsletter"] != ""
        assert blocks["image"] == "image configured"


class TestRegulationCheckBlock:
    def test_regulation_check_lines_include_report_contract(self):
        lines = DraftPromptsMixin._regulation_check_lines()

        assert lines[0] == ""
        assert lines[1] == "[자체 규제 검증 리포트 작성 조건]"
        assert "반드시 <regulation_check> 와 </regulation_check> 태그 안에만 작성하세요." in lines[3]
        assert "✅ X | 글자 수 | 267자 (280자 이내 준수)" in lines[7]
        assert lines[-1] == ""

    def test_regulation_check_block_requires_context(self):
        assert DraftPromptsMixin._build_regulation_check_block("") == ""

    def test_regulation_check_block_includes_report_contract(self):
        block = DraftPromptsMixin._build_regulation_check_block("regulation context")

        assert "[자체 규제 검증 리포트 작성 조건]" in block
        assert "반드시 <regulation_check> 와 </regulation_check> 태그 안에만 작성하세요." in block
        assert "✅ X | 글자 수 | 267자 (280자 이내 준수)" in block


class TestRegulationContext:
    def test_regulation_context_filters_supported_platforms(self):
        obj = object.__new__(DraftPromptsMixin)

        class _RegulationChecker:
            def __init__(self):
                self.platforms = None

            def build_regulation_context(self, platforms):
                self.platforms = platforms
                return "regulation context"

        checker = _RegulationChecker()
        obj.regulation_checker = checker

        assert _REGULATION_SUPPORTED_OUTPUT_FORMATS == ("twitter", "threads", "naver_blog")
        assert obj._build_regulation_context(["twitter", "newsletter", "threads", "naver_blog"]) == (
            "regulation context"
        )
        assert checker.platforms == ["twitter", "threads", "naver_blog"]

    def test_regulation_context_returns_empty_when_checker_fails(self):
        obj = object.__new__(DraftPromptsMixin)

        class _RegulationChecker:
            def build_regulation_context(self, platforms):
                raise RuntimeError("boom")

        obj.regulation_checker = _RegulationChecker()

        assert obj._build_regulation_context(["twitter"]) == ""


class TestRegulationOutputBlocks:
    def test_regulation_output_block_values_pair_context_with_check_block(self):
        obj = object.__new__(DraftPromptsMixin)

        with (
            patch.object(obj, "_build_regulation_context", return_value="regulation context") as context,
            patch.object(obj, "_build_regulation_check_block", return_value="regulation check") as check,
        ):
            blocks = obj._regulation_output_block_values(["twitter"])

        assert blocks == {"regulation_context": "regulation context", "regulation_check": "regulation check"}
        context.assert_called_once_with(["twitter"])
        check.assert_called_once_with("regulation context")

    def test_regulation_output_blocks_pair_context_with_check_block(self):
        obj = object.__new__(DraftPromptsMixin)

        class _RegulationChecker:
            def __init__(self):
                self.platforms = None

            def build_regulation_context(self, platforms):
                self.platforms = platforms
                return "regulation context"

        checker = _RegulationChecker()
        obj.regulation_checker = checker

        blocks = obj._build_regulation_output_blocks(["twitter", "newsletter", "threads"])

        assert list(blocks) == list(_REGULATION_OUTPUT_BLOCK_KEYS)
        assert blocks["regulation_context"] == "regulation context"
        assert "[자체 규제 검증 리포트 작성 조건]" in blocks["regulation_check"]
        assert checker.platforms == ["twitter", "threads"]

    def test_regulation_output_blocks_keep_check_empty_without_context(self):
        obj = object.__new__(DraftPromptsMixin)

        class _RegulationChecker:
            def build_regulation_context(self, platforms):
                return ""

        obj.regulation_checker = _RegulationChecker()

        blocks = obj._build_regulation_output_blocks(["twitter"])

        assert list(blocks) == list(_REGULATION_OUTPUT_BLOCK_KEYS)
        assert blocks == {
            "regulation_context": "",
            "regulation_check": "",
        }


class TestBuildPromptComposition:
    def test_prompt_preparation_values_combine_context_and_loaded_config(self):
        obj = object.__new__(DraftPromptsMixin)
        post_data = {"title": "title"}

        with (
            patch.object(obj, "_build_prompt_context", return_value={"content": "content text"}) as build_context,
            patch.object(
                obj,
                "_load_prompt_template_config",
                return_value=({"rules": True}, {"templates": True}, "system role"),
            ) as load_config,
        ):
            values = obj._prompt_preparation_values(post_data)

        assert values == {
            "context": {"content": "content text"},
            "rules": {"rules": True},
            "templates": {"templates": True},
            "system_role": "system role",
        }
        build_context.assert_called_once_with(post_data)
        load_config.assert_called_once_with()

    def test_prompt_preparation_combines_context_and_loaded_config(self):
        obj = object.__new__(DraftPromptsMixin)
        post_data = {"title": "title"}

        with (
            patch.object(obj, "_build_prompt_context", return_value={"content": "content text"}) as build_context,
            patch.object(
                obj,
                "_load_prompt_template_config",
                return_value=({"rules": True}, {"templates": True}, "system role"),
            ) as load_config,
        ):
            preparation = obj._build_prompt_preparation(post_data)

        assert preparation == _PromptPreparation(
            context={"content": "content text"},
            rules={"rules": True},
            templates={"templates": True},
            system_role="system role",
        )
        build_context.assert_called_once_with(post_data)
        load_config.assert_called_once_with()

    def test_prompt_component_request_from_preparation_delegates_prepared_values(self):
        obj = object.__new__(DraftPromptsMixin)
        post_data = {"title": "title"}
        preparation = _PromptPreparation(
            context={"content": "content text"},
            rules={"rules": True},
            templates={"templates": True},
            system_role="system role",
        )

        with patch.object(
            obj,
            "_build_prompt_component_request_from_config",
            return_value="component request",
        ) as request_factory:
            request = obj._prompt_component_request_from_preparation(
                post_data=post_data,
                top_examples=[],
                output_formats=["twitter"],
                draft_format="standard",
                preparation=preparation,
            )

        assert request == "component request"
        request_factory.assert_called_once_with(
            post_data=post_data,
            top_examples=[],
            output_formats=["twitter"],
            draft_format="standard",
            context={"content": "content text"},
            rules={"rules": True},
            templates={"templates": True},
        )

    def test_prompt_component_blocks_from_config_builds_request_then_blocks(self):
        obj = object.__new__(DraftPromptsMixin)
        post_data = {"title": "title"}
        preparation = _PromptPreparation(
            context={"content": "content text"},
            rules={"rules": True},
            templates={"templates": True},
            system_role="system role",
        )
        component_request = _PromptComponentRequest(
            post_data=post_data,
            top_examples=[],
            output_formats=["twitter"],
            draft_format="standard",
            context={"content": "content text"},
            rules={"rules": True},
            templates={"templates": True},
        )

        with (
            patch.object(
                obj,
                "_build_prompt_component_request_from_config",
                return_value=component_request,
            ) as request_factory,
            patch.object(
                obj,
                "_build_prompt_component_blocks_from_request",
                return_value={"output": {"twitter": "twitter block"}},
            ) as blocks_factory,
        ):
            blocks = obj._build_prompt_component_blocks_from_config(
                post_data=post_data,
                top_examples=[],
                output_formats=["twitter"],
                draft_format="standard",
                preparation=preparation,
            )

        assert blocks == {"output": {"twitter": "twitter block"}}
        request_factory.assert_called_once_with(
            post_data=post_data,
            top_examples=[],
            output_formats=["twitter"],
            draft_format="standard",
            context={"content": "content text"},
            rules={"rules": True},
            templates={"templates": True},
        )
        blocks_factory.assert_called_once_with(component_request)

    def test_prompt_component_request_from_config_delegates_to_context_factory(self):
        obj = object.__new__(DraftPromptsMixin)
        post_data = {"title": "title"}
        top_examples = [{"text": "example"}]
        context = {"content": "content text"}

        with patch.object(
            obj,
            "_build_prompt_component_request_from_context",
            return_value="component request",
        ) as request_factory:
            request = obj._build_prompt_component_request_from_config(
                post_data=post_data,
                top_examples=top_examples,
                output_formats=["twitter"],
                draft_format="standard",
                context=context,
                rules={"rules": True},
                templates={"templates": True},
            )

        assert request == "component request"
        request_factory.assert_called_once_with(
            post_data=post_data,
            top_examples=top_examples,
            output_formats=["twitter"],
            draft_format="standard",
            context=context,
            rules={"rules": True},
            templates={"templates": True},
        )

    def test_prompt_result_from_preparation_routes_component_blocks_into_result_request(self):
        obj = object.__new__(DraftPromptsMixin)
        post_data = {"title": "title"}
        context = {"content": "content text"}
        preparation = _PromptPreparation(
            context=context,
            rules={"rules": True},
            templates={"templates": True},
            system_role="system role",
        )
        component_blocks = {
            "guidance": {"voice": "voice block"},
            "output": {"twitter": "twitter block"},
            "reference": {"reviewer_memory": "memory block"},
        }

        with (
            patch.object(
                obj,
                "_build_prompt_component_blocks_from_config",
                return_value=component_blocks,
            ) as component_blocks_builder,
            patch.object(
                obj, "_build_anthropic_prompt_result_from_components", return_value="prompt"
            ) as result_builder,
        ):
            prompt = obj._build_prompt_result_from_preparation(
                post_data=post_data,
                top_examples=[],
                output_formats=["twitter"],
                draft_format="standard",
                preparation=preparation,
            )

        assert prompt == "prompt"
        component_blocks_builder.assert_called_once_with(
            post_data=post_data,
            top_examples=[],
            output_formats=["twitter"],
            draft_format="standard",
            preparation=preparation,
        )
        result_builder.assert_called_once_with(
            post_data=post_data,
            context=context,
            system_role="system role",
            component_blocks=component_blocks,
        )

    def test_build_prompt_delegates_preparation_to_prompt_result_builder(self):
        obj = object.__new__(DraftPromptsMixin)
        post_data = {"title": "title"}
        preparation = _PromptPreparation(
            context={"content": "content text"},
            rules={"rules": True},
            templates={"templates": True},
            system_role="system role",
        )

        with (
            patch.object(obj, "_build_prompt_preparation", return_value=preparation) as prepare_prompt,
            patch.object(obj, "_build_prompt_result_from_preparation", return_value="prompt") as result_builder,
        ):
            prompt = obj._build_prompt(post_data, top_examples=[], output_formats=["twitter"])

        assert prompt == "prompt"
        prepare_prompt.assert_called_once_with(post_data)
        result_builder.assert_called_once_with(
            post_data=post_data,
            top_examples=[],
            output_formats=["twitter"],
            draft_format="standard",
            preparation=preparation,
        )


class TestBuildPromptResearchContext:
    def _make_instance(self):
        obj = object.__new__(DraftPromptsMixin)
        obj.tone = "담담한 직장인 톤"
        obj.max_length = 280
        obj.threads_tone = "친근한 톤"
        obj.threads_max_length = 500
        obj.threads_hashtags_count = 2
        obj.blog_tone = "전문 에디터 톤"
        obj.blog_min_length = 450
        obj.blog_max_length = 900
        obj.blog_seo_tags_count = 3

        class _RegulationChecker:
            def build_regulation_context(self, platforms):
                return ""

        obj.regulation_checker = _RegulationChecker()
        return obj

    @patch(
        "pipeline.draft_prompts._load_draft_rules",
        return_value={"prompt_templates": {}, "tone_mapping": {}, "emotion_rules": []},
    )
    def test_research_context_is_injected_into_user_prompt(self, mock_rules):
        obj = self._make_instance()
        prompt = obj._build_prompt(
            {
                "source": "blind",
                "title": "상사가 야근을 당연하게 여긴다는 글",
                "content": "팀장이 매일 퇴근 직전에 일을 줍니다.",
                "research_context": {
                    "source_frame": "개인이 편하게 일하고 싶다는 문제",
                    "real_issue": "일의 책임과 개인 시간의 경계를 어디에 둘 것인가",
                    "universal_value": "경계 존중",
                    "killer_sentence": "이건 편하게 일하자는 게 아니라 일과 삶의 경계를 지키자는 말입니다",
                    "closure": "open",
                    "conflict_risk": 0.91,
                    "anchor": "팀장이 매일 퇴근 직전에 일을 줍니다.",
                },
            },
            top_examples=[],
            output_formats=["twitter"],
        )

        assert "[오토리서치 컨텍스트 - 반드시 반영]" in prompt.anthropic_user_prompt
        assert "핵심 사실: 경계 존중" in prompt.anthropic_user_prompt
        assert "갈등 위험 높음" in prompt.anthropic_user_prompt
        assert "위 킬러 문장의 핵심 사실" in prompt.anthropic_user_prompt


# ── _select_examples_deterministically ───────────────────────────────────────


class TestFormatExampleReferenceLines:
    def test_example_reference_values_apply_defaults_grade_and_strip_text(self):
        assert DraftPromptsMixin._example_reference_values(2, {"grade": "A", "text": "  body text  "}) == {
            "index": 2,
            "grade": " [등급: A]",
            "views": 0,
            "topic_cluster": "기타",
            "hook_type": "공감형",
            "emotion_axis": "공감",
            "draft_style": "공감형",
            "text": "body text",
        }

    def test_example_reference_lines_include_grade_and_strip_text(self):
        lines = DraftPromptsMixin._format_example_reference_lines(
            2,
            {
                "grade": "A",
                "views": 123,
                "topic_cluster": "salary",
                "hook_type": "number hook",
                "emotion_axis": "relief",
                "draft_style": "공감형",
                "text": "  body text  ",
            },
        )

        assert lines == [
            "- 예시 2 [등급: A]",
            "  조회수: 123",
            "  토픽: salary",
            "  훅: number hook",
            "  감정: relief",
            "  추천 초안 타입: 공감형",
            "  본문: body text",
        ]

    def test_example_reference_lines_use_existing_defaults(self):
        lines = DraftPromptsMixin._format_example_reference_lines(1, {})

        assert lines == [
            "- 예시 1",
            "  조회수: 0",
            "  토픽: 기타",
            "  훅: 공감형",
            "  감정: 공감",
            "  추천 초안 타입: 공감형",
            "  본문: ",
        ]


class TestGoldenReferenceExamples:
    def test_golden_reference_example_maps_to_shared_reference_shape(self):
        assert DraftPromptsMixin._golden_reference_example(
            "salary",
            {"hook_type": "number hook", "text": "body", "grade": "A"},
        ) == {
            "views": "(골든 예시)",
            "topic_cluster": "salary",
            "hook_type": "number hook",
            "emotion_axis": "-",
            "draft_style": "number hook",
            "text": "body",
            "grade": "A",
        }

    def test_golden_reference_example_applies_existing_defaults(self):
        assert DraftPromptsMixin._golden_reference_example("salary", {}) == {
            "views": "(골든 예시)",
            "topic_cluster": "salary",
            "hook_type": "공감형",
            "emotion_axis": "-",
            "draft_style": "공감형",
            "text": "",
            "grade": "",
        }

    def test_golden_reference_examples_returns_empty_without_matching_topic(self):
        assert DraftPromptsMixin._golden_reference_examples({"golden_examples": {}}, "salary", "seed") == []
        assert DraftPromptsMixin._golden_reference_examples({"golden_examples": {"salary": []}}, "", "seed") == []

    def test_golden_reference_examples_maps_selected_examples(self):
        result = DraftPromptsMixin._golden_reference_examples(
            {
                "golden_examples": {
                    "salary": [
                        {"hook_type": "number hook", "text": "first", "grade": "A"},
                        {"text": "second"},
                    ],
                },
            },
            "salary",
            "seed",
        )

        assert result == [
            {
                "views": "(골든 예시)",
                "topic_cluster": "salary",
                "hook_type": "number hook",
                "emotion_axis": "-",
                "draft_style": "number hook",
                "text": "first",
                "grade": "A",
            },
            {
                "views": "(골든 예시)",
                "topic_cluster": "salary",
                "hook_type": "공감형",
                "emotion_axis": "-",
                "draft_style": "공감형",
                "text": "second",
                "grade": "",
            },
        ]


class TestCostDbReferenceExamples:
    def test_cost_db_reference_example_maps_row_to_shared_reference_shape(self):
        assert DraftPromptsMixin._cost_db_reference_example(
            {
                "yt_views": 123,
                "topic_cluster": "salary",
                "hook_type": "number hook",
                "emotion_axis": "relief",
                "draft_style": "공감형",
                "text": "body text",
            }
        ) == {
            "views": 123,
            "topic_cluster": "salary",
            "hook_type": "number hook",
            "emotion_axis": "relief",
            "draft_style": "공감형",
            "text": "body text",
            "grade": "실적우수",
        }

    def test_cost_db_reference_example_applies_existing_defaults(self):
        assert DraftPromptsMixin._cost_db_reference_example({}) == {
            "views": 0,
            "topic_cluster": "",
            "hook_type": "",
            "emotion_axis": "",
            "draft_style": "",
            "text": "",
            "grade": "실적우수",
        }

    def test_cost_db_reference_examples_maps_top_drafts(self):
        class _Db:
            def __init__(self):
                self.calls = []

            def get_top_performing_drafts(self, **kwargs):
                self.calls.append(kwargs)
                return [
                    {
                        "yt_views": 123,
                        "topic_cluster": "salary",
                        "hook_type": "number hook",
                        "emotion_axis": "relief",
                        "draft_style": "공감형",
                        "text": "body text",
                    },
                    {},
                ]

        db = _Db()

        with patch("pipeline.cost_db.get_cost_db", return_value=db):
            result = DraftPromptsMixin._cost_db_reference_examples("salary")

        assert db.calls == [{"topic_cluster": "salary", "limit": 2}]
        assert result == [
            {
                "views": 123,
                "topic_cluster": "salary",
                "hook_type": "number hook",
                "emotion_axis": "relief",
                "draft_style": "공감형",
                "text": "body text",
                "grade": "실적우수",
            },
            {
                "views": 0,
                "topic_cluster": "",
                "hook_type": "",
                "emotion_axis": "",
                "draft_style": "",
                "text": "",
                "grade": "실적우수",
            },
        ]

    def test_cost_db_reference_examples_returns_empty_when_db_fails(self):
        with patch("pipeline.cost_db.get_cost_db", side_effect=RuntimeError("missing db")):
            assert DraftPromptsMixin._cost_db_reference_examples("salary") == []


class TestMergedReferenceExamples:
    def test_runtime_reference_examples_skip_reviewer_memory(self):
        runtime = {"text": "runtime"}
        memory = {"text": "memory", "example_source": "reviewer_memory"}

        assert DraftPromptsMixin._runtime_reference_examples([runtime, memory]) == [runtime]
        assert DraftPromptsMixin._runtime_reference_examples(None) == []

    def test_reviewer_memory_examples_keep_only_reviewer_memory(self):
        runtime = {"text": "runtime"}
        memory = {"text": "memory", "example_source": "reviewer_memory"}

        assert DraftPromptsMixin._reviewer_memory_examples([runtime, memory]) == [memory]
        assert DraftPromptsMixin._reviewer_memory_examples(None) == []

    def test_reviewer_memory_line_values_apply_defaults_and_strip_text(self):
        assert DraftPromptsMixin._reviewer_memory_line_values(
            {"memory_label": "  label  ", "text": "  warning  ", "reason": "  repeated  "}
        ) == {
            "label": "label",
            "text": "warning",
            "reason": "repeated",
        }
        assert DraftPromptsMixin._reviewer_memory_line_values({}) == {
            "label": "운영 메모",
            "text": "",
            "reason": "",
        }

    def test_format_reviewer_memory_item_lines_formats_reason_when_present(self):
        assert DraftPromptsMixin._format_reviewer_memory_item_lines(
            {"memory_label": "label", "text": "warning", "reason": "repeated"}
        ) == ["- label: warning", "  이유: repeated"]

    def test_format_reviewer_memory_item_lines_omits_blank_reason_and_text(self):
        assert DraftPromptsMixin._format_reviewer_memory_item_lines({"text": "warning"}) == ["- 운영 메모: warning"]
        assert DraftPromptsMixin._format_reviewer_memory_item_lines({"reason": "no text"}) == []

    @patch("pipeline.draft_prompts._load_draft_rules", return_value={"rules": True})
    def test_merged_reference_examples_combines_sources_and_skips_reviewer_memory(self, mock_rules):
        top_examples = [
            {"text": "runtime"},
            {"text": "memory", "example_source": "reviewer_memory"},
        ]

        with (
            patch.object(
                DraftPromptsMixin,
                "_golden_reference_examples",
                return_value=[{"text": "golden"}],
            ) as golden,
            patch.object(
                DraftPromptsMixin,
                "_cost_db_reference_examples",
                return_value=[{"text": "cost"}],
            ) as cost_db,
        ):
            merged = DraftPromptsMixin._merged_reference_examples(top_examples, "salary", "seed")

        assert merged == [{"text": "golden"}, {"text": "cost"}, {"text": "runtime"}]
        golden.assert_called_once_with({"rules": True}, "salary", "salary|seed")
        cost_db.assert_called_once_with("salary")


class TestSelectExamplesDeterministically:
    def test_example_selection_sort_key_uses_seed_hash_and_stripped_text(self):
        key = DraftPromptsMixin._example_selection_sort_key("seed", {"text": "  example  "})

        assert len(key[0]) == 64
        assert key[1] == "example"
        assert key == DraftPromptsMixin._example_selection_sort_key("seed", {"text": "example"})
        assert key != DraftPromptsMixin._example_selection_sort_key("other", {"text": "example"})

    def test_example_selection_offset_is_deterministic_and_within_count(self):
        offset = DraftPromptsMixin._example_selection_offset("seed", 5)

        assert 0 <= offset < 5
        assert offset == DraftPromptsMixin._example_selection_offset("seed", 5)
        assert DraftPromptsMixin._example_selection_offset("seed", 1) == 0

    def test_deterministic_same_seed(self):
        examples = [{"text": f"example {i}"} for i in range(10)]
        r1 = DraftPromptsMixin._select_examples_deterministically(examples, 3, "seed_a")
        r2 = DraftPromptsMixin._select_examples_deterministically(examples, 3, "seed_a")
        assert r1 == r2

    def test_different_seed_different_result(self):
        examples = [{"text": f"example {i}"} for i in range(10)]
        r1 = DraftPromptsMixin._select_examples_deterministically(examples, 3, "seed_a")
        r2 = DraftPromptsMixin._select_examples_deterministically(examples, 3, "seed_b")
        # Different seeds should (almost certainly) produce different orderings
        assert r1 != r2

    def test_limit_exceeds_list(self):
        examples = [{"text": "a"}, {"text": "b"}]
        result = DraftPromptsMixin._select_examples_deterministically(examples, 5, "seed")
        assert len(result) == 2

    def test_empty_list(self):
        result = DraftPromptsMixin._select_examples_deterministically([], 3, "seed")
        assert result == []

    def test_limit_zero(self):
        examples = [{"text": "a"}]
        result = DraftPromptsMixin._select_examples_deterministically(examples, 0, "seed")
        # limit=0 → len(examples)=1 > 0 is True, so sorting happens then [:0]
        assert len(result) == 0


# ── _build_retry_prompt ──────────────────────────────────────────────────────


class TestBuildRetryPrompt:
    def _make_instance(self):
        """Create a minimal object with the mixin."""
        obj = object.__new__(DraftPromptsMixin)
        return obj

    def test_fix_instruction_for_issue_matches_known_issue_keywords(self):
        obj = self._make_instance()

        assert "펀치라인" in obj._fix_instruction_for_issue("CTA 위반")
        assert "글이 너무 짧습니다" in obj._fix_instruction_for_issue("최소 글자 수 미달")

    def test_fix_instruction_for_issue_returns_empty_for_unknown_issue(self):
        obj = self._make_instance()

        assert obj._fix_instruction_for_issue("unknown issue") == ""

    def test_retry_feedback_issue_lines_include_issue_and_known_fix(self):
        obj = self._make_instance()

        lines = obj._retry_feedback_issue_lines("CTA 위반")

        assert lines[0] == "  - CTA 위반"
        assert any("수정 방법" in line and "펀치라인" in line for line in lines)
        assert obj._retry_feedback_issue_lines("unknown issue") == ["  - unknown issue"]

    def test_retry_feedback_group_lines_include_platform_score_and_issues(self):
        obj = self._make_instance()

        lines = obj._retry_feedback_group_lines(
            {"platform": "twitter", "score": 40, "issues": ["CTA 위반", "unknown issue"]}
        )

        assert lines[0] == "\n❌ twitter (점수: 40/100):"
        assert "  - CTA 위반" in lines
        assert any("수정 방법" in line and "펀치라인" in line for line in lines)
        assert "  - unknown issue" in lines

    def test_retry_feedback_lines_include_platform_score_issues_and_known_fix(self):
        obj = self._make_instance()

        lines = obj._retry_feedback_lines(
            [{"platform": "twitter", "score": 40, "issues": ["CTA 위반", "unknown issue"]}]
        )

        assert lines[0] == ""
        assert "[이전 초안 품질 게이트 실패" in lines[2]
        assert "\n❌ twitter (점수: 40/100):" in lines
        assert "  - CTA 위반" in lines
        assert any("수정 방법" in line and "펀치라인" in line for line in lines)
        assert "  - unknown issue" in lines

    def test_retry_rewrite_instruction_lines_include_fixed_contract(self):
        lines = DraftPromptsMixin._retry_rewrite_instruction_lines()

        assert lines[0] == ""
        assert lines[1] == "[재작성 지침]"
        assert "반드시 반영하세요" in lines[2]
        assert "날조하지 마세요" in lines[-2]
        assert lines[-1] == "━" * 40

    def test_retry_prompt_feedback_lines_combine_feedback_and_rewrite_guidance(self):
        obj = self._make_instance()
        quality_feedback = [{"platform": "twitter"}]

        with (
            patch.object(obj, "_retry_feedback_lines", return_value=["feedback"]) as feedback_lines,
            patch.object(obj, "_retry_rewrite_instruction_lines", return_value=["rewrite"]) as rewrite_lines,
        ):
            lines = obj._retry_prompt_feedback_lines(quality_feedback)

        assert lines == ["feedback", "rewrite"]
        feedback_lines.assert_called_once_with(quality_feedback)
        rewrite_lines.assert_called_once_with()

    def test_basic_feedback_injection(self):
        obj = self._make_instance()
        feedback = [
            {"platform": "twitter", "score": 40, "issues": ["최소 글자 수 미달"]},
        ]
        result = obj._build_retry_prompt("원본 프롬프트", feedback)
        assert "원본 프롬프트" in result
        assert "twitter" in result
        assert "40/100" in result
        assert "최소 글자 수 미달" in result
        # Fix instruction should be matched
        assert "수정 방법" in result

    def test_multiple_platforms(self):
        obj = self._make_instance()
        feedback = [
            {"platform": "twitter", "score": 30, "issues": ["CTA 위반"]},
            {"platform": "threads", "score": 50, "issues": ["해시태그 초과"]},
        ]
        result = obj._build_retry_prompt("prompt", feedback)
        assert "twitter" in result
        assert "threads" in result

    def test_unmatched_issue_still_listed(self):
        obj = self._make_instance()
        feedback = [
            {"platform": "x", "score": 60, "issues": ["알 수 없는 문제"]},
        ]
        result = obj._build_retry_prompt("prompt", feedback)
        assert "알 수 없는 문제" in result
        assert "x" in result
