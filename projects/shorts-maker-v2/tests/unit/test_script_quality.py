"""스크립트 품질 강화 테스트 (Phase 2).

검증 항목:
  1. Hook 15자 트림 (_trim_hook_to_limit)
  2. CTA 금지어 감지 (_validate_cta)
  3. 페르소나 키워드 스코어 (_score_persona_match)
  4. parse_script_payload() Hook 트림 통합
  5. run() CTA 경고 로깅
"""

from __future__ import annotations

from types import SimpleNamespace

from shorts_maker_v2.models import ScenePlan
from shorts_maker_v2.pipeline.script_step import ScriptStep

# ── 공통 픽스처 ───────────────────────────────────────────────────────────────


def make_scene(
    *,
    narration_ko: str,
    visual_prompt_en: str = "some visual",
    scene_id: int = 1,
    target_sec: float = 5.0,
    structure_role: str = "body",
) -> ScenePlan:
    return ScenePlan(
        scene_id=scene_id,
        narration_ko=narration_ko,
        visual_prompt_en=visual_prompt_en,
        target_sec=target_sec,
        structure_role=structure_role,
    )


def make_config(*, duration_range: tuple[int, int] = (20, 30), tts_speed: float = 1.05):
    return SimpleNamespace(
        providers=SimpleNamespace(
            llm="openai",
            llm_model="gpt-4o-mini",
            tts_speed=tts_speed,
            thinking_level="low",
            thinking_level_review="high",
            embedding_model="gemini-embedding-2-preview",
        ),
        project=SimpleNamespace(
            default_scene_count=2,
            language="ko-KR",
            script_review_enabled=False,
            script_review_min_score=6,
            structure_presets={},
        ),
        video=SimpleNamespace(
            target_duration_sec=duration_range,
        ),
    )


class FakeLLMRouter:
    """단순 응답 큐. LLMRouter 인터페이스 최소 구현."""

    def __init__(self, responses: list):
        self._responses = list(responses)

    def generate_json(self, *, system_prompt="", user_prompt="", temperature=0.7, thinking_level=None):
        if not self._responses:
            raise AssertionError("No more fake responses")
        return self._responses.pop(0)


# ── 1. Hook 15자 트림 ─────────────────────────────────────────────────────────


class TestTrimHookToLimit:
    def test_within_limit_unchanged(self):
        """15자 이하면 변경 없이 그대로 반환."""
        narration = "짧은후크야"  # 5자
        assert ScriptStep._trim_hook_to_limit(narration) == narration

    def test_exactly_at_limit_unchanged(self):
        """정확히 15자이면 변경 없이 그대로 반환."""
        narration = "열다섯글자바로이야"  # 9자 (테스트용으로 limit 설정)
        result = ScriptStep._trim_hook_to_limit(narration, limit=9)
        assert result == narration

    def test_over_limit_trimmed(self):
        """20자 → limit=15 기준 15자로 트림."""
        narration = "이것은스크롤을멈추게하는강력한후크입니다"  # 20자 이상
        result = ScriptStep._trim_hook_to_limit(narration, limit=15)
        assert len(result) <= 15

    def test_trim_korean_char_boundary(self):
        """한국어 글자 단위로 트림 (공백 없이도 정확히 잘림)."""
        narration = "가나다라마바사아자차카타파하가나다라마"
        result = ScriptStep._trim_hook_to_limit(narration, limit=10)
        assert len(result) <= 10
        # 원본의 앞 10자로 시작해야 함
        assert result == narration[:10].rstrip()

    def test_trailing_space_stripped(self):
        """트림 후 trailing 공백이 있으면 rstrip으로 정리."""
        narration = "ab cd ef gh ij kl"  # 공백 포함 18자
        result = ScriptStep._trim_hook_to_limit(narration, limit=6)
        assert result == "ab cd"  # 6자 트림 후 rstrip → "ab cd" (5자, 마지막 공백 제거)

    # 경계값 검사
    def test_empty_string_returns_empty(self):
        assert ScriptStep._trim_hook_to_limit("", limit=15) == ""

    def test_single_char_within_limit(self):
        assert ScriptStep._trim_hook_to_limit("가") == "가"

    # ── 새 기본값 (limit=40) + 단어 경계 우선 회귀 ───────────────────────────
    # Phase 1 #5: 38~55자 hook 이 통째로 잘리던 사례 (2026-05-19 history run).
    # `로마는 하루아침에 무너지지 않았다 — 그 진짜 이유` 같은 의미 있는 hook 이
    # `로마는 하루아침에 무너` 14자로 잘려 의미가 깨졌다.

    def test_default_limit_is_55(self):
        """Default limit 은 55 (T-AB026: 정보 밀집형 hook 보존)."""
        narration = "x" * 56
        result = ScriptStep._trim_hook_to_limit(narration)
        assert len(result) <= 55

    def test_38char_korean_hook_preserved(self):
        """38자 한국어 hook 은 default limit=55 이내라 그대로 유지."""
        narration = "로마는 하루아침에 무너지지 않았다 그 진짜 이유는"  # 24자
        # 24자 < 55 → 변형 없음
        assert ScriptStep._trim_hook_to_limit(narration) == narration

    def test_word_boundary_preferred_when_close(self):
        """공백이 limit 근처(≥ limit-8)에 있으면 단어 경계 기준 절단."""
        # limit=15, head="짧은 후크가 강렬해야" → 마지막 공백이 8번 인덱스(>= 15-8=7).
        narration = "짧은 후크가 강렬해야 합니다요"
        result = ScriptStep._trim_hook_to_limit(narration, limit=15)
        assert result == "짧은 후크가 강렬해야"  # 공백 기준 12자
        assert " " not in result[-1:]  # trailing 공백 없음

    def test_word_boundary_skipped_when_space_too_early(self):
        """공백이 limit-8 보다 앞에 있으면 단어 경계 무시하고 문자 트림."""
        # limit=20. 마지막 공백이 인덱스 4 (< 20-8=12). 단어 경계 적용 안 함.
        narration = "abcd efghijklmnopqrstuvwxyz12345"
        result = ScriptStep._trim_hook_to_limit(narration, limit=20)
        # 첫 공백은 4번 → 단어 경계 너무 이른 → 문자 트림 (앞 20)
        assert result == narration[:20].rstrip()


# ── 2. CTA 금지어 감지 ────────────────────────────────────────────────────────


class TestValidateCta:
    def test_clean_cta_returns_empty(self):
        """금지어 없는 CTA는 빈 리스트 반환."""
        clean = "오늘부터 물 한 컵 더 마셔보세요."
        assert ScriptStep._validate_cta(clean) == []

    def test_detects_subscription(self):
        """'구독' 감지."""
        assert "구독" in ScriptStep._validate_cta("채널 구독 부탁드려요!")

    def test_detects_like(self):
        """'좋아요' 감지."""
        assert "좋아요" in ScriptStep._validate_cta("좋아요 눌러주세요.")

    def test_detects_english_subscribe(self):
        """영어 'subscribe' 감지."""
        assert "subscribe" in ScriptStep._validate_cta("Please subscribe to the channel.")

    def test_detects_multiple_violations(self):
        """복수 위반 항목 모두 반환."""
        text = "구독하고 좋아요 눌러주세요!"
        violations = ScriptStep._validate_cta(text)
        assert "구독" in violations
        assert "좋아요" in violations
        assert "눌러주" in violations

    def test_detects_bell(self):
        """'알림' 감지."""
        assert "알림" in ScriptStep._validate_cta("알림 설정 잊지 마세요.")

    def test_detects_follow(self):
        """'follow' 감지."""
        assert "follow" in ScriptStep._validate_cta("Follow for more tips!")

    def test_case_sensitive_korean(self):
        """한국어 금지어는 대소문자 구분 없지만 부분 일치 작동."""
        # '구독하면' → '구독' 포함됨
        assert "구독" in ScriptStep._validate_cta("구독하면 유익한 정보를 더 받을 수 있어요.")


# ── 3. 페르소나 키워드 스코어 ─────────────────────────────────────────────────


class TestScorePersonaMatch:
    def test_empty_scenes_returns_zero(self):
        """씬이 없으면 0.0 반환."""
        assert ScriptStep._score_persona_match([], "ai_tech") == 0.0

    def test_unknown_channel_returns_neutral(self):
        """알 수 없는 채널 키는 0.5 중립값 반환."""
        scenes = [make_scene(narration_ko="아무 내용이나 들어가도 됩니다.")]
        assert ScriptStep._score_persona_match(scenes, "unknown_channel") == 0.5

    def test_ai_tech_high_score(self):
        """ai_tech 채널 키워드가 풍부하면 높은 스코어."""
        text = "AI 모델의 데이터 기반 알고리즘 연구 결과, 기술 개발이 급속도로 진화하고 있습니다."
        scenes = [make_scene(narration_ko=text)]
        score = ScriptStep._score_persona_match(scenes, "ai_tech")
        assert score > 0.4, f"score {score} should be > 0.4"

    def test_psychology_keywords(self):
        """psychology 채널 키워드 감지."""
        text = "당신의 마음 속에서 감정이 공감을 통해 관계를 형성합니다."
        scenes = [make_scene(narration_ko=text)]
        score = ScriptStep._score_persona_match(scenes, "psychology")
        assert score > 0.4

    def test_space_keywords(self):
        """space 채널 키워드 감지."""
        text = "우주의 광년을 넘어 은하와 블랙홀, 태양과 지구, 별과 빛의 신비."
        scenes = [make_scene(narration_ko=text)]
        score = ScriptStep._score_persona_match(scenes, "space")
        assert score > 0.5

    def test_wrong_channel_low_score(self):
        """채널 키워드와 무관한 내용은 낮은 스코어."""
        text = "오늘 날씨가 좋아서 공원에 나갔습니다."
        scenes = [make_scene(narration_ko=text)]
        score = ScriptStep._score_persona_match(scenes, "ai_tech")
        assert score < 0.4, f"score {score} should be < 0.4"

    def test_multiple_scenes_aggregated(self):
        """여러 씬의 텍스트를 합산하여 스코어링."""
        scene1 = make_scene(narration_ko="건강한 습관이 중요합니다.", scene_id=1)
        scene2 = make_scene(narration_ko="운동과 식단, 수면이 몸에 효과적입니다.", scene_id=2)
        score = ScriptStep._score_persona_match([scene1, scene2], "health")
        assert score > 0.4


# ── 4. parse_script_payload Hook 트림 통합 ────────────────────────────────────


class TestParseScriptPayloadHookTrim:
    def test_long_hook_trimmed_in_parse(self):
        """parse_script_payload 에서 55자 초과 Hook 이 자동 트림된다.

        T-AB026 에서 hard cap 을 40→55 로 상향했음. 정보 밀집형 hook 은 보존한다.
        """
        # 새 한도(55) 초과를 명시적으로 보장하기 위해 60자 이상으로 잡는다.
        long_hook = (
            "이것은매우긴후크문장으로마흔자를훨씬넘어가서반드시잘리는내용입니다그래야합니다"
            "추가로더많은단어를덧붙여서절대로한도안에들지않게만든다"
        )  # 65+ 자
        assert len(long_hook) > 55  # 테스트 데이터 자체 검증
        payload = {
            "title": "Hook Trim Test",
            "scenes": [
                {
                    "narration_ko": long_hook,
                    "visual_prompt_en": "Dramatic close-up",
                    "structure_role": "hook",
                },
                {
                    "narration_ko": "두 번째 씬 나레이션입니다.",
                    "visual_prompt_en": "Cinematic shot",
                    "structure_role": "cta",
                },
            ],
        }
        _, scenes = ScriptStep.parse_script_payload(
            payload,
            scene_count=2,
            target_duration_sec=(20, 30),
            language="ko-KR",
            tts_speed=1.05,
        )
        hook_scene = next(s for s in scenes if s.structure_role == "hook")
        assert len(hook_scene.narration_ko) <= 55, (
            f"Hook should be trimmed to <=55 chars but got {len(hook_scene.narration_ko)}"
        )
        # 그리고 실제로 트림이 일어났는지(원본보다 짧아졌는지) 검증
        assert len(hook_scene.narration_ko) < len(long_hook)

    def test_short_hook_unchanged_in_parse(self):
        """15자 이하 Hook은 parse에서 변경 없이 유지된다."""
        short_hook = "AI가 바꾼 세상"  # 8자
        payload = {
            "title": "Short Hook Test",
            "scenes": [
                {
                    "narration_ko": short_hook,
                    "visual_prompt_en": "Futuristic scene",
                    "structure_role": "hook",
                },
                {
                    "narration_ko": "결론 씬입니다.",
                    "visual_prompt_en": "Calm ending shot",
                    "structure_role": "cta",
                },
            ],
        }
        _, scenes = ScriptStep.parse_script_payload(
            payload,
            scene_count=2,
            target_duration_sec=(20, 30),
            language="ko-KR",
            tts_speed=1.05,
        )
        hook_scene = next(s for s in scenes if s.structure_role == "hook")
        assert hook_scene.narration_ko == short_hook


# ── 5. run() 통합 검증 ─────────────────────────────────────────────────────────


class TestRunIntegration:
    """run() 통합 테스트: 반환된 씬에서 직접 CTA/페르소나를 검증한다.

    caplog 대신 run() 반환 씬을 이용해 _validate_cta()/_score_persona_match()를
    직접 호출하여 기능 동작을 검증한다. 로거 전파 문제 우회.
    run()은 duration_range에 맞을 때까지 최대 max_generation_attempts=3번 LLM을 호출한다.
    FakeLLMRouter 응답을 3개 제공하여 응답 부족 AssertionError를 방지한다.
    """

    # duration_range 기준: Hook(2자≈1초) + CTA(35자이내≈13초 max) → 합산 ≤14초
    # CTA는 금지어를 포함하면서도 14초 범위 내에 들어오는 짧은 문장 사용
    _CLEAN_CTA = "지금 당장 물 한 컵을 마셔보세요."  # 금지어 없음 (15자)
    _BAD_CTA = "구독 부탁드려요!"  # 금지어 포함 (8자)

    def _make_payload(self, cta_narration: str, hook: str = "멈춰") -> dict:
        return {
            "title": "Test Video",
            "scenes": [
                {
                    "narration_ko": hook,
                    "visual_prompt_en": "Dramatic scene with bold typography",
                    "structure_role": "hook",
                },
                {
                    "narration_ko": cta_narration,
                    "visual_prompt_en": "Calm motivational ending scene",
                    "structure_role": "cta",
                },
            ],
        }

    def _run_with_payload(self, payload: dict, *, channel_key: str = "") -> tuple:
        client = FakeLLMRouter([payload, payload, payload])
        step = ScriptStep(
            config=make_config(duration_range=(8, 14)),
            llm_router=client,
            channel_key=channel_key,
        )
        return step.run("test topic")

    def test_cta_violation_detected(self):
        """run() 결과의 CTA 씬에 금지어가 포함되면 _validate_cta()가 감지한다."""
        bad_cta = self._BAD_CTA
        _, scenes, _, _ = self._run_with_payload(self._make_payload(bad_cta))

        cta_scenes = [s for s in scenes if s.structure_role == "cta"]
        assert cta_scenes, "CTA scene should exist"

        all_violations: list[str] = []
        for s in cta_scenes:
            all_violations.extend(ScriptStep._validate_cta(s.narration_ko))

        assert all_violations, (
            f"Expected CTA violations (구독, 부탁) but got none. CTA narration: {[s.narration_ko for s in cta_scenes]}"
        )
        assert "구독" in all_violations

    def test_cta_violation_included_in_run_return(self):
        """SMV2-CV002: CTA 금지어 위반이 run() 4번째 반환값에 포함돼야 함."""
        bad_cta = self._BAD_CTA
        _, _, _, cta_violations = self._run_with_payload(self._make_payload(bad_cta))
        assert cta_violations, f"Expected CTA violations in 4th return value, got: {cta_violations}"
        codes = [v.get("words", "") for v in cta_violations]
        assert any("구독" in c for c in codes), f"Expected '구독' in violation words, got: {codes}"

    def test_clean_cta_no_violations(self):
        """금지어 없는 CTA는 _validate_cta()가 빈 리스트를 반환한다."""
        clean_cta = self._CLEAN_CTA
        _, scenes, _, _ = self._run_with_payload(self._make_payload(clean_cta))

        cta_scenes = [s for s in scenes if s.structure_role == "cta"]
        for s in cta_scenes:
            violations = ScriptStep._validate_cta(s.narration_ko)
            assert violations == [], f"Unexpected violations in clean CTA: {violations}"

    def test_persona_score_with_channel_key(self):
        """channel_key가 있을 때 _score_persona_match()가 의미있는 스코어를 반환한다."""
        cta = self._CLEAN_CTA
        payload = self._make_payload(cta)
        client = FakeLLMRouter([payload, payload, payload])
        step = ScriptStep(
            config=make_config(duration_range=(8, 14)),
            llm_router=client,
            channel_key="health",
        )
        _, scenes, _, _ = step.run("health topic")

        # channel_key=health가 설정되어 있으므로 스코어가 계산되어야 함
        score = ScriptStep._score_persona_match(scenes, "health")
        # 반환값이 float이고 0.0~1.0 범위여야 함
        assert isinstance(score, float)
        assert 0.0 <= score <= 1.0

    def test_persona_score_neutral_for_unknown_channel(self):
        """알 수 없는 채널 키는 0.5 중립 스코어를 반환한다."""
        cta = self._CLEAN_CTA
        _, scenes, _, _ = self._run_with_payload(self._make_payload(cta))

        score = ScriptStep._score_persona_match(scenes, "unknown_xyz_channel")
        assert score == 0.5

    def test_hook_trimmed_in_run_output(self):
        """run() 결과에서 Hook 씬의 narration 이 55자 이하임을 확인한다.

        T-AB026: hard cap 40→55 로 상향. 55+ 자 hook 만 트림된다.
        """
        long_hook = "정말 충격적인 사실 하나를 지금 바로 들려드릴게요 그러니 끝까지 보세요 부탁드립니다"
        cta = self._CLEAN_CTA
        payload = self._make_payload(cta, hook=long_hook)
        _, scenes, _, _ = self._run_with_payload(payload)

        hook_scenes = [s for s in scenes if s.structure_role == "hook"]
        assert hook_scenes, "Hook scene should exist"
        for hook in hook_scenes:
            assert len(hook.narration_ko) <= 55, (
                f"Hook should be <=55 chars but got {len(hook.narration_ko)}: '{hook.narration_ko}'"
            )
            assert len(hook.narration_ko) < len(long_hook)


# ── T-AB032: _truncate_to_fit ─────────────────────────────────────────────────


def make_step(**kwargs) -> ScriptStep:
    config = make_config(**kwargs)
    return ScriptStep(config=config, llm_router=FakeLLMRouter([]), channel_key="ai_tech")


class TestTruncateToFit:
    """_truncate_to_fit: 총 길이 초과 시 씬별 비례 트림."""

    def _step(self) -> ScriptStep:
        return make_step(duration_range=(38, 52), tts_speed=1.05)

    def _scene(self, narration: str, sec: float = 10.0, sid: int = 1) -> ScenePlan:
        return ScenePlan(
            scene_id=sid,
            narration_ko=narration,
            visual_prompt_en="visual",
            target_sec=sec,
            structure_role="body",
        )

    def test_no_truncation_when_within_limit(self):
        """총 시간이 한도 이하면 씬이 변경되지 않아야 한다."""
        step = self._step()
        scene = self._scene("짧은 나레이션.", sec=2.0)
        result = step._truncate_to_fit([scene], max_total_sec=60.0, language="ko-KR", tts_speed=1.05)
        assert result[0].narration_ko == "짧은 나레이션."

    def test_truncation_shortens_long_narration(self):
        """총 시간 초과 시 나레이션이 짧아져야 한다."""
        step = self._step()
        long_narration = "가" * 300
        scene = self._scene(long_narration, sec=60.0)
        result = step._truncate_to_fit([scene], max_total_sec=5.0, language="ko-KR", tts_speed=1.05)
        assert len(result[0].narration_ko) < len(long_narration)

    def test_truncated_narration_ends_with_ellipsis(self):
        """자른 나레이션은 '...'로 끝나야 한다."""
        step = self._step()
        scene = self._scene("가" * 200, sec=40.0)
        result = step._truncate_to_fit([scene], max_total_sec=3.0, language="ko-KR", tts_speed=1.05)
        assert result[0].narration_ko.endswith("...")

    def test_minimum_narration_length_preserved(self):
        """잘린 나레이션은 최소 10자 이상이어야 한다 (또는 원본이 10자 미만이면 원본)."""
        step = self._step()
        short_narration = "짧게"  # 2자
        scene = self._scene(short_narration, sec=30.0)
        result = step._truncate_to_fit([scene], max_total_sec=1.0, language="ko-KR", tts_speed=1.05)
        assert len(result[0].narration_ko) <= len(short_narration) + 3  # at most original + ellipsis

    def test_scene_count_preserved(self):
        """씬 수는 변경되지 않아야 한다."""
        step = self._step()
        scenes = [self._scene("나레이션" * 50, sec=20.0, sid=i) for i in range(1, 4)]
        result = step._truncate_to_fit(scenes, max_total_sec=10.0, language="ko-KR", tts_speed=1.05)
        assert len(result) == 3

    def test_scene_ids_preserved(self):
        """씬 ID는 잘라내기 후에도 보존되어야 한다."""
        step = self._step()
        scenes = [self._scene("나레이션" * 30, sec=15.0, sid=sid) for sid in (1, 2, 3)]
        result = step._truncate_to_fit(scenes, max_total_sec=5.0, language="ko-KR", tts_speed=1.05)
        assert [s.scene_id for s in result] == [1, 2, 3]
