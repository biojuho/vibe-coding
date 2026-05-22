"""Retention Report — 리텐션 시뮬레이션 결과를 사람이 읽는 리포트로.

`RetentionSimulatorStep` / `RetentionAutoFixer` / `retention_hints` 가
manifest 에 남긴 구조화 데이터를 크리에이터가 바로 읽을 수 있는 Markdown
리포트로 변환한다. 파이프라인 내부 데이터를 *제품 산출물* 로 만드는 마지막
계층 — 순수 함수라 어디서든(대시보드, CLI, 파일) 호출할 수 있다.

호출:
    from shorts_maker_v2.utils.retention_report import build_retention_report
    md = build_retention_report(manifest)  # manifest: dict 또는 JobManifest
"""

from __future__ import annotations

from typing import Any

_BAR_WIDTH = 20  # 리텐션 막대 그래프 폭(문자)


def _as_dict(manifest: Any) -> dict[str, Any]:
    """JobManifest / dict 어느 쪽이 와도 dict 로 정규화."""
    if isinstance(manifest, dict):
        return manifest
    to_dict = getattr(manifest, "to_dict", None)
    if callable(to_dict):
        result = to_dict()
        if isinstance(result, dict):
            return result
    # 마지막 폴백 — 속성 추출
    return {
        k: getattr(manifest, k, None)
        for k in (
            "title",
            "topic",
            "job_id",
            "retention_simulation",
            "retention_autofix",
            "retention_hints",
        )
    }


def _bar(fraction: float) -> str:
    """0..1 비율을 막대 그래프 문자열로."""
    fraction = max(0.0, min(1.0, float(fraction)))
    filled = round(fraction * _BAR_WIDTH)
    return "█" * filled + "░" * (_BAR_WIDTH - filled)


def _pct(value: Any, default: str = "—") -> str:
    """0..1 값을 퍼센트 문자열로. None/비정상은 default."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return default
    return f"{max(0.0, min(1.0, float(value))):.0%}"


def _verdict_icon(verdict: str) -> str:
    return {
        "pass": "✅",
        "degraded": "⚠️",
        "error": "❌",
        "improved": "✅",
        "no_improvement": "⚠️",
        "skipped": "⏭️",
    }.get(verdict, "•")


def build_retention_report(manifest: Any) -> str:
    """manifest 에서 리텐션 리포트 Markdown 을 생성한다.

    Args:
        manifest: `JobManifest` 인스턴스 또는 그 `to_dict()` 결과(dict).

    Returns:
        Markdown 문자열. 리텐션 데이터가 전혀 없으면 안내 문구를 담은
        짧은 리포트를 반환한다 (예외를 던지지 않는다).
    """
    data = _as_dict(manifest)
    title = str(data.get("title") or data.get("topic") or "(제목 없음)")
    job_id = str(data.get("job_id") or "")

    lines: list[str] = [f"# 📊 리텐션 리포트 — {title}"]
    if job_id:
        lines.append(f"`job_id: {job_id}`")
    lines.append("")

    sim = data.get("retention_simulation")
    autofix = data.get("retention_autofix")
    hints = data.get("retention_hints")

    if not isinstance(sim, dict):
        lines.append("> 합성 시청자 리텐션 시뮬레이션 데이터가 없습니다.")
        lines.append("> `project.retention_sim_enabled = true` 로 활성화하세요.")
        if isinstance(hints, dict):
            lines.append("")
            lines.extend(_hints_section(hints))
        return "\n".join(lines)

    lines.extend(_summary_section(sim))
    lines.append("")
    lines.extend(_curve_section(sim))
    lines.append("")
    lines.extend(_dropoff_section(sim))
    lines.append("")
    lines.extend(_persona_section(sim))

    if isinstance(autofix, dict):
        lines.append("")
        lines.extend(_autofix_section(autofix))

    if isinstance(hints, dict):
        lines.append("")
        lines.extend(_hints_section(hints))

    return "\n".join(lines)


def _summary_section(sim: dict[str, Any]) -> list[str]:
    verdict = str(sim.get("verdict", "—"))
    source = str(sim.get("source", "—"))
    src_label = {"llm": "LLM 시뮬레이션", "heuristic": "휴리스틱(LLM 폴백)"}.get(source, source)
    return [
        "## 예측 요약",
        "",
        f"- {_verdict_icon(verdict)} **판정**: `{verdict}`",
        f"- 🎯 **예측 리텐션**: {_pct(sim.get('predicted_retention'))} `{_bar(sim.get('predicted_retention') or 0.0)}`",
        f"- 🔁 **루핑(재시청) 확률**: {_pct(sim.get('loop_probability'))}",
        f"- 🧪 **산출 엔진**: {src_label}",
        f"- 💬 {sim.get('feedback') or '(요약 없음)'}",
    ]


def _curve_section(sim: dict[str, Any]) -> list[str]:
    curve = sim.get("retention_curve")
    lines = ["## 리텐션 곡선", ""]
    if not isinstance(curve, list) or not curve:
        lines.append("> 곡선 데이터 없음")
        return lines
    lines.append("| 씬 | 역할 | 잔류 | 그래프 | 이탈 사유 |")
    lines.append("|---|---|---|---|---|")
    for point in curve:
        if not isinstance(point, dict):
            continue
        remaining = point.get("viewers_remaining") or 0.0
        lines.append(
            f"| {point.get('scene_id', '?')} "
            f"| {point.get('role', '—')} "
            f"| {_pct(remaining)} "
            f"| `{_bar(remaining)}` "
            f"| {str(point.get('drop_reason', '') or '—')[:60]} |"
        )
    return lines


def _dropoff_section(sim: dict[str, Any]) -> list[str]:
    weakest = sim.get("weakest_scene_id")
    first_drop = sim.get("first_dropoff_scene_id")
    directive = sim.get("rewrite_directive") or "(없음)"
    return [
        "## 이탈 분석",
        "",
        f"- 📉 **첫 대량 이탈 씬**: {first_drop if first_drop is not None else '없음 (안정적)'}",
        f"- 🩹 **가장 약한 씬**: {weakest if weakest is not None else '—'}",
        f"- ✍️ **재작성 지시**: {directive}",
    ]


def _persona_section(sim: dict[str, Any]) -> list[str]:
    personas = sim.get("persona_breakdown")
    lines = ["## 페르소나별 이탈", ""]
    if not isinstance(personas, list) or not personas:
        lines.append("> 페르소나 데이터 없음")
        return lines
    lines.append("| 페르소나 | 이탈 씬 | 메모 |")
    lines.append("|---|---|---|")
    for persona in personas:
        if not isinstance(persona, dict):
            continue
        swiped = persona.get("swiped_at_scene")
        swiped_label = "끝까지 시청" if swiped is None else f"씬 {swiped}"
        lines.append(f"| {persona.get('name', '—')} | {swiped_label} | {str(persona.get('note', '') or '—')[:60]} |")
    return lines


def _autofix_section(autofix: dict[str, Any]) -> list[str]:
    verdict = str(autofix.get("verdict", "—"))
    before = autofix.get("before_retention")
    after = autofix.get("after_retention")
    lines = [
        "## 🔧 자가 치유 (closed-loop)",
        "",
        f"- {_verdict_icon(verdict)} **결과**: `{verdict}`",
        f"- 📈 **예측 리텐션 변화**: {_pct(before)} → {_pct(after)}",
    ]
    if autofix.get("applied_to_render"):
        lines.append("- 🚀 **재작성이 실제 렌더 대본에 반영됨** (pre_asset closed-loop)")
    elif verdict == "improved":
        lines.append("- 📝 재작성은 advisory 기록만 (post_asset — 다음 이터레이션 참고)")
    lines.append(f"- 💬 {autofix.get('feedback') or '(요약 없음)'}")
    rewrites = autofix.get("rewrites")
    if isinstance(rewrites, list) and rewrites:
        lines.append("")
        lines.append("| 씬 | 채택 | 전 → 후 |")
        lines.append("|---|---|---|")
        for rw in rewrites:
            if not isinstance(rw, dict):
                continue
            mark = "✅" if rw.get("accepted") else "❌"
            before_txt = str(rw.get("before", "") or "")[:40]
            after_txt = str(rw.get("after", "") or "")[:40]
            lines.append(f"| {rw.get('scene_id', '?')} | {mark} | {before_txt!r} → {after_txt!r} |")
    return lines


def _hints_section(hints: dict[str, Any]) -> list[str]:
    lines = ["## 💡 휴리스틱 힌트", ""]
    score = hints.get("estimated_retention_score")
    if score is not None:
        lines.append(f"- 추정 리텐션 점수: {_pct(score)}")
    loop = hints.get("loop_potential")
    if loop is not None:
        lines.append(f"- 루핑 잠재력: {_pct(loop)}")
    hint_list = hints.get("hints")
    if isinstance(hint_list, list) and hint_list:
        lines.append("")
        for hint in hint_list[:12]:
            if not isinstance(hint, dict):
                continue
            sev = {"critical": "🔴", "warning": "🟡", "info": "🔵"}.get(str(hint.get("severity")), "•")
            lines.append(f"- {sev} [{hint.get('category', '—')}] {hint.get('message', '')}")
    return lines
