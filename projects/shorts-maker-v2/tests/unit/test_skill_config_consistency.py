"""스킬 문서 ↔ 코드/설정 정합성 회귀 테스트.

`.agents/skills/shorts-tts-quality/SKILL.md`는 TTS 음성·prosody 규칙의 참조
문서다. 과거 이 문서의 음성 매핑 표가 `channel_profiles.yaml`보다 뒤처져
5개 채널 중 4개가 불일치하는 사고가 있었다 (HANDOFF Next Steps #2).

이 테스트는 스킬 문서가 실제 SSOT(YAML / edge_tts_client.py)와 어긋나면
CI에서 즉시 실패하도록 만들어 문서 드리프트를 결정론적으로 차단한다.

검증 대상:
  - 음성 매핑 표      ↔ channel_profiles.yaml 의 `tts_voice`
  - `_CHANNEL_PROSODY` ↔ edge_tts_client.py 의 동일 딕셔너리
  - `pitch_hook_map`   ↔ edge_tts_client.py `_get_role_prosody` 내부 매핑

스킬 파일이 없는 환경(프로젝트 단독 체크아웃 등)에서는 모듈 전체를 skip한다.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest
import yaml

# ── 경로 ──────────────────────────────────────────────────────────────────────
_THIS = Path(__file__).resolve()
PROJECT_ROOT = _THIS.parents[2]  # tests/unit/ -> tests/ -> shorts-maker-v2/
WORKSPACE_ROOT = PROJECT_ROOT.parents[1]  # shorts-maker-v2/ -> projects/ -> 워크스페이스
SKILL_MD = WORKSPACE_ROOT / ".agents" / "skills" / "shorts-tts-quality" / "SKILL.md"
CHANNEL_PROFILES = PROJECT_ROOT / "channel_profiles.yaml"
EDGE_TTS_CLIENT = PROJECT_ROOT / "src" / "shorts_maker_v2" / "providers" / "edge_tts_client.py"

pytestmark = pytest.mark.skipif(
    not SKILL_MD.exists(),
    reason=f"shorts-tts-quality 스킬 파일 없음 — 정합성 검증 skip ({SKILL_MD})",
)


# ── 파서 헬퍼 ─────────────────────────────────────────────────────────────────
def _markdown_tables(text: str) -> list[list[list[str]]]:
    """연속된 `|...|` 줄을 하나의 표로 묶어 셀 2차원 배열 목록을 반환."""
    tables: list[list[list[str]]] = []
    current: list[list[str]] = []
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("|"):
            current.append([c.strip() for c in stripped.strip("|").split("|")])
        elif current:
            tables.append(current)
            current = []
    if current:
        tables.append(current)
    return tables


def _is_separator_row(row: list[str]) -> bool:
    """`|---|:--|` 같은 마크다운 표 구분선 여부."""
    return bool(row) and all(re.fullmatch(r":?-+:?", c or "") for c in row)


def _parse_voice_table(text: str) -> dict[str, str]:
    """SKILL.md의 음성 매핑 표에서 {channel: voice} 추출."""
    for table in _markdown_tables(text):
        rows = [r for r in table if not _is_separator_row(r)]
        if len(rows) < 2:
            continue
        header = rows[0]
        if len(header) >= 2 and "음성" in header[1]:
            return {r[0]: r[1] for r in rows[1:] if len(r) >= 2 and r[0]}
    raise AssertionError("SKILL.md에서 음성 매핑 표를 찾지 못했다")


def _skill_code_blocks(text: str) -> list[str]:
    """SKILL.md의 ```...``` 펜스 코드 블록 본문 목록."""
    blocks: list[str] = []
    inside = False
    current: list[str] = []
    for line in text.splitlines():
        if line.strip().startswith("```"):
            if inside:
                blocks.append("\n".join(current))
                current = []
            inside = not inside
            continue
        if inside:
            current.append(line)
    return blocks


def _literal_assign(source: str, name: str) -> object | None:
    """소스 문자열에서 `name = <리터럴>` 또는 `name: T = <리터럴>` 값을 literal_eval.

    모듈 레벨과 함수 내부(중첩) 할당을 모두 찾는다.
    """
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            targets, value = node.targets, node.value
        elif isinstance(node, ast.AnnAssign):
            targets, value = [node.target], node.value
        else:
            continue
        if value is None:
            continue
        for target in targets:
            if isinstance(target, ast.Name) and target.id == name:
                return ast.literal_eval(value)
    return None


def _skill_dict_literal(text: str, name: str) -> object:
    """SKILL.md 코드 블록 중 `name`을 정의한 블록을 찾아 literal_eval."""
    for block in _skill_code_blocks(text):
        if name in block:
            value = _literal_assign(block, name)
            if value is not None:
                return value
    raise AssertionError(f"SKILL.md 코드 블록에서 `{name}` 정의를 찾지 못했다")


# ── 픽스처 ────────────────────────────────────────────────────────────────────
@pytest.fixture(scope="module")
def skill_text() -> str:
    return SKILL_MD.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def channel_profiles() -> dict:
    data = yaml.safe_load(CHANNEL_PROFILES.read_text(encoding="utf-8"))
    return data["channels"]


@pytest.fixture(scope="module")
def edge_tts_source() -> str:
    return EDGE_TTS_CLIENT.read_text(encoding="utf-8")


# ── 테스트 ────────────────────────────────────────────────────────────────────
def test_voice_table_matches_channel_profiles(skill_text, channel_profiles):
    """스킬 음성 매핑 표가 channel_profiles.yaml의 `tts_voice`와 일치해야 한다."""
    skill_voices = _parse_voice_table(skill_text)
    yaml_voices = {ch: cfg["tts_voice"] for ch, cfg in channel_profiles.items()}

    assert set(skill_voices) == set(yaml_voices), (
        f"스킬 음성 표의 채널 목록이 YAML과 다르다 — 스킬: {sorted(skill_voices)}, YAML: {sorted(yaml_voices)}"
    )
    mismatches = {ch: (skill_voices[ch], yaml_voices[ch]) for ch in yaml_voices if skill_voices[ch] != yaml_voices[ch]}
    assert not mismatches, (
        "스킬 음성 표가 channel_profiles.yaml과 불일치 (스킬값, YAML값): "
        f"{mismatches} — SKILL.md를 YAML 기준으로 갱신할 것"
    )


def test_channel_prosody_matches_edge_tts_client(skill_text, edge_tts_source):
    """스킬의 `_CHANNEL_PROSODY` 표가 edge_tts_client.py와 일치해야 한다."""
    skill_prosody = _skill_dict_literal(skill_text, "_CHANNEL_PROSODY")
    code_prosody = _literal_assign(edge_tts_source, "_CHANNEL_PROSODY")

    assert code_prosody is not None, "edge_tts_client.py에서 `_CHANNEL_PROSODY`를 찾지 못함"
    assert skill_prosody == code_prosody, (
        f"SKILL.md의 `_CHANNEL_PROSODY`가 edge_tts_client.py와 불일치 — 스킬: {skill_prosody}, 코드: {code_prosody}"
    )


def test_pitch_hook_map_matches_edge_tts_client(skill_text, edge_tts_source):
    """스킬의 `pitch_hook_map`이 `_get_role_prosody` 내부 매핑과 일치해야 한다."""
    skill_map = _skill_dict_literal(skill_text, "pitch_hook_map")
    code_map = _literal_assign(edge_tts_source, "pitch_hook_map")

    assert code_map is not None, "edge_tts_client.py에서 `pitch_hook_map`을 찾지 못함"
    assert skill_map == code_map, (
        f"SKILL.md의 `pitch_hook_map`이 edge_tts_client.py와 불일치 — 스킬: {skill_map}, 코드: {code_map}"
    )
