"""Notion page upload and property update.

Mixin: NotionUploadMixin — upload(), update_page_properties() 및 헬퍼.
"""

from __future__ import annotations

import logging
from datetime import date, datetime
from typing import Any

from config import (
    ERROR_NOTION_SCHEMA_MISMATCH,
    ERROR_NOTION_UPLOAD_FAILED,
)
from pipeline.draft_contract import iter_publishable_drafts
from pipeline.publish_decision import decision_card_lines
from pipeline.regulation_checker import x_weighted_character_count

logger = logging.getLogger(__name__)


class NotionUploadMixin:
    """Notion 페이지 생성(upload) 및 속성 업데이트를 담당하는 Mixin.

    사전 조건: ensure_schema, _db_properties, props, client,
    _page_parent_payload, canonicalize_url, _register_url_in_cache 등이
    동일 클래스(NotionUploader)에 합쳐져 있어야 합니다.
    """

    REVIEW_FLAG_ALIASES = {
        "문자 깨짐 또는 비한글 비율 과다": "품질 이상",
        "너무 추상적": "근거 약함",
        "파생각 부족": "후속 반응 약함",
        "직장인 맥락 약함": "독자 핏 약함",
        "갈등 낚시 과다": "갈등 과열",
    }
    X_MAX_CHARS = 280
    CLEARABLE_EMPTY_RICH_TEXT_KEYS = {"x_publish_error"}

    def _prepare_property_payload(self, semantic_key: str, value: Any):
        """시맨틱 키 + 값 → Notion API 속성 payload 변환."""
        prop_name, prop_type = self._resolve_property_target(semantic_key, value)
        if not prop_name:
            return None, None

        payload = self._build_property_payload(prop_type, value)
        if payload is None:
            return None, None
        return prop_name, payload

    def _resolve_property_target(self, semantic_key: str, value: Any) -> tuple[str | None, str | None]:
        prop_name = self.props.get(semantic_key)
        if not prop_name or prop_name not in self._db_properties or value is None:
            return None, None
        if value == "" and semantic_key not in self.CLEARABLE_EMPTY_RICH_TEXT_KEYS:
            return None, None
        return prop_name, self._db_properties[prop_name]["type"]

    def _build_property_payload(self, prop_type: str | None, value: Any) -> dict[str, Any] | None:
        scalar_payload = self._build_scalar_property_payload(prop_type, value)
        if scalar_payload is not None:
            return scalar_payload
        if prop_type == "multi_select":
            return self._build_multi_select_property_payload(value)
        if prop_type == "date":
            return self._build_date_property_payload(value)
        return None

    @staticmethod
    def _build_scalar_property_payload(prop_type: str | None, value: Any) -> dict[str, Any] | None:
        if prop_type == "rich_text" and value == "":
            return {"rich_text": []}
        builders = {
            "title": lambda item: {"title": [{"text": {"content": str(item)[:1990]}}]},
            "rich_text": lambda item: {"rich_text": [{"text": {"content": str(item)[:1990]}}]},
            "checkbox": lambda item: {"checkbox": bool(item)},
            "number": lambda item: {"number": float(item)},
            "url": lambda item: {"url": str(item)},
            "status": lambda item: {"status": {"name": str(item)}},
            "select": lambda item: {"select": {"name": str(item)}},
        }
        builder = builders.get(prop_type or "")
        if not builder:
            return None
        return builder(value)

    @staticmethod
    def _build_multi_select_property_payload(value: Any) -> dict[str, Any] | None:
        if isinstance(value, (list, tuple, set)):
            names = [str(item).strip() for item in value if str(item).strip()]
        else:
            names = [str(value).strip()] if str(value).strip() else []
        if not names:
            return None
        return {"multi_select": [{"name": name[:100]} for name in names]}

    @staticmethod
    def _build_date_property_payload(value: Any) -> dict[str, Any]:
        if value == "now":
            iso_value = datetime.utcnow().isoformat()
        elif isinstance(value, datetime):
            iso_value = value.isoformat()
        elif isinstance(value, date):
            iso_value = value.isoformat()
        else:
            iso_value = str(value)
        return {"date": {"start": iso_value}}

    def _append_property_if_present(self, properties: dict[str, Any], semantic_key: str, value: Any):
        """값이 있으면 properties dict에 속성 payload 추가."""
        prop_name, payload = self._prepare_property_payload(semantic_key, value)
        if prop_name and payload is not None:
            properties[prop_name] = payload

    def _create_text_blocks(self, text: str):
        """긴 텍스트를 2000자 단위 Notion paragraph 블록으로 분할."""
        blocks = []
        for start in range(0, len(text), 2000):
            chunk = text[start : start + 2000]
            blocks.append(self._create_paragraph_block(chunk))
        return blocks

    @staticmethod
    def _rich_text(content: str, *, limit: int = 1990) -> list[dict[str, Any]]:
        return [{"type": "text", "text": {"content": str(content)[:limit]}}]

    def _create_paragraph_block(self, text: str) -> dict[str, Any]:
        return {
            "object": "block",
            "type": "paragraph",
            "paragraph": {"rich_text": self._rich_text(text)},
        }

    def _create_heading_block(self, level: int, text: str) -> dict[str, Any]:
        block_type = f"heading_{level}"
        return {
            "object": "block",
            "type": block_type,
            block_type: {"rich_text": self._rich_text(text)},
        }

    def _create_callout_block(self, text: str, emoji: str, color: str = "default") -> dict[str, Any]:
        return {
            "object": "block",
            "type": "callout",
            "callout": {
                "rich_text": self._rich_text(text),
                "icon": {"type": "emoji", "emoji": emoji},
                "color": color,
            },
        }

    def _create_toggle_block(
        self,
        title: str,
        children: list[dict[str, Any]],
        *,
        color: str = "gray_background",
    ) -> dict[str, Any]:
        return {
            "object": "block",
            "type": "toggle",
            "toggle": {
                "rich_text": self._rich_text(title),
                "color": color,
                "children": children,
            },
        }

    def _create_bulleted_list_blocks(self, lines: list[str]) -> list[dict[str, Any]]:
        blocks: list[dict[str, Any]] = []
        for line in lines:
            clean_line = str(line or "").strip()
            if not clean_line:
                continue
            for start in range(0, len(clean_line), 2000):
                chunk = clean_line[start : start + 2000]
                blocks.append(
                    {
                        "object": "block",
                        "type": "bulleted_list_item",
                        "bulleted_list_item": {"rich_text": self._rich_text(chunk)},
                    }
                )
        return blocks

    def _derive_publish_platforms(self, drafts: Any) -> list[str]:
        if not isinstance(drafts, dict):
            return ["X"]

        platforms: list[str] = []
        if drafts.get("twitter"):
            platforms.append("X")
        if drafts.get("threads"):
            platforms.append("Threads")
        if drafts.get("newsletter"):
            platforms.append("뉴스레터")
        if drafts.get("naver_blog"):
            platforms.append("블로그")
        return platforms

    def _list_publishable_draft_keys(self, drafts: Any) -> list[str]:
        if isinstance(drafts, dict):
            return [key for key, _value in iter_publishable_drafts(drafts)]
        if isinstance(drafts, str) and drafts.strip():
            return ["twitter"]
        return []

    def _extract_x_upload_parts(self, drafts: Any) -> dict[str, str]:
        if isinstance(drafts, dict):
            return {
                "body": str(drafts.get("twitter") or "").strip(),
                "reply": str(drafts.get("reply_text") or "").strip(),
            }
        return {"body": str(drafts or "").strip(), "reply": ""}

    def _build_x_upload_check_lines(self, drafts: Any) -> list[str]:
        parts = self._extract_x_upload_parts(drafts)
        body = parts["body"]
        if not body:
            return []

        char_count = x_weighted_character_count(body)
        length_status = "OK" if char_count <= self.X_MAX_CHARS else "초과"
        lines = [
            f"X 가중 글자 수: {char_count}/{self.X_MAX_CHARS}자 ({length_status})",
            "본문에는 원문 링크와 해시태그를 넣지 않고, 필요하면 첫 답글로 분리",
            "업로드 순서: X 본문 복사 → 이미지 첨부 → 게시 → 첫 답글에 원문/해시태그 추가",
        ]
        if parts["reply"]:
            lines.append(f"첫 답글 메모: {self._truncate_for_brief(parts['reply'], limit=120)}")
        return lines

    def _build_x_publish_ops_lines(self, post_data: dict[str, Any]) -> list[str]:
        lines = decision_card_lines(post_data.get("publish_decision"))
        scheduled_at = str(post_data.get("x_scheduled_at") or post_data.get("publish_scheduled_at") or "").strip()
        if scheduled_at:
            lines.append(f"예약 후보: {scheduled_at}")
        lines.append("게시 후 X Post URL과 X Published At을 채우고 상태를 Published로 변경")
        lines.append("실패하면 X Publish Error에 원문 오류를 남기고 상태를 Blocked로 변경")
        return lines

    def _extract_review_risk_flags(
        self, post_data: dict[str, Any], drafts: Any, analysis: dict[str, Any] | None
    ) -> list[str]:
        flags: list[str] = []

        for reason in (analysis or {}).get("hard_reject_reasons", []) or []:
            flags.append(self.REVIEW_FLAG_ALIASES.get(str(reason), str(reason)))

        qg_report = str(post_data.get("quality_gate_report", "") or "")
        if "클리셰" in qg_report and "클리셰 0건" not in qg_report:
            flags.append("클리셰")
        if "구체 장면 없음" in qg_report or "구체성 부족" in qg_report:
            flags.append("근거 약함")
        if "CTA" in qg_report and "CTA 포함" not in qg_report:
            flags.append("CTA 약함")
        if "날조" in qg_report or "팩트" in qg_report:
            flags.append("팩트 경계")

        if isinstance(drafts, dict) and not str(drafts.get("creator_take", "") or "").strip():
            flags.append("해석 약함")

        deduped: list[str] = []
        for flag in flags:
            clean_flag = str(flag).strip()
            if clean_flag and clean_flag not in deduped:
                deduped.append(clean_flag)
        return deduped[:5]

    @staticmethod
    def _truncate_for_brief(text: str, limit: int = 42) -> str:
        clean = " ".join(str(text or "").split())
        if len(clean) <= limit:
            return clean
        return clean[: limit - 1].rstrip() + "…"

    @staticmethod
    def _format_metric_value(value: Any) -> str:
        if isinstance(value, bool):
            return "Yes" if value else "No"
        if isinstance(value, int):
            return str(value)
        if isinstance(value, float):
            if value.is_integer():
                return str(int(value))
            return f"{value:.2f}".rstrip("0").rstrip(".")
        return str(value)

    def _format_metric_pairs(self, values: Any) -> str:
        if not isinstance(values, dict) or not values:
            return ""
        return ", ".join(
            f"{name}={self._format_metric_value(score)}" for name, score in values.items() if score not in (None, "")
        )

    @staticmethod
    def _metric_as_float(value: Any) -> float | None:
        if value in (None, ""):
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    def _build_selection_quality_verdict(self, drafts: dict[str, Any]) -> str:
        failures = self._metric_as_float(drafts.get("_quality_gate_failures"))
        warnings = self._metric_as_float(drafts.get("_quality_gate_warnings"))
        quality_score = self._metric_as_float(drafts.get("_quality_gate_score"))
        selection_score = self._metric_as_float(drafts.get("_best_of_n_selection_score"))
        similarity = self._metric_as_float(drafts.get("_max_semantic_similarity"))

        if failures and failures > 0:
            return f"수정 필요: 품질 게이트 실패 {self._format_metric_value(failures)}건"
        if quality_score is not None and quality_score < 8:
            return f"수정 필요: 게시 적합성 {self._format_metric_value(quality_score)}"
        if similarity is not None and similarity >= 0.75:
            return f"검수 후 게시: 최근 초안 유사도 {self._format_metric_value(similarity)}"
        if warnings and warnings > 0:
            return f"검수 후 게시: 경고 {self._format_metric_value(warnings)}건 확인"
        if (
            quality_score is not None
            and quality_score >= 9
            and (selection_score is None or selection_score >= 8)
            and (warnings in (None, 0))
        ):
            return "바로 게시 가능"
        return "검수 후 게시: 선택 근거 확인"

    def _build_selection_quality_summary(self, drafts: Any) -> str:
        if not isinstance(drafts, dict):
            return ""

        summary_parts: list[str] = []
        selection_score = drafts.get("_best_of_n_selection_score")
        if selection_score not in (None, ""):
            summary_parts.append(f"최종 선택점수 {self._format_metric_value(selection_score)}")

        quality_score = drafts.get("_quality_gate_score")
        if quality_score not in (None, ""):
            summary_parts.append(f"게시 적합성 {self._format_metric_value(quality_score)}")

        similarity = drafts.get("_max_semantic_similarity")
        if similarity not in (None, ""):
            summary_parts.append(f"최근 유사도 {self._format_metric_value(similarity)}(낮을수록 새로움)")

        failures = drafts.get("_quality_gate_failures")
        if failures not in (None, ""):
            summary_parts.append(f"실패 {self._format_metric_value(failures)}건")

        warnings = drafts.get("_quality_gate_warnings")
        if warnings not in (None, ""):
            summary_parts.append(f"경고 {self._format_metric_value(warnings)}건")

        if summary_parts:
            summary_parts.insert(0, self._build_selection_quality_verdict(drafts))

        return ", ".join(summary_parts)

    def _build_selection_edit_plan(
        self,
        drafts: Any,
        risk_flags: list[str],
        has_publishable_draft: bool,
    ) -> str:
        if not has_publishable_draft:
            return "초안 없음: 원문과 공감 앵커가 살아 있으면 재생성하고, 약하면 반려 사유만 남깁니다."
        if not isinstance(drafts, dict):
            return "검수 후 게시: 첫 문장 훅, 근거 보존, 톤 자연스러움만 확인한 뒤 복사합니다."

        failures = self._metric_as_float(drafts.get("_quality_gate_failures"))
        quality_score = self._metric_as_float(drafts.get("_quality_gate_score"))
        selection_score = self._metric_as_float(drafts.get("_best_of_n_selection_score"))
        similarity = self._metric_as_float(drafts.get("_max_semantic_similarity"))
        warnings = self._metric_as_float(drafts.get("_quality_gate_warnings"))

        if failures and failures > 0:
            return (
                f"품질 게이트 실패 {self._format_metric_value(failures)}건: "
                "진단 상세의 실패 항목을 먼저 고치고 다시 검수합니다."
            )
        if quality_score is not None and quality_score < 8:
            return (
                f"게시 적합성 {self._format_metric_value(quality_score)}: "
                "훅, 근거, 독자 행동 중 가장 약한 1개만 보강합니다."
            )
        if similarity is not None and similarity >= 0.75:
            return (
                f"최근 유사도 {self._format_metric_value(similarity)}: "
                "같은 결론은 유지하되 첫 문장 장면과 표현을 새로 씁니다."
            )
        if warnings and warnings > 0:
            if "팩트 경계" in risk_flags:
                return "경고 있음: 숫자, 댓글, 인용 해석을 원문 기준으로 낮춰 쓰고 과장 표현을 뺍니다."
            if "근거 약함" in risk_flags or "훅 약함" in risk_flags:
                return "경고 있음: 첫 문장에 원문 장면이나 근거를 먼저 넣어 추상도를 낮춥니다."
            if "독자 핏 약함" in risk_flags:
                return "경고 있음: 직장인 독자가 자기 상황과 비교할 문장 1개를 보강합니다."
            if "클리셰" in risk_flags:
                return "경고 있음: 상투어를 실제 사람이 말할 법한 구체 문장으로 바꿉니다."
            return "경고 있음: 경고 문장 1개만 고친 뒤 훅과 근거가 그대로 살아 있는지 확인합니다."
        if quality_score is not None and quality_score >= 9 and (selection_score is None or selection_score >= 8):
            return "바로 게시 가능: 오탈자만 보고 X 본문을 복사한 뒤 링크와 해시태그는 첫 답글로 분리합니다."
        return "검수 후 게시: 첫 문장 훅, 근거 보존, 톤 자연스러움만 확인한 뒤 복사합니다."

    @staticmethod
    def _format_fact_check_warning_counts(values: Any) -> str:
        if not isinstance(values, dict) or not values:
            return ""
        return ", ".join(
            f"{platform} {len(items)}건" for platform, items in values.items() if isinstance(items, list) and items
        )

    def _format_fact_check_warning_previews(self, values: Any) -> str:
        if not isinstance(values, dict) or not values:
            return ""
        summaries = []
        for platform, items in values.items():
            if isinstance(items, list) and items:
                preview = self._truncate_for_brief(items[0], limit=80)
                summaries.append(f"{platform} {len(items)}건 ({preview})")
        return "; ".join(summaries)

    def _build_emotion_profile_lines(self, emotion_profile: Any) -> list[str]:
        if not isinstance(emotion_profile, dict):
            return []

        lines: list[str] = []
        top_emotions = emotion_profile.get("top_emotions") or []
        if top_emotions:
            formatted = ", ".join(f"{name}={self._format_metric_value(score)}" for name, score in top_emotions if name)
            if formatted:
                lines.append(f"세부 감정 프로필: {formatted}")

        dominant_group = str(emotion_profile.get("dominant_group", "") or "").strip()
        if dominant_group:
            lines.append(f"지배 감정 그룹: {dominant_group}")
        return lines

    def _build_review_focus(
        self,
        analysis: dict[str, Any] | None,
        evidence_anchor: str,
        risk_flags: list[str],
        has_publishable_draft: bool,
    ) -> str:
        focus_items: list[str] = []

        if not has_publishable_draft:
            if evidence_anchor:
                focus_items.append(f"근거 앵커 '{self._truncate_for_brief(evidence_anchor)}' 자체가 살릴 만한지")
            if analysis and analysis.get("selection_summary"):
                focus_items.append("선정 이유만으로도 다시 써볼 가치가 있는지")
            focus_items.append("초안 없이도 운영자가 직접 쓰고 싶은 글감인지")
            return " / ".join(focus_items[:3])

        if evidence_anchor:
            focus_items.append(f"근거 앵커 '{self._truncate_for_brief(evidence_anchor)}'가 초안에 살아 있는지")
        if analysis and analysis.get("selection_summary"):
            focus_items.append("왜 이 글을 골랐는지 선정 이유가 납득되는지")
        if "팩트 경계" in risk_flags:
            focus_items.append("숫자·댓글·인용 해석이 과장되지 않았는지")
        elif "근거 약함" in risk_flags:
            focus_items.append("첫 문장에서 장면과 근거가 바로 잡히는지")
        elif "독자 핏 약함" in risk_flags:
            focus_items.append("직장인 독자가 자기 일처럼 느낄 만한지")
        elif "클리셰" in risk_flags:
            focus_items.append("문장이 뻔하지 않고 실제 사람 말처럼 들리는지")

        if not focus_items:
            focus_items.append("첫 문장 훅, 근거 보존, 톤 자연스러움 이 3가지만 보면 됩니다")

        return " / ".join(focus_items[:3])

    def _build_feedback_request(self, risk_flags: list[str], has_publishable_draft: bool) -> str:
        if not has_publishable_draft:
            return (
                "초안이 비어 있습니다. 승인/보류/반려 중 하나만 고른 뒤, "
                "살릴 거면 재생성 또는 직접 작성, 아니면 '반려 사유'만 체크해주세요."
            )

        primary_check = "승인/보류/반려 중 하나만 고르고, 가장 먼저 고칠 1개만 남겨주세요"
        if "팩트 경계" in risk_flags:
            secondary = "특히 과장되거나 추론이 튄 문장이 있으면 바로 표시해주세요"
        elif "근거 약함" in risk_flags or "훅 약함" in risk_flags:
            secondary = "특히 첫 문장이 약한지, 근거가 흐린지 봐주세요"
        elif "클리셰" in risk_flags:
            secondary = "특히 기계적으로 들리는 문장이 있으면 표시해주세요"
        else:
            secondary = "문제 없으면 살릴 포인트 1개만 적어주세요"
        return f"{primary_check}. {secondary}. 반려면 '반려 사유' 컬럼만 체크해도 충분합니다."

    def _build_action_steps(self, has_publishable_draft: bool) -> list[str]:
        if has_publishable_draft:
            return [
                "지금 할 일",
                "1. '검토 포인트'와 '피드백 요청'만 먼저 읽습니다.",
                "2. 아래 초안을 보고 승인됨 / 보류 / 반려 중 하나로 상태를 고릅니다.",
                "3. 승인이라면 필요한 채널용으로 조금만 다듬고, 반려라면 '반려 사유'만 체크합니다.",
            ]

        return [
            "지금 할 일",
            "1. 규제 리포트의 '초안 없음' 경고는 규제 위반이 아니라 초안 비어 있음 안내입니다.",
            "2. 원문과 공감 앵커가 살릴 만하면 파이프라인을 다시 돌리거나 초안을 직접 씁니다.",
            "3. 살릴 가치가 낮으면 '반려 사유'만 체크하고 반려로 끝냅니다.",
        ]

    def _build_review_brief(
        self, post_data: dict[str, Any], drafts: Any, analysis: dict[str, Any] | None
    ) -> dict[str, Any]:
        creator_take = ""
        if isinstance(drafts, dict):
            creator_take = str(drafts.get("creator_take", "") or "").strip()

        evidence_anchor = str((analysis or {}).get("empathy_anchor", "") or "").strip()
        risk_flags = self._extract_review_risk_flags(post_data, drafts, analysis)
        publishable_draft_keys = self._list_publishable_draft_keys(drafts)
        has_publishable_draft = bool(publishable_draft_keys)
        publish_platforms = self._derive_publish_platforms(drafts)

        return {
            "creator_take": creator_take,
            "evidence_anchor": evidence_anchor,
            "risk_flags": risk_flags,
            "has_publishable_draft": has_publishable_draft,
            "selection_quality_summary": self._build_selection_quality_summary(drafts),
            "edit_plan": self._build_selection_edit_plan(drafts, risk_flags, has_publishable_draft),
            "review_focus": self._build_review_focus(analysis, evidence_anchor, risk_flags, has_publishable_draft),
            "feedback_request": self._build_feedback_request(risk_flags, has_publishable_draft),
            "action_steps": self._build_action_steps(has_publishable_draft),
            "publish_platforms": publish_platforms,
        }

    def _build_summary_metric_lines(self, post_data: dict[str, Any], analysis: dict[str, Any] | None) -> list[str]:
        metric_lines: list[str] = []

        if analysis and analysis.get("final_rank_score") not in (None, ""):
            metric_lines.append(f"최종 랭크 점수: {self._format_metric_value(analysis['final_rank_score'])}")

        editorial_avg_score = post_data.get("editorial_avg_score")
        if editorial_avg_score not in (None, ""):
            metric_lines.append(f"에디토리얼 평균 점수: {self._format_metric_value(editorial_avg_score)}")

        quality_gate_retries = post_data.get("quality_gate_retries")
        if quality_gate_retries not in (None, "", 0):
            metric_lines.append(f"품질 재시도: {self._format_metric_value(quality_gate_retries)}회")

        quality_gate_scores = self._format_metric_pairs(post_data.get("quality_gate_scores"))
        if quality_gate_scores:
            metric_lines.append(f"품질 점수: {quality_gate_scores}")

        warning_summary = self._format_fact_check_warning_counts(post_data.get("fact_check_warnings"))
        if warning_summary:
            metric_lines.append(f"팩트 체크 경고: {warning_summary}")

        return metric_lines

    def _build_content_intelligence_lines(
        self, post_data: dict[str, Any], analysis: dict[str, Any] | None
    ) -> list[str]:
        if not analysis:
            return []

        lines = [
            f"토픽 클러스터: {analysis.get('topic_cluster', '기타')}",
            f"훅 타입: {analysis.get('hook_type', '공감형')}",
            f"감정 축/선: {analysis.get('emotion_axis', '공감')} / {analysis.get('emotion_lane', '')}",
            f"대상 독자: {analysis.get('audience_fit', '범용')}",
            f"선정 이유: {analysis.get('selection_summary', '')}",
            f"독자 욕구: {analysis.get('audience_need', '')}",
            f"추천 스타일: {analysis.get('recommended_draft_type', '공감형')}",
        ]

        lines.extend(self._build_emotion_profile_lines(post_data.get("emotion_profile")))

        spinoff_angle = str(analysis.get("spinoff_angle", "") or "").strip()
        if spinoff_angle:
            lines.append(f"파생각: {spinoff_angle}")

        for label, key in (
            ("에디토리얼 점수", "editorial_scores"),
            ("가독성 점수", "readability_scores"),
            ("품질 게이트 점수", "quality_gate_scores"),
        ):
            formatted = self._format_metric_pairs(post_data.get(key))
            if formatted:
                lines.append(f"{label}: {formatted}")

        quality_gate_retries = post_data.get("quality_gate_retries")
        if quality_gate_retries not in (None, "", 0):
            lines.append(f"품질 재시도: {self._format_metric_value(quality_gate_retries)}회")

        warning_previews = self._format_fact_check_warning_previews(post_data.get("fact_check_warnings"))
        if warning_previews:
            lines.append(f"팩트 체크 경고: {warning_previews}")

        draft_generation_error = str(post_data.get("draft_generation_error", "") or "").strip()
        if draft_generation_error:
            lines.append(f"초안 생성 오류: {self._truncate_for_brief(draft_generation_error, limit=140)}")

        return [line for line in lines if line.split(":", 1)[-1].strip()]

    def _build_summary_section_blocks(
        self,
        post_data: dict[str, Any],
        review_brief: dict[str, Any],
        analysis: dict[str, Any] | None,
        draft_generation_error: str,
        drafts: Any,
    ) -> list[dict[str, Any]]:
        if not analysis:
            return []

        blocks = [
            {"object": "block", "type": "divider", "divider": {}},
            self._create_heading_block(2, "검토 요약"),
            self._create_callout_block(
                "\n".join(review_brief["action_steps"]),
                "📝" if review_brief["has_publishable_draft"] else "⚠️",
                "green_background" if review_brief["has_publishable_draft"] else "yellow_background",
            ),
        ]

        if review_brief["creator_take"]:
            blocks.append(
                self._create_callout_block(
                    f"한줄 해석: {review_brief['creator_take']}",
                    "🧭",
                    "blue_background",
                )
            )

        summary_lines = [
            f"검토 포인트: {review_brief['review_focus']}",
            f"피드백 요청: {review_brief['feedback_request']}",
        ]
        if review_brief["evidence_anchor"]:
            summary_lines.append(f"근거 앵커: {review_brief['evidence_anchor']}")
        if review_brief["risk_flags"]:
            summary_lines.append(f"위험 신호: {', '.join(review_brief['risk_flags'])}")
        if review_brief["publish_platforms"]:
            summary_lines.append(f"권장 채널: {', '.join(review_brief['publish_platforms'])}")
        if review_brief.get("selection_quality_summary"):
            summary_lines.append(f"선택 품질: {review_brief['selection_quality_summary']}")
        if review_brief.get("edit_plan"):
            summary_lines.append(f"수정 플랜: {review_brief['edit_plan']}")
        summary_lines.extend(self._build_x_upload_check_lines(drafts))
        if draft_generation_error:
            summary_lines.append(f"초안 생성 오류: {self._truncate_for_brief(draft_generation_error, limit=140)}")
        summary_lines.extend(self._build_summary_metric_lines(post_data, analysis))

        blocks.extend(self._create_bulleted_list_blocks(summary_lines))
        return blocks

    def _build_x_upload_card_blocks(self, drafts: Any, post_data: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        parts = self._extract_x_upload_parts(drafts)
        body = parts["body"]
        if not body:
            return []

        blocks: list[dict[str, Any]] = [
            {"object": "block", "type": "divider", "divider": {}},
            self._create_heading_block(2, "X 업로드 카드"),
            self._create_callout_block(
                "아래 X 본문을 그대로 복사하고, 링크와 해시태그는 첫 답글로 분리합니다.",
                "✍️",
                "green_background",
            ),
            self._create_heading_block(3, "X 본문"),
            *self._create_text_blocks(body),
        ]
        if parts["reply"]:
            blocks.extend(
                [
                    self._create_heading_block(3, "첫 답글 / 출처 메모"),
                    *self._create_text_blocks(parts["reply"]),
                ]
            )
        blocks.append(self._create_heading_block(3, "게시 운영"))
        blocks.extend(self._create_bulleted_list_blocks(self._build_x_publish_ops_lines(post_data or {})))
        blocks.extend(self._create_bulleted_list_blocks(self._build_x_upload_check_lines(drafts)))
        return blocks

    def _build_draft_section_blocks(self, drafts: Any) -> list[dict[str, Any]]:
        if not drafts:
            return []

        draft_blocks: list[dict[str, Any]] = []

        if isinstance(drafts, dict):
            if drafts.get("threads"):
                draft_blocks.append(self._create_heading_block(3, "Threads 초안"))
                draft_blocks.extend(self._create_text_blocks(drafts["threads"]))
            if drafts.get("newsletter"):
                draft_blocks.append(self._create_heading_block(3, "뉴스레터 초안"))
                draft_blocks.extend(self._create_text_blocks(drafts["newsletter"]))
            if drafts.get("naver_blog"):
                draft_blocks.append(self._create_heading_block(3, "네이버 블로그 초안"))
                draft_blocks.extend(self._create_text_blocks(drafts["naver_blog"]))
        else:
            return []

        if not draft_blocks:
            return []

        return [
            {"object": "block", "type": "divider", "divider": {}},
            self._create_heading_block(2, "보조 채널 초안"),
            *draft_blocks,
        ]

    def _build_diagnostic_section_blocks(
        self,
        post_data: dict[str, Any],
        review_brief: dict[str, Any],
        analysis: dict[str, Any] | None,
    ) -> list[dict[str, Any]]:
        diagnostic_children: list[dict[str, Any]] = []
        intelligence_lines = self._build_content_intelligence_lines(post_data, analysis)
        if intelligence_lines:
            diagnostic_children.append(self._create_heading_block(3, "콘텐츠 인텔리전스"))
            if review_brief["evidence_anchor"]:
                diagnostic_children.append(
                    self._create_callout_block(
                        f"공감 앵커 (킬링포인트): {review_brief['evidence_anchor']}",
                        "🎯",
                        "blue_background",
                    )
                )
            if analysis and analysis.get("spinoff_angle"):
                diagnostic_children.append(
                    self._create_callout_block(
                        f"파생각 (Spinoff): {analysis['spinoff_angle']}",
                        "💡",
                        "yellow_background",
                    )
                )
            diagnostic_children.extend(self._create_bulleted_list_blocks(intelligence_lines))

        qg_report = str(post_data.get("quality_gate_report", "") or "").strip()
        if qg_report:
            diagnostic_children.append(self._create_heading_block(3, "품질 검증 리포트"))
            diagnostic_children.extend(self._create_text_blocks(qg_report))

        regulation_report = str(post_data.get("regulation_report", "") or "").strip()
        if regulation_report:
            diagnostic_children.append(self._create_heading_block(3, "규제 검증 리포트"))
            diagnostic_children.extend(self._create_text_blocks(regulation_report))

        if not diagnostic_children:
            return []

        return [
            {"object": "block", "type": "divider", "divider": {}},
            self._create_heading_block(2, "진단 상세"),
            self._create_toggle_block("진단 펼치기", diagnostic_children),
        ]

    def _build_raw_source_section_blocks(
        self, post_data: dict[str, Any], screenshot_url: str | None
    ) -> list[dict[str, Any]]:
        raw_children: list[dict[str, Any]] = []

        if screenshot_url:
            raw_children.append(self._create_heading_block(3, "원문 스크린샷"))
            raw_children.append(
                {
                    "object": "block",
                    "type": "image",
                    "image": {"type": "external", "external": {"url": screenshot_url}},
                }
            )

        raw_content = str(post_data.get("content", "") or "").strip()
        if raw_content:
            raw_children.append(self._create_heading_block(3, "원문 내용"))
            raw_children.extend(self._create_text_blocks(raw_content))

        if not raw_children:
            return []

        return [
            {"object": "block", "type": "divider", "divider": {}},
            self._create_heading_block(2, "원문"),
            self._create_toggle_block("원문 펼치기", raw_children),
        ]

    def _build_nlm_article_blocks(self, nlm_article: str) -> list[dict[str, Any]]:
        try:
            import importlib.util as _ilu
            import pathlib as _pl

            _uploader_path = (
                _pl.Path(__file__).resolve().parents[4] / "workspace" / "execution" / "notion_article_uploader.py"
            )
            if not _uploader_path.exists():
                raise FileNotFoundError(_uploader_path)
            _spec = _ilu.spec_from_file_location("notion_article_uploader", str(_uploader_path))
            _uploader_mod = _ilu.module_from_spec(_spec)
            _spec.loader.exec_module(_uploader_mod)
            return list(_uploader_mod.markdown_to_notion_blocks(nlm_article))
        except Exception as exc:
            logger.debug("[NLM Article] 블록 변환 실패, plain text 폴백: %s", exc)
            return self._create_text_blocks(nlm_article)

    def _build_asset_section_blocks(
        self, post_data: dict[str, Any], properties: dict[str, Any]
    ) -> list[dict[str, Any]]:
        asset_children: list[dict[str, Any]] = []

        nlm_article = str(post_data.get("nlm_article", "") or "").strip()
        if nlm_article:
            asset_children.append(self._create_heading_block(3, "AI 자동 아티클"))
            asset_children.extend(self._build_nlm_article_blocks(nlm_article))

        nlm_infographic = str(post_data.get("nlm_infographic_url", "") or "").strip()
        nlm_slides = str(post_data.get("nlm_slides_path", "") or "").strip()
        if nlm_infographic or nlm_slides:
            asset_children.append(self._create_heading_block(3, "NotebookLM 리서치 자산"))
            if nlm_infographic:
                asset_children.append(
                    {
                        "object": "block",
                        "type": "image",
                        "image": {"type": "external", "external": {"url": nlm_infographic}},
                    }
                )
                self._append_property_if_present(properties, "nlm_infographic_url", nlm_infographic)
            if nlm_slides:
                asset_children.extend(self._create_text_blocks(f"📊 슬라이드 파일: {nlm_slides}"))

        if not asset_children:
            return []

        return [
            {"object": "block", "type": "divider", "divider": {}},
            self._create_heading_block(2, "부가 산출물"),
            self._create_toggle_block("부가 산출물 펼치기", asset_children),
        ]

    def _build_upload_memo(
        self,
        post_data: dict[str, Any],
        canonical_url: str,
        review_brief: dict[str, Any],
        analysis: dict[str, Any] | None,
        draft_generation_error: str,
    ) -> str:
        memo_parts = [f"원본 링크: {canonical_url or post_data.get('url', '')}"]
        if analysis and analysis.get("selection_summary"):
            memo_parts.append(f"선정 요약: {analysis['selection_summary']}")
        if review_brief["creator_take"]:
            memo_parts.append(f"운영자 해석: {review_brief['creator_take']}")
        if review_brief["risk_flags"]:
            memo_parts.append(f"위험 신호: {', '.join(review_brief['risk_flags'])}")
        if review_brief["publish_platforms"]:
            memo_parts.append(f"권장 채널: {', '.join(review_brief['publish_platforms'])}")
        if review_brief.get("selection_quality_summary"):
            memo_parts.append(f"선택 품질: {review_brief['selection_quality_summary']}")
        if review_brief.get("edit_plan"):
            memo_parts.append(f"수정 플랜: {review_brief['edit_plan']}")
        if analysis and analysis.get("final_rank_score") not in (None, ""):
            memo_parts.append(f"최종 랭크: {self._format_metric_value(analysis['final_rank_score'])}")
        editorial_avg_score = post_data.get("editorial_avg_score")
        if editorial_avg_score not in (None, ""):
            memo_parts.append(f"에디토리얼 평균: {self._format_metric_value(editorial_avg_score)}")
        if draft_generation_error:
            memo_parts.append(f"초안 생성 오류: {self._truncate_for_brief(draft_generation_error, limit=140)}")
        return "\n".join(memo_parts)

    def _append_x_publish_properties(self, properties: dict[str, Any], post_data: dict[str, Any]) -> None:
        decision = post_data.get("publish_decision")
        decision_status = "Needs Edit"
        if isinstance(decision, dict) and decision.get("action") == "PUBLISH":
            decision_status = "Ready to Post"
        self._append_property_if_present(
            properties,
            "x_publish_status",
            post_data.get("x_publish_status") or decision_status,
        )
        self._append_property_if_present(
            properties,
            "x_scheduled_at",
            post_data.get("x_scheduled_at") or post_data.get("publish_scheduled_at"),
        )
        self._append_property_if_present(properties, "x_post_url", post_data.get("x_post_url"))
        self._append_property_if_present(properties, "x_published_at", post_data.get("x_published_at"))
        self._append_property_if_present(properties, "x_publish_error", post_data.get("x_publish_error"))

    def _append_draft_body_properties(self, properties: dict[str, Any], drafts: Any) -> None:
        if isinstance(drafts, dict):
            self._append_property_if_present(properties, "tweet_body", drafts.get("twitter"))
            self._append_property_if_present(properties, "reply_text", drafts.get("reply_text"))
            self._append_property_if_present(properties, "threads_body", drafts.get("threads"))
            self._append_property_if_present(properties, "blog_body", drafts.get("naver_blog"))
            return
        self._append_property_if_present(properties, "tweet_body", drafts)

    def _append_analysis_properties(self, properties: dict[str, Any], analysis: dict[str, Any] | None) -> None:
        if not analysis:
            return
        analysis_mapping = {
            "topic_cluster": analysis.get("topic_cluster"),
            "emotion_axis": analysis.get("emotion_axis"),
            "final_rank_score": analysis.get("final_rank_score"),
        }
        for semantic_key, value in analysis_mapping.items():
            self._append_property_if_present(properties, semantic_key, value)

    def _build_upload_properties(
        self,
        post_data: dict[str, Any],
        canonical_url: str,
        review_brief: dict[str, Any],
        analysis: dict[str, Any] | None,
        drafts: Any,
        draft_generation_error: str,
    ) -> dict[str, Any]:
        properties: dict[str, Any] = {}
        self._append_property_if_present(properties, "title", post_data.get("title", ""))
        self._append_property_if_present(
            properties,
            "memo",
            self._build_upload_memo(post_data, canonical_url, review_brief, analysis, draft_generation_error),
        )
        self._append_property_if_present(properties, "status", post_data.get("status") or self.status_default)
        self._append_property_if_present(properties, "date", datetime.now().date())
        self._append_property_if_present(properties, "url", canonical_url)
        self._append_property_if_present(properties, "source", post_data.get("source", "blind"))
        self._append_property_if_present(properties, "creator_take", review_brief["creator_take"])
        self._append_property_if_present(properties, "review_focus", review_brief["review_focus"])
        self._append_property_if_present(properties, "feedback_request", review_brief["feedback_request"])
        self._append_property_if_present(properties, "risk_flags", review_brief["risk_flags"])
        self._append_property_if_present(properties, "evidence_anchor", review_brief["evidence_anchor"])
        self._append_property_if_present(properties, "publish_platforms", review_brief["publish_platforms"])
        if "X" in review_brief["publish_platforms"]:
            self._append_x_publish_properties(properties, post_data)
        self._append_draft_body_properties(properties, drafts)
        self._append_analysis_properties(properties, analysis)
        return properties

    def _build_initial_upload_children(self, image_url: str | None) -> list[dict[str, Any]]:
        if not image_url:
            return []
        return [
            {
                "object": "block",
                "type": "image",
                "image": {"type": "external", "external": {"url": image_url}},
            }
        ]

    def _append_regulation_status_property(self, properties: dict[str, Any], post_data: dict[str, Any]) -> None:
        regulation_report = post_data.get("regulation_report", "")
        if not regulation_report:
            return
        self._append_property_if_present(
            properties,
            "regulation_status",
            "통과" if "전체 플랫폼 규제 검증 통과" in regulation_report else "경고",
        )

    def _build_upload_children(
        self,
        post_data: dict[str, Any],
        image_url: str | None,
        drafts: Any,
        analysis: dict[str, Any] | None,
        screenshot_url: str | None,
        review_brief: dict[str, Any],
        draft_generation_error: str,
        properties: dict[str, Any],
    ) -> list[dict[str, Any]]:
        children = self._build_initial_upload_children(image_url)
        self._append_regulation_status_property(properties, post_data)
        children.extend(
            self._build_summary_section_blocks(
                post_data,
                review_brief,
                analysis,
                draft_generation_error,
                drafts,
            )
        )
        children.extend(self._build_x_upload_card_blocks(drafts, post_data))
        children.extend(self._build_draft_section_blocks(drafts))
        children.extend(self._build_diagnostic_section_blocks(post_data, review_brief, analysis))
        children.extend(self._build_raw_source_section_blocks(post_data, screenshot_url))
        children.extend(self._build_asset_section_blocks(post_data, properties))
        return children

    async def upload(self, post_data, image_url, drafts, analysis=None, screenshot_url=None):
        """Notion DB에 새 페이지 생성 (본문 + 초안 + 분석 결과)."""
        if not await self.ensure_schema():
            return None

        logger.info("Uploading to Notion: %s", post_data.get("title", "(untitled)"))
        try:
            canonical_url = self.canonicalize_url(post_data.get("url", ""))
            review_brief = self._build_review_brief(post_data, drafts, analysis)
            draft_generation_error = str(post_data.get("draft_generation_error", "") or "").strip()
            properties = self._build_upload_properties(
                post_data,
                canonical_url,
                review_brief,
                analysis,
                drafts,
                draft_generation_error,
            )
            children = self._build_upload_children(
                post_data,
                image_url,
                drafts,
                analysis,
                screenshot_url,
                review_brief,
                draft_generation_error,
                properties,
            )

            response = await self._safe_notion_call(
                self.client.pages.create,
                parent=self._page_parent_payload(),
                properties=properties,
                children=children,
            )
            self._clear_error()
            # 업로드 성공 즉시 캐시에 등록 (동일 세션 내 중복 방지)
            self._register_url_in_cache(post_data.get("url", ""))
            return response.get("url", "Unknown URL"), response.get("id")
        except Exception as exc:
            err_str = str(exc)
            if "is not a property that exists" in err_str:
                self._set_error(
                    ERROR_NOTION_SCHEMA_MISMATCH,
                    "Notion 속성명이 실제 DB와 일치하지 않습니다. notion.properties 또는 NOTION_PROP_* 값을 확인하세요. "
                    f"원본 에러: {err_str}",
                )
            else:
                self._set_error(ERROR_NOTION_UPLOAD_FAILED, f"Failed to upload to Notion: {err_str}")
            return None

    async def update_page_properties(self, page_id: str, updates: dict):
        """기존 페이지의 속성을 업데이트."""
        if not await self.ensure_schema():
            return None
        try:
            properties = {}
            for semantic_key, value in updates.items():
                prop_name, payload = self._prepare_property_payload(semantic_key, value)
                if prop_name and payload is not None:
                    properties[prop_name] = payload
            if not properties:
                return True
            await self._safe_notion_call(self.client.pages.update, page_id=page_id, properties=properties)
            logger.info("Successfully updated properties for Notion page %s", page_id)
            return True
        except Exception as exc:
            err_str = str(exc)
            if "is not a property that exists" in err_str:
                self._set_error(
                    ERROR_NOTION_SCHEMA_MISMATCH,
                    f"Notion property update schema mismatch. Original error: {err_str}",
                )
            else:
                self._set_error(
                    ERROR_NOTION_UPLOAD_FAILED,
                    f"Failed to update Notion page properties: {err_str}",
                )
            logger.error("Failed to update Notion page properties: %s", exc)
            return False
