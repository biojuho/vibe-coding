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

logger = logging.getLogger(__name__)


class NotionUploadMixin:
    """Notion 페이지 생성(upload) 및 속성 업데이트를 담당하는 Mixin.

    사전 조건: ensure_schema, _db_properties, props, client,
    _page_parent_payload, canonicalize_url, _register_url_in_cache 등이
    동일 클래스(NotionUploader)에 합쳐져 있어야 합니다.
    """

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

    async def upload(self, post_data, image_url, drafts, analysis=None, screenshot_url=None):
        """Notion DB에 새 페이지 생성 (본문 + 초안 + 분석 결과)."""
        if not await self.ensure_schema():
            return None

        logger.info("Uploading to Notion: %s", post_data.get("title", "(untitled)"))
        try:
            canonical_url = self.canonicalize_url(post_data.get("url", ""))
            properties: dict[str, Any] = {}

            self._append_property_if_present(properties, "title", post_data.get("title", ""))

            # memo: 원본 링크 + creator_take (있으면)
            memo_parts = [f"원본 링크: {canonical_url or post_data.get('url', '')}"]
            if analysis and analysis.get("selection_summary"):
                memo_parts.append(f"왜 고름: {analysis['selection_summary']}")
            if analysis and analysis.get("selection_reason_labels"):
                memo_parts.append(f"선정 포인트: {', '.join(analysis['selection_reason_labels'])}")
            elif analysis and analysis.get("rationale"):
                memo_parts.append(f"선정 포인트: {', '.join(analysis['rationale'])}")
            if analysis and analysis.get("emotion_lane"):
                memo_parts.append(f"감정선: {analysis['emotion_lane']}")
            if analysis and analysis.get("spinoff_angle"):
                memo_parts.append(f"파생각: {analysis['spinoff_angle']}")
            creator_take = ""
            if isinstance(drafts, dict):
                creator_take = drafts.get("creator_take", "")
            if creator_take:
                memo_parts.append(f"🎯 운영자 해석: {creator_take}")
            self._append_property_if_present(properties, "memo", "\n".join(memo_parts))

            self._append_property_if_present(properties, "status", post_data.get("status") or self.status_default)
            self._append_property_if_present(properties, "date", datetime.now().date())
            self._append_property_if_present(properties, "url", canonical_url)
            self._append_property_if_present(properties, "source", post_data.get("source", "blind"))

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
                        "heading_2": {"rich_text": [{"type": "text", "text": {"content": "콘텐츠 인텔리전스"}}]},
                    }
                )
                profile_lines = [
                    f"토픽 클러스터: {analysis.get('topic_cluster', '기타')}",
                    f"훅 타입: {analysis.get('hook_type', '공감형')}",
                    f"감정 축: {analysis.get('emotion_axis', '공감')}",
                    f"대상 독자: {analysis.get('audience_fit', '범용')}",
                    f"왜 고름: {analysis.get('selection_summary', '')}",
                    f"독자 욕구: {analysis.get('audience_need', '')}",
                    f"감정선: {analysis.get('emotion_lane', '')}",
                    f"공감 앵커: {analysis.get('empathy_anchor', '')}",
                    f"파생각: {analysis.get('spinoff_angle', '')}",
                    f"추천 초안 타입: {analysis.get('recommended_draft_type', '공감형')}",
                    f"스크랩 품질 점수: {analysis.get('scrape_quality_score', 0)}",
                    f"발행 적합도 점수: {analysis.get('publishability_score', 0)}",
                    f"성과 예측 점수: {analysis.get('performance_score', 0)}",
                    f"최종 랭크 점수: {analysis.get('final_rank_score', 0)}",
                ]
                children.extend(self._create_text_blocks("\n".join(profile_lines)))

            if drafts:
                if isinstance(drafts, dict):
                    if drafts.get("twitter"):
                        children.append({"object": "block", "type": "divider", "divider": {}})
                        children.append(
                            {
                                "object": "block",
                                "type": "heading_2",
                                "heading_2": {"rich_text": [{"type": "text", "text": {"content": "X(Twitter) 초안"}}]},
                            }
                        )
                        children.extend(self._create_text_blocks(drafts["twitter"]))
                    if drafts.get("reply_text"):
                        children.append({"object": "block", "type": "divider", "divider": {}})
                        children.append(
                            {
                                "object": "block",
                                "type": "heading_3",
                                "heading_3": {
                                    "rich_text": [{"type": "text", "text": {"content": "X 답글 (링크+해시태그)"}}]
                                },
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
                            "heading_2": {"rich_text": [{"type": "text", "text": {"content": "X(Twitter) 초안"}}]},
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
                # markdown_to_notion_blocks 동적 로드 (execution/ 단일 소스 유지)
                try:
                    import importlib.util as _ilu
                    import pathlib as _pl

                    _uploader_path = (
                        _pl.Path(__file__).resolve().parent.parent.parent.parent
                        / "execution"
                        / "notion_article_uploader.py"
                    )
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
