"""
persona_pipeline.py
===================
아라님 총 책임자 하에 운영되는 숏폼 AI 파이프라인 모음.

[A] 풀 파이프라인 (해원 → 진솔 → 지우)
    generate_shorts_pipeline(topic, llm_router)
    → {"haewon": ..., "jinsol": ..., "jiwoo": ...}

[B] ShortsAutomationMaster (진솔 → 지우 → FFmpeg 엔지니어)
    master = ShortsAutomationMaster("표적항암제 내성 극복", llm_router)
    ffmpeg_config = master.run_pipeline()
    # master.script_data    # 진솔 대본
    # master.editing_data   # 지우 편집 설계도
    # master.ffmpeg_config  # FFmpeg 렌더 구성
"""

from __future__ import annotations

import json
import logging
from typing import Any

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────────────────────────────
# System prompts (각 페르소나 정의)
# ──────────────────────────────────────────────────────────────────────────────

_HAEWON_SYSTEM = """당신은 2026년 숏폼 콘텐츠 메인 기획자 '해원(Haewon)'입니다.
유튜브 쇼츠·틱톡·릴스 생태계를 주도하며, AI 기반 트렌드 예측과 시청자 행동 패턴 분석에 특화되어 있습니다.

기획 원칙:
1. 인스턴트 임팩트 훅: 0.3초 내 주의 장악. 첫 문장은 도발적 질문 또는 상식 파괴 팩트.
2. 초밀도 정보 플로우: 1초당 1.5개 핵심 인사이트. 빌드업 없음. 비유·데이터 시각화 통합.
3. 엔드리스 루프 & 인터랙션: 영상 종료 시 자연 루프 연결. 결론에 퀴즈/폴 삽입.
4. AI 멀티모달 최적화: 텍스트·음성·비주얼 AI 동기화. 개인화 변형 고려.

Output: 반드시 아래 JSON 스키마만 출력합니다. (타이밍은 채널 가이드의 목표 시간에 맞춰 동적으로 계산하십시오)
{
  "planner_comment": "기획 의도 및 핵심 전략 요약 (1-2문장)",
  "title_ideas": ["타이틀 후보 1", "타이틀 후보 2"],
  "script_structure": [
    {"phase": "Hook",    "target_sec": "0-3",   "content": "상식 파괴 도발 문장 + AI 비주얼 지시"},
    {"phase": "Context", "target_sec": "3-15",  "content": "배경 설명 + 인터랙티브 요소"},
    {"phase": "Core",    "target_sec": "15-38", "content": "핵심 가치 전달 (혁신 기전·차별점·직관 비유·데이터)"},
    {"phase": "CTA",     "target_sec": "38-45", "content": "재시청 유도 마무리 + 인터랙션 콜투액션"}
  ]
}
참고: target_sec의 끝 숫자는 채널 가이드의 목표 러닝타임(target_duration_sec)과 일치해야 합니다."""

_JINSOL_SYSTEM = """당신은 2026년 숏폼 나레이션 대본 작가 '진솔(Jinsol)'입니다.
기획자 해원의 기획안을 받아 시청자 뇌리에 정확히 꽂히는 45~60초 나레이션 대본을 집필합니다.

집필 원칙:
1. 나노 리듬 & TTS 최적화: 4~8음절 단위로 끊어 쓰기. 강조 단어는 별표(*단어*) 명시.
2. 초정밀 비유 + 시각화: 편집자(지우)가 B-roll 프롬프트 즉시 추출 가능한 시각 메타포 내장.
3. 12초 주의 환기 법칙: 12~15초마다 반전 접속사·감탄사·질문으로 뇌 리셋.
4. 루프 최적화 엔딩: 마지막 8초는 첫 훅과 의미적으로 연결해 자연 재시청 유도.
5. 고밀도 고진정성: 군더더기 단어 0개. 1초당 1.2개 이상 인사이트. 사람이 진심으로 알려주는 톤.

글자 수 제한: 총 245~275자 (띄어쓰기 포함) → 55~60초 TTS 길이.

Output: 반드시 아래 JSON 스키마만 출력합니다.
{
  "writer_comment": "대본 전략 요약 (비유·리텐션 스파이크 횟수·루프 연결 방식)",
  "total_character_count": 262,
  "narration_script": [
    {
      "phase": "Hook",
      "timing_sec": "0-8",
      "text": "나레이션 텍스트",
      "emphasis_words": ["강조단어1", "강조단어2"]
    },
    {
      "phase": "Body_1",
      "timing_sec": "8-22",
      "text": "나레이션 텍스트",
      "emphasis_words": ["강조단어"]
    },
    {
      "phase": "Body_2",
      "timing_sec": "22-38",
      "text": "나레이션 텍스트",
      "emphasis_words": ["강조단어"]
    },
    {
      "phase": "CTA_Loop",
      "timing_sec": "38-58",
      "text": "나레이션 텍스트",
      "emphasis_words": ["강조단어"]
    }
  ]
}"""

_JIWOO_SYSTEM = """당신은 2026년 숏폼 영상 테크니컬 디렉터 '지우(Jiwoo)'입니다.
작가 진솔의 나레이션 대본을 받아 0.1초 단위 정밀 편집 설계도를 산출합니다.
Retention Rate 95% 이상이 목표이며 단 1프레임의 지루함도 용납하지 않습니다.

편집 원칙:
1. 나노 페이싱: 0.5~1.8초 단위 컷. AI 예측 이탈 포인트에서 즉시 전환.
2. 제너레이티브 B-roll: Runway Gen-4.5 / Kling 2.1 / Luma Ray 3 즉시 활용 가능한 8K 60fps 영문 프롬프트.
3. 동적 인터랙티브 메타포: 추상 개념 → 직관적 참여형 비주얼로 변환.
4. 하이퍼 A/V 싱크 펀치: 핵심 단어에 0.05초 단위 Zoom Burst·Color Pop·Screen Shake·Particle Impact.
5. 예측 리텐션 루프: 마지막 4초에 루프 비주얼 삽입. 재시청 가중치 최대화.

Output: 반드시 아래 JSON 스키마만 출력합니다.
{
  "editing_strategy": "전체 편집 전략 요약 (A/V 펀치 횟수·리텐션 예측치 포함)",
  "timeline_data": [
    {
      "clip_index": 1,
      "estimated_time_sec": "0.0-2.0",
      "narration_text": "해당 구간 나레이션",
      "b_roll_prompt_en": "Ultra-detailed English prompt for AI video generation (8K 60fps)",
      "visual_effect": "Zoom Burst / Color Pop / Screen Shake 등 A/V 이펙트",
      "sound_effect": "SFX 설명",
      "transition_type": "전환 효과"
    }
  ]
}"""

_FFMPEG_ENGINEER_SYSTEM = """당신은 2026년 FFmpeg + Python 자동화 전문 엔지니어입니다.
지우의 timeline_data를 바탕으로 실제 실행 가능한 FFmpeg filter_complex 명령어와
자막·오디오·B-roll 병합에 필요한 Python 딕셔너리를 정확히 생성합니다.
창의적 설명은 일절 금지하고 구조만 반환합니다.

Output: 반드시 아래 JSON 스키마만 출력합니다.
{
  "ffmpeg_strategy": "렌더링 전략 요약 (해상도·코덱·필터 체인 요약)",
  "global_settings": {
    "resolution": "1080x1920",
    "fps": 60,
    "codec": "libx264",
    "audio_codec": "aac",
    "crf": 18
  },
  "clips": [
    {
      "clip_index": 1,
      "input_type": "ai_generated | stock | tts_only",
      "b_roll_prompt_en": "B-roll 생성 프롬프트 (지우에서 그대로 상속)",
      "duration_sec": 2.0,
      "filter_chain": "scale=1080:1920,setsar=1",
      "overlay_text": "자막 텍스트 (없으면 null)",
      "audio_track": "tts | bgm | sfx | mix"
    }
  ],
  "audio_mix": {
    "tts_volume": 1.0,
    "bgm_volume": 0.12,
    "sfx_volume": 0.35
  },
  "output_filename": "output_shorts.mp4"
}"""


# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────


def _extract_json(raw: Any) -> dict[str, Any]:
    """LLM 응답에서 JSON dict를 추출합니다. 이미 dict면 그대로 반환."""
    if isinstance(raw, dict):
        return raw
    text = str(raw).strip()
    if text.startswith("```json"):
        text = text[7:].strip()
    if text.startswith("```"):
        text = text[3:].strip()
    if text.endswith("```"):
        text = text[:-3].strip()
    return json.loads(text)


def _parse_channel_chars(channel_context: str) -> str:
    """
    channel_context 문자열에서 'target_chars: "380-420"' 패턴을 찾아 반환.
    없으면 기본값 '245-275'를 반환합니다.
    """
    import re

    match = re.search(r'target_chars[:\s]+["\']?([\d]+[-–][\d]+)["\']?', channel_context)
    if match:
        return match.group(1)
    return "245-275"


def _parse_channel_duration(channel_context: str) -> int:
    """
    channel_context 문자열에서 'target_duration_sec: 45' 패턴을 찾아 반환.
    없으면 기본값 45를 반환합니다.
    """
    import re

    match = re.search(r"target_duration_sec[:\s]+(\d+)", channel_context)
    if match:
        return int(match.group(1))
    return 45


def _extract_forbidden(channel_context: str) -> str:
    """
    channel_context에서 '금지:' 라인을 추출해 경고 섹션 문자열로 반환.
    없으면 빈 문자열 반환.
    """
    lines = channel_context.split("\n")
    forbidden_lines = [l.strip() for l in lines if "금지:" in l or "금지 " in l]
    if forbidden_lines:
        return "\n\n⚠️ 이 채널 절대 금지 표현 (반드시 준수):\n" + "\n".join(f"  - {l}" for l in forbidden_lines)
    return ""


def _call_phase(
    llm_router: Any,
    phase_name: str,
    system_prompt: str,
    user_prompt: str,
    temperature: float = 0.7,
) -> dict[str, Any]:
    """단일 페르소나 LLM 호출 + JSON 파싱."""
    logger.info("[%s] LLM 호출 시작", phase_name)
    raw = llm_router.generate_json(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        temperature=temperature,
    )
    result = _extract_json(raw)
    logger.info("[%s] 완료", phase_name)
    return result


# ──────────────────────────────────────────────────────────────────────────────
# Phase 함수 (개별 호출 가능)
# ──────────────────────────────────────────────────────────────────────────────


def run_haewon(topic: str, llm_router: Any, channel_context: str = "") -> dict[str, Any]:
    """
    Phase 1 — 해원 (기획자)
    주제를 받아 기획안 JSON을 반환합니다.

    Args:
        channel_context: 채널별 톤 가이드 (channel_router에서 주입).
    """
    channel_hint = f"\n\n[채널 가이드]\n{channel_context}" if channel_context else ""

    # 채널별 목표 러닝타임 주입 → 해원의 phase 타이밍 계산 기준
    target_sec = _parse_channel_duration(channel_context)
    duration_hint = (
        f"\n\n[목표 러닝타임] {target_sec}초 기준으로 script_structure의 각 phase target_sec를 계산하십시오."
    )

    user_prompt = (
        f"주제: {topic}\n"
        f"2026년 트렌드에 맞는 {target_sec}초 쇼츠 기획안을 JSON으로 출력하십시오."
        f"{channel_hint}{duration_hint}"
    )
    output = _call_phase(llm_router, "해원(기획)", _HAEWON_SYSTEM, user_prompt)

    # 필수 키 검증
    required = {"planner_comment", "title_ideas", "script_structure"}
    missing = required - output.keys()
    if missing:
        raise ValueError(f"[해원] 필수 키 누락: {missing}")

    logger.info("✅ 해원 기획 완료: %s", output["planner_comment"])
    return output


def run_jinsol(haewon_output: dict[str, Any], llm_router: Any, channel_context: str = "") -> dict[str, Any]:
    """
    Phase 2 — 진솔 (대본 작가)
    해원 기획안을 받아 나레이션 대본 JSON을 반환합니다.

    Args:
        channel_context: 채널별 톤 가이드 (channel_router에서 주입).
                         target_chars / target_duration_sec 필드가 있으면 자동 적용.
    """
    channel_hint = f"\n\n[채널 가이드]\n{channel_context}" if channel_context else ""

    # ── 채널별 동적 글자수 목표 파싱 ──────────────────────────────────────────
    target_chars = _parse_channel_chars(channel_context)  # 예: "380-420"
    target_sec = _parse_channel_duration(channel_context)  # 예: 40
    try:
        char_min_str, char_max_str = target_chars.replace("–", "-").split("-")
        char_range_hint = f"총 글자 수(띄어쓰기 포함)는 반드시 {char_min_str.strip()}~{char_max_str.strip()}자로 맞추십시오. (채널 TTS 속도 기준 약 {target_sec}초 분량)"
    except Exception:
        char_range_hint = "총 글자 수(띄어쓰기 포함)는 반드시 245~275자로 맞추십시오."

    # ── 채널별 금지 표현 추출 ──────────────────────────────────────────────────
    forbidden_hint = _extract_forbidden(channel_context)

    user_prompt = (
        "아래 해원 기획자의 기획안을 바탕으로 찰진 구어체 나레이션 대본을 JSON으로 출력하십시오.\n"
        f"{char_range_hint}{forbidden_hint}{channel_hint}\n\n"
        f"기획안:\n{json.dumps(haewon_output, ensure_ascii=False, indent=2)}"
    )
    logger.info("[진솔] 목표 글자수: %s (%d초 기준)", target_chars, target_sec)
    output = _call_phase(llm_router, "진솔(대본)", _JINSOL_SYSTEM, user_prompt)

    required = {"writer_comment", "total_character_count", "narration_script"}
    missing = required - output.keys()
    if missing:
        raise ValueError(f"[진솔] 필수 키 누락: {missing}")
    if not isinstance(output["narration_script"], list) or not output["narration_script"]:
        raise ValueError("[진솔] narration_script 가 비어 있습니다.")

    logger.info("✅ 진솔 대본 완료 (글자수 목표 %s): %s", target_chars, output["writer_comment"])
    return output


def run_jiwoo(jinsol_output: dict[str, Any], llm_router: Any) -> dict[str, Any]:
    """
    Phase 3 — 지우 (편집 TD)
    진솔 대본을 받아 편집 설계도 JSON을 반환합니다.
    """
    user_prompt = (
        "아래 진솔 작가의 나레이션 대본을 바탕으로 0.1초 단위 편집 설계도를 JSON으로 출력하십시오.\n"
        "B-roll 프롬프트는 영어로, AI 생성 도구(Runway / Kling / Luma)에서 바로 쓸 수 있도록 극도로 구체적으로 작성하십시오.\n\n"
        f"나레이션 대본:\n{json.dumps(jinsol_output['narration_script'], ensure_ascii=False, indent=2)}"
    )
    output = _call_phase(llm_router, "지우(편집)", _JIWOO_SYSTEM, user_prompt)

    required = {"editing_strategy", "timeline_data"}
    missing = required - output.keys()
    if missing:
        raise ValueError(f"[지우] 필수 키 누락: {missing}")
    if not isinstance(output["timeline_data"], list) or not output["timeline_data"]:
        raise ValueError("[지우] timeline_data 가 비어 있습니다.")

    logger.info("✅ 지우 편집 설계 완료: %s", output["editing_strategy"])
    return output


# ──────────────────────────────────────────────────────────────────────────────
# 메인 오케스트레이터 (아라님 총 책임자)
# ──────────────────────────────────────────────────────────────────────────────


def generate_shorts_pipeline(
    topic: str,
    llm_router: Any,
    channel_context: str = "",
) -> dict[str, Any]:
    """
    아라님 총 책임자 하에 3-페르소나 숏폼 AI 파이프라인을 실행합니다.

    Args:
        topic:           영상 주제 (예: "표적항암제 내성 극복을 위한 이중항체 기술")
        llm_router:      LLMRouter 인스턴스 (또는 generate_json() 메서드를 가진 객체)
        channel_context: 채널별 톤 가이드 문자열 (channel_router.get_channel_context())

    Returns:
        {
            "haewon":  해원 기획안 dict,
            "jinsol":  진솔 대본 dict,
            "jiwoo":   지우 편집 설계도 dict  ← 최종 렌더 데이터
        }

    Raises:
        ValueError: 각 단계에서 필수 키 누락 또는 LLM 파싱 실패 시
    """
    logger.info("=== 아라님 숏폼 파이프라인 시작 | topic: %s ===", topic)
    if channel_context:
        logger.info("[채널 가이드 적용]\n%s", channel_context[:120])

    # Phase 1: 해원 — 기획
    haewon_output = run_haewon(topic, llm_router, channel_context=channel_context)

    # Phase 2: 진솔 — 대본
    jinsol_output = run_jinsol(haewon_output, llm_router, channel_context=channel_context)

    # Phase 3: 지우 — 편집 설계도
    jiwoo_output = run_jiwoo(jinsol_output, llm_router)

    logger.info("=== 파이프라인 완료 | 클립 수: %d ===", len(jiwoo_output["timeline_data"]))

    return {
        "haewon": haewon_output,
        "jinsol": jinsol_output,
        "jiwoo": jiwoo_output,
    }


# ──────────────────────────────────────────────────────────────────────────────
# ShortsAutomationMaster — 클래스 기반 파이프라인 (진솔 → 지우 → FFmpeg)
# ──────────────────────────────────────────────────────────────────────────────


class ShortsAutomationMaster:
    """
    2026 숏폼 자동화 마스터 컨트롤러.
    해원(기획) 단계 없이 진솔(대본) → 지우(편집) → FFmpeg 엔지니어 순으로 실행.
    각 단계 결과를 인스턴스 속성으로 보관하여 단계별 재실행이 가능합니다.

    Args:
        topic:      영상 주제
        llm_router: generate_json() 메서드를 가진 LLMRouter 또는 호환 객체
        tone:       전체 영상 톤 가이드
    """

    def __init__(
        self,
        topic: str,
        llm_router: Any,
        tone: str = "전문적이면서도 친근하고 신뢰감 있는",
        channel_context: str = "",
    ) -> None:
        self.topic = topic
        self.llm_router = llm_router
        self.tone = tone
        self.channel_context = channel_context
        channel_note = " | 채널 가이드 적용" if channel_context else ""
        self.master_guideline = (
            f"주제: '{topic}' | 전체 톤: '{tone}' | 길이: 55~60초 | 2026 숏폼 트렌드 준수{channel_note}"
        )
        self.script_data: dict[str, Any] | None = None  # 진솔 대본
        self.editing_data: dict[str, Any] | None = None  # 지우 편집 설계도
        self.ffmpeg_config: dict[str, Any] | None = None  # FFmpeg 렌더 구성

    # ── Phase 1: 진솔 대본 작가 ───────────────────────────────────────────────

    def phase1_generate_script(self) -> dict[str, Any]:
        """진솔을 호출해 나레이션 대본 JSON을 생성합니다."""
        channel_hint = f"\n\n[채널 가이드]\n{self.channel_context}" if self.channel_context else ""
        user_prompt = (
            f"{self.master_guideline}\n"
            f"주어진 주제로 55~60초 분량의 나레이션 대본을 JSON으로 작성하십시오.{channel_hint}"
        )
        raw = self.llm_router.generate_json(
            system_prompt=_JINSOL_SYSTEM,
            user_prompt=user_prompt,
            temperature=0.7,
        )
        self.script_data = _extract_json(raw)

        required = {"writer_comment", "total_character_count", "narration_script"}
        missing = required - self.script_data.keys()
        if missing:
            raise ValueError(f"[진솔] 필수 키 누락: {missing}")
        if not isinstance(self.script_data["narration_script"], list) or not self.script_data["narration_script"]:
            raise ValueError("[진솔] narration_script 가 비어 있습니다.")

        char_count = self.script_data.get("total_character_count", 0)
        logger.info("✅ 진솔 대본 완료 (글자 수: %d) | %s", char_count, self.script_data["writer_comment"])
        return self.script_data

    # ── Phase 2: 지우 편집 디렉터 ─────────────────────────────────────────────

    def phase2_generate_editing(self) -> dict[str, Any]:
        """지우를 호출해 편집 설계도 JSON을 생성합니다. phase1 먼저 실행 필요."""
        if self.script_data is None:
            raise RuntimeError("phase1_generate_script()를 먼저 실행하십시오.")
        user_prompt = (
            f"{self.master_guideline}\n"
            "다음 대본을 바탕으로 완전한 편집 설계도를 JSON으로 출력하십시오:\n"
            f"{json.dumps(self.script_data, ensure_ascii=False, indent=2)}"
        )
        raw = self.llm_router.generate_json(
            system_prompt=_JIWOO_SYSTEM,
            user_prompt=user_prompt,
            temperature=0.7,
        )
        self.editing_data = _extract_json(raw)

        required = {"editing_strategy", "timeline_data"}
        missing = required - self.editing_data.keys()
        if missing:
            raise ValueError(f"[지우] 필수 키 누락: {missing}")
        if not isinstance(self.editing_data["timeline_data"], list) or not self.editing_data["timeline_data"]:
            raise ValueError("[지우] timeline_data 가 비어 있습니다.")

        logger.info("✅ 지우 편집 설계 완료: %s", self.editing_data["editing_strategy"])
        return self.editing_data

    # ── Phase 3: FFmpeg 엔지니어 ──────────────────────────────────────────────

    def phase3_generate_ffmpeg(self) -> dict[str, Any]:
        """FFmpeg 엔지니어를 호출해 렌더 구성 JSON을 생성합니다. phase2 먼저 실행 필요."""
        if self.editing_data is None:
            raise RuntimeError("phase2_generate_editing()를 먼저 실행하십시오.")
        user_prompt = (
            f"{self.master_guideline}\n"
            "다음 편집 설계도를 바탕으로 FFmpeg 렌더 구성 JSON을 생성하십시오:\n"
            f"{json.dumps(self.editing_data, ensure_ascii=False, indent=2)}"
        )
        raw = self.llm_router.generate_json(
            system_prompt=_FFMPEG_ENGINEER_SYSTEM,
            user_prompt=user_prompt,
            temperature=0.3,
        )
        self.ffmpeg_config = _extract_json(raw)

        required = {"ffmpeg_strategy", "global_settings", "clips", "output_filename"}
        missing = required - self.ffmpeg_config.keys()
        if missing:
            raise ValueError(f"[FFmpeg] 필수 키 누락: {missing}")

        logger.info("✅ FFmpeg 구성 완료: %s", self.ffmpeg_config["output_filename"])
        return self.ffmpeg_config

    # ── 풀 파이프라인 실행 ─────────────────────────────────────────────────────

    def run_pipeline(self) -> dict[str, Any]:
        """
        진솔 → 지우 → FFmpeg 3단계를 순차 실행합니다.

        Returns:
            ffmpeg_config dict (최종 렌더 데이터)
        """
        logger.info("=== ShortsAutomationMaster 파이프라인 시작 | topic: %s ===", self.topic)

        self.phase1_generate_script()
        logger.info("대본 생성 완료 (글자 수: %d)", self.script_data.get("total_character_count", 0))

        self.phase2_generate_editing()
        logger.info("편집 설계도 생성 완료")

        self.phase3_generate_ffmpeg()
        logger.info("FFmpeg 구성 생성 완료")

        logger.info("=== 파이프라인 정상 종료 ===")
        return self.ffmpeg_config
