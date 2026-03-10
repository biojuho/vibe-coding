"""
SRT 자막 파일 생성.
Whisper 타이밍 JSON → .srt 형식으로 변환.
"""
from __future__ import annotations

from pathlib import Path

from shorts_maker_v2.render.karaoke import WordSegment, group_into_chunks, load_words_json


def _format_timestamp(seconds: float) -> str:
    """SRT 타임스탬프 포맷: HH:MM:SS,mmm"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int((seconds % 1) * 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def generate_srt_from_words(
    words: list[WordSegment],
    chunk_size: int = 3,
) -> str:
    """WordSegment 리스트 → SRT 문자열."""
    chunks = group_into_chunks(words, chunk_size)
    lines: list[str] = []
    for idx, (start, end, text) in enumerate(chunks, start=1):
        lines.append(str(idx))
        lines.append(f"{_format_timestamp(start)} --> {_format_timestamp(end)}")
        lines.append(text.strip())
        lines.append("")  # 빈 줄 구분자
    return "\n".join(lines)


def export_srt(
    words_json_paths: list[Path],
    scene_offsets: list[float],
    output_path: Path,
    chunk_size: int = 3,
    *,
    narrations: list[str] | None = None,
    durations: list[float] | None = None,
) -> Path:
    """
    여러 씬의 Whisper JSON을 합쳐 단일 SRT 생성.
    Whisper JSON이 없으면 narration 텍스트 기반 fallback SRT를 생성.

    Args:
        words_json_paths: 씬별 _words.json 파일 경로 리스트
        scene_offsets: 씬별 시작 시간 오프셋 (초)
        output_path: 출력 .srt 파일 경로
        chunk_size: 단어 묶음 크기
        narrations: (fallback) 씬별 narration 텍스트 리스트
        durations: (fallback) 씬별 duration 리스트 (초)

    Returns:
        생성된 SRT 파일 경로
    """
    all_words: list[WordSegment] = []

    for json_path, offset in zip(words_json_paths, scene_offsets):
        if not json_path.exists():
            continue
        words = load_words_json(json_path)
        for w in words:
            all_words.append(
                WordSegment(
                    word=w.word,
                    start=w.start + offset,
                    end=w.end + offset,
                )
            )

    # Whisper JSON 기반 SRT
    if all_words:
        srt_content = generate_srt_from_words(all_words, chunk_size)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(srt_content, encoding="utf-8")
        return output_path

    # Fallback: narration 텍스트 + duration 기반 간단 SRT 생성
    if narrations and durations and scene_offsets:
        srt_content = _generate_srt_from_narrations(
            narrations, durations, scene_offsets
        )
        if srt_content:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(srt_content, encoding="utf-8")
        return output_path

    return output_path


def _generate_srt_from_narrations(
    narrations: list[str],
    durations: list[float],
    offsets: list[float],
) -> str:
    """narration 텍스트를 씬 단위로 SRT 항목 생성 (Whisper 없을 때 fallback)."""
    lines: list[str] = []
    idx = 1
    for narration, duration, offset in zip(narrations, durations, offsets):
        if not narration.strip():
            continue
        # 긴 나레이션은 문장 단위로 분할
        sentences = [s.strip() for s in narration.replace(".", ".\n").replace("?", "?\n").replace("!", "!\n").split("\n") if s.strip()]
        if not sentences:
            sentences = [narration]

        # 각 문장에 시간을 균등 배분
        per_sentence = duration / max(len(sentences), 1)
        cursor = offset
        for sentence in sentences:
            start = cursor
            end = cursor + per_sentence
            lines.append(str(idx))
            lines.append(f"{_format_timestamp(start)} --> {_format_timestamp(end)}")
            lines.append(sentence)
            lines.append("")
            idx += 1
            cursor = end
    return "\n".join(lines)
