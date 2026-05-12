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

    def _prepare_property_payload(self, semantic_key: str, value: Any):
        """시맨틱 키 + 값 → Notion API 속성 payload 변환."""
        prop_name = self.props.get(semantic_key)
        if not prop_name or prop_name not in self._db_properties or value in (None, ""):
            return None, None

        prop_type = self._db_properties[prop_name]["type"]
        if prop_type == "title":
            return prop_name, {"title": [{"text": {"content": str(value)[:1990]}}]}
        if prop_type == "rich_text":
            return prop_name, {"rich_text": [{"text": {"content": str(value)[:1990]}}]}
        if prop_type == "checkbox":
            return prop_name, {"checkbox": bool(value)}
        if prop_type == "number":
            return prop_name, {"number": float(value)}
        if prop_type == "url":
            return prop_name, {"url": str(value)}
        if prop_type == "status":
            return prop_name, {"status": {"name": str(value)}}
        if prop_type == "select":
            return prop_name, {"select": {"name": str(value)}}
        if prop_type == "multi_select":
            if isinstance(value, (list, tuple, set)):
                names = [str(item).strip() for item in value if str(item).strip()]
            else:
                names = [str(value).strip()] if str(value).strip() else []
            if not names:
                return None, None
            return prop_name, {"multi_select": [{"name": name[:100]} for name in names]}
        if prop_type == "date":
            if value == "now":
                iso_value = datetime.utcnow().isoformat()
            elif isinstance(value, datetime):
                iso_value = value.isoformat()
            elif isinstance(value, date):
                iso_value = value.isoformat()
            else:
                iso_value = str(value)
            return prop_name, {"date": {"start": iso_value}}
        return None, None

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
            blocks.append(
                {
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {"rich_text": [{"type": "text", "text": {"content": chunk}}]},
                }
            )
        return blocks

    def _derive_publish_platforms(self, drafts: Any) -> list[str]:
        if not isinstance(drafts, dict):
            return ["숏폼"]

        platforms: list[str] = []
        if drafts.get("twitter"):
            platforms.append("숏폼")
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
            "review_focus": self._build_review_focus(analysis, evidence_anchor, risk_flags, has_publishable_draft),
            "feedback_request": self._build_feedback_request(risk_flags, has_publishable_draft),
            "action_steps": self._build_action_steps(has_publishable_draft),
            "publish_platforms": publish_platforms,
        }

    async def upload(self, post_data, image_url, drafts, analysis=None, screenshot_url=None):
        """Notion DB에 새 페이지 생성 (본문 + 초안 + 분석 결과)."""
        if not await self.ensure_schema():
            return None

        logger.info("Uploading to Notion: %s", post_data.get("title", "(untitled)"))
        try:
            canonical_url = self.canonicalize_url(post_data.get("url", ""))
            properties: dict[str, Any] = {}
            review_brief = self._build_review_brief(post_data, drafts, analysis)
            draft_generation_error = str(post_data.get("draft_generation_error", "") or "").strip()

            self._append_property_if_present(properties, "title", post_data.get("title", ""))

            # memo: 원본 링크 + 핵심 판단 정보만 간결하게 유지
            memo_parts = [f"원본 링크: {canonical_url or post_data.get('url', '')}"]
            if analysis and analysis.get("selection_summary"):
                memo_parts.append(f"선정 요약: {analysis['selection_summary']}")
            if review_brief["creator_take"]:
                memo_parts.append(f"운영자 해석: {review_brief['creator_take']}")
            if review_brief["risk_flags"]:
                memo_parts.append(f"위험 신호: {', '.join(review_brief['risk_flags'])}")
            if draft_generation_error:
                memo_parts.append(f"초안 생성 오류: {self._truncate_for_brief(draft_generation_error, limit=140)}")
            self._append_property_if_present(properties, "memo", "\n".join(memo_parts))

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

            if isinstance(drafts, dict):
                self._append_property_if_present(properties, "tweet_body", drafts.get("twitter"))
                self._append_property_if_present(properties, "reply_text", drafts.get("reply_text"))
                self._append_property_if_present(properties, "threads_body", drafts.get("threads"))
                self._append_property_if_present(properties, "blog_body", drafts.get("naver_blog"))
            else:
                self._append_property_if_present(properties, "tweet_body", drafts)

            if analysis:
                analysis_mapping = {
                    "topic_cluster": analysis.get("topic_cluster"),
                    "emotion_axis": analysis.get("emotion_axis"),
                    "final_rank_score": analysis.get("final_rank_score"),
                }
                for semantic_key, value in analysis_mapping.items():
                    self._append_property_if_present(properties, semantic_key, value)

            children = []
            if image_url:
                children.append(
                    {
                        "object": "block",
                        "type": "image",
                        "image": {"type": "external", "external": {"url": image_url}},
                    }
                )

            if analysis:
                children.append({"object": "block", "type": "divider", "divider": {}})
                children.append(
                    {
                        "object": "block",
                        "type": "heading_2",
                        "heading_2": {"rich_text": [{"type": "text", "text": {"content": "검토 브리프"}}]},
                    }
                )

                children.append(
                    {
                        "object": "block",
                        "type": "callout",
                        "callout": {
                            "rich_text": [
                                {
                                    "type": "text",
                                    "text": {"content": "\n".join(review_brief["action_steps"])},
                                }
                            ],
                            "icon": {
                                "type": "emoji",
                                "emoji": "📝" if review_brief["has_publishable_draft"] else "⚠️",
                            },
                            "color": "green_background"
                            if review_brief["has_publishable_draft"]
                            else "yellow_background",
                        },
                    }
                )

                if review_brief["creator_take"]:
                    children.append(
                        {
                            "object": "block",
                            "type": "callout",
                            "callout": {
                                "rich_text": [
                                    {"type": "text", "text": {"content": f"한줄 해석: {review_brief['creator_take']}"}}
                                ],
                                "icon": {"type": "emoji", "emoji": "🧭"},
                                "color": "blue_background",
                            },
                        }
                    )

                brief_lines = [
                    f"검토 포인트: {review_brief['review_focus']}",
                    f"피드백 요청: {review_brief['feedback_request']}",
                ]
                if review_brief["evidence_anchor"]:
                    brief_lines.append(f"근거 앵커: {review_brief['evidence_anchor']}")
                if review_brief["risk_flags"]:
                    brief_lines.append(f"위험 신호: {', '.join(review_brief['risk_flags'])}")
                if review_brief["publish_platforms"]:
                    brief_lines.append(f"권장 채널: {', '.join(review_brief['publish_platforms'])}")
                if draft_generation_error:
                    brief_lines.append(f"초안 생성 오류: {self._truncate_for_brief(draft_generation_error, limit=140)}")
                children.extend(self._create_text_blocks("\n".join(brief_lines)))

                children.append({"object": "block", "type": "divider", "divider": {}})
                children.append(
                    {
                        "object": "block",
                        "type": "heading_2",
                        "heading_2": {
                            "rich_text": [{"type": "text", "text": {"content": "🧠 콘텐츠 인텔리전스 (V2.0)"}}]
                        },
                    }
                )

                # ── [V2.0] 핵심 가치 강조 (Callout) ──
                anchor = analysis.get("empathy_anchor")
                if anchor:
                    children.append(
                        {
                            "object": "block",
                            "type": "callout",
                            "callout": {
                                "rich_text": [
                                    {"type": "text", "text": {"content": f"🎯 공감 앵커 (킬링포인트): {anchor}"}}
                                ],
                                "icon": {"type": "emoji", "emoji": "🎯"},
                                "color": "blue_background",
                            },
                        }
                    )

                spinoff = analysis.get("spinoff_angle")
                if spinoff:
                    children.append(
                        {
                            "object": "block",
                            "type": "callout",
                            "callout": {
                                "rich_text": [{"type": "text", "text": {"content": f"💡 파생각 (Spinoff): {spinoff}"}}],
                                "icon": {"type": "emoji", "emoji": "💡"},
                                "color": "yellow_background",
                            },
                        }
                    )

                profile_lines = [
                    f"📂 토픽 클러스터: {analysis.get('topic_cluster', '기타')}",
                    f"🎣 훅 타입: {analysis.get('hook_type', '공감형')}",
                    f"🎭 감정 축/선: {analysis.get('emotion_axis', '공감')} / {analysis.get('emotion_lane', '')}",
                    f"👥 대상 독자: {analysis.get('audience_fit', '범용')}",
                    f"🔍 선정 이유: {analysis.get('selection_summary', '')}",
                    f"💝 독자 욕구: {analysis.get('audience_need', '')}",
                    f"📝 추천 스타일: {analysis.get('recommended_draft_type', '공감형')}",
                ]
                children.extend(self._create_text_blocks("\n".join(profile_lines)))

            # ── [V2.0] 품질 게이트 결과 노출 ──
            qg_report = post_data.get("quality_gate_report")
            if qg_report:
                children.append({"object": "block", "type": "divider", "divider": {}})
                children.append(
                    {
                        "object": "block",
                        "type": "callout",
                        "callout": {
                            "rich_text": [{"type": "text", "text": {"content": f"🛡️ 품질 검증 리포트\n{qg_report}"}}],
                            "icon": {"type": "emoji", "emoji": "🛡️"},
                            "color": "gray_background",
                        },
                    }
                )

            if drafts:
                if isinstance(drafts, dict):
                    if drafts.get("twitter"):
                        children.append({"object": "block", "type": "divider", "divider": {}})
                        children.append(
                            {
                                "object": "block",
                                "type": "heading_2",
                                "heading_2": {"rich_text": [{"type": "text", "text": {"content": "숏폼 초안"}}]},
                            }
                        )
                        children.extend(self._create_text_blocks(drafts["twitter"]))
                    if drafts.get("reply_text"):
                        children.append({"object": "block", "type": "divider", "divider": {}})
                        children.append(
                            {
                                "object": "block",
                                "type": "heading_3",
                                "heading_3": {"rich_text": [{"type": "text", "text": {"content": "링크 메모"}}]},
                            }
                        )
                        children.extend(self._create_text_blocks(drafts["reply_text"]))
                    if drafts.get("threads"):
                        children.append({"object": "block", "type": "divider", "divider": {}})
                        children.append(
                            {
                                "object": "block",
                                "type": "heading_2",
                                "heading_2": {"rich_text": [{"type": "text", "text": {"content": "Threads 초안"}}]},
                            }
                        )
                        children.extend(self._create_text_blocks(drafts["threads"]))
                    if drafts.get("newsletter"):
                        children.append({"object": "block", "type": "divider", "divider": {}})
                        children.append(
                            {
                                "object": "block",
                                "type": "heading_2",
                                "heading_2": {"rich_text": [{"type": "text", "text": {"content": "뉴스레터 초안"}}]},
                            }
                        )
                        children.extend(self._create_text_blocks(drafts["newsletter"]))
                    if drafts.get("naver_blog"):
                        children.append({"object": "block", "type": "divider", "divider": {}})
                        children.append(
                            {
                                "object": "block",
                                "type": "heading_2",
                                "heading_2": {
                                    "rich_text": [{"type": "text", "text": {"content": "네이버 블로그 초안"}}]
                                },
                            }
                        )
                        children.extend(self._create_text_blocks(drafts["naver_blog"]))
                else:
                    children.append({"object": "block", "type": "divider", "divider": {}})
                    children.append(
                        {
                            "object": "block",
                            "type": "heading_2",
                            "heading_2": {"rich_text": [{"type": "text", "text": {"content": "숏폼 초안"}}]},
                        }
                    )
                    children.extend(self._create_text_blocks(str(drafts)))

            if screenshot_url:
                children.append({"object": "block", "type": "divider", "divider": {}})
                children.append(
                    {
                        "object": "block",
                        "type": "heading_2",
                        "heading_2": {"rich_text": [{"type": "text", "text": {"content": "원문 스크린샷"}}]},
                    }
                )
                children.append(
                    {
                        "object": "block",
                        "type": "image",
                        "image": {"type": "external", "external": {"url": screenshot_url}},
                    }
                )

            children.append({"object": "block", "type": "divider", "divider": {}})
            children.append(
                {
                    "object": "block",
                    "type": "heading_2",
                    "heading_2": {"rich_text": [{"type": "text", "text": {"content": "원문 내용"}}]},
                }
            )
            if post_data.get("content"):
                children.extend(self._create_text_blocks(str(post_data["content"])))

            # P7: 규제 검증 리포트 저장
            regulation_report = post_data.get("regulation_report", "")
            if regulation_report:
                children.append({"object": "block", "type": "divider", "divider": {}})
                children.append(
                    {
                        "object": "block",
                        "type": "heading_2",
                        "heading_2": {"rich_text": [{"type": "text", "text": {"content": "📋 규제 검증 리포트"}}]},
                    }
                )
                children.extend(self._create_text_blocks(regulation_report))
                # 규제 검증 상태 요약을 속성에도 저장
                self._append_property_if_present(
                    properties,
                    "regulation_status",
                    "통과" if "전체 플랫폼 규제 검증 통과" in regulation_report else "경고",
                )

            # ── NotebookLM AI 아티클 (content_writer 자동 생성) ──────────────────
            nlm_article = post_data.get("nlm_article", "")
            if nlm_article:
                children.append({"object": "block", "type": "divider", "divider": {}})
                children.append(
                    {
                        "object": "block",
                        "type": "heading_2",
                        "heading_2": {"rich_text": [{"type": "text", "text": {"content": "✍️ AI 자동 아티클"}}]},
                    }
                )
                # markdown_to_notion_blocks 동적 로드 (workspace/execution/ 단일 소스 유지)
                # 이전: parent.parent.parent.parent 가 projects/ 까지만 가서
                # projects/execution/notion_article_uploader.py 를 찾다가 항상 실패하던 dead-code 였음.
                # parents[4] = repo root → workspace/execution/ 로 정정.
                try:
                    import importlib.util as _ilu
                    import pathlib as _pl

                    _uploader_path = (
                        _pl.Path(__file__).resolve().parents[4]
                        / "workspace"
                        / "execution"
                        / "notion_article_uploader.py"
                    )
                    if not _uploader_path.exists():
                        raise FileNotFoundError(_uploader_path)
                    _spec = _ilu.spec_from_file_location("notion_article_uploader", str(_uploader_path))
                    _uploader_mod = _ilu.module_from_spec(_spec)
                    _spec.loader.exec_module(_uploader_mod)
                    _article_blocks = _uploader_mod.markdown_to_notion_blocks(nlm_article)
                    for _i in range(0, len(_article_blocks), 100):
                        children.extend(_article_blocks[_i : _i + 100])
                except Exception as _exc:
                    logger.debug("[NLM Article] 블록 변환 실패, plain text 폴백: %s", _exc)
                    children.extend(self._create_text_blocks(nlm_article))

            # ── NotebookLM 리서치 자산 (인포그래픽·슬라이드) ─────────────────
            nlm_infographic = post_data.get("nlm_infographic_url", "")
            nlm_slides = post_data.get("nlm_slides_path", "")
            if nlm_infographic or nlm_slides:
                children.append({"object": "block", "type": "divider", "divider": {}})
                children.append(
                    {
                        "object": "block",
                        "type": "heading_2",
                        "heading_2": {
                            "rich_text": [{"type": "text", "text": {"content": "🔬 NotebookLM 리서치 자산"}}]
                        },
                    }
                )
                if nlm_infographic:
                    children.append(
                        {
                            "object": "block",
                            "type": "image",
                            "image": {"type": "external", "external": {"url": nlm_infographic}},
                        }
                    )
                if nlm_slides:
                    children.extend(self._create_text_blocks(f"📊 슬라이드 파일: {nlm_slides}"))
                # NLM infographic URL을 Notion 속성에도 저장
                self._append_property_if_present(properties, "nlm_infographic_url", nlm_infographic)

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
            logger.error("Failed to update Notion page properties: %s", exc)
            return False
