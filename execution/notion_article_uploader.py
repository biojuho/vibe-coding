"""
Notion 아티클 업로더 (NotebookLM 파이프라인 Phase 1)

3계층 아키텍처의 Execution Layer 스크립트.
AI가 생성한 아티클을 Notion DB에 레코드로 등록하고 페이지 본문을 작성합니다.

이 스크립트는 blind-to-x 프로젝트의 Notion API 인프라를 재사용하지 않고,
독립적인 httpx 기반 구현으로 설계되어 다른 프로젝트 의존성 없이 동작합니다.

환경 변수:
    NOTION_API_KEY            Notion Integration 토큰
    NOTEBOOKLM_NOTION_DB_ID  대상 Notion DB ID

사용 예:
    python execution/notion_article_uploader.py upload --article-file .tmp/article.json
    python execution/notion_article_uploader.py upload --title "제목" --article "본문..." --project default
"""

from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path

from execution._logging import logger

NOTION_API_VERSION = "2022-06-28"
NOTION_BASE_URL = "https://api.notion.com/v1"


# ── Notion API 헬퍼 ─────────────────────────────────────────────────────────

class NotionClient:
    """경량 Notion API 클라이언트 (httpx 기반, 재시도 포함)."""

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or os.environ.get("NOTION_API_KEY")
        if not self.api_key:
            raise ValueError("NOTION_API_KEY 환경 변수 또는 api_key 인자 필요")

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Notion-Version": NOTION_API_VERSION,
            "Content-Type": "application/json",
        }

    def post(self, path: str, body: dict, *, max_retries: int = 3) -> dict:
        """POST 요청 (동기). 429/5xx 시 지수 백오프 재시도."""
        import time
        import httpx

        url = f"{NOTION_BASE_URL}{path}"
        last_exc: Exception | None = None

        for attempt in range(max_retries):
            try:
                resp = httpx.post(url, headers=self._headers(), json=body, timeout=30)
                if resp.status_code == 429:
                    retry_after = int(resp.headers.get("Retry-After", 2 ** attempt))
                    logger.warning("[Notion] Rate limited. %d초 대기 후 재시도...", retry_after)
                    time.sleep(retry_after)
                    continue
                resp.raise_for_status()
                return resp.json()
            except Exception as exc:
                last_exc = exc
                if attempt < max_retries - 1:
                    delay = 2 ** attempt
                    logger.warning("[Notion] 요청 실패 (시도 %d): %s. %d초 후 재시도.", attempt + 1, exc, delay)
                    time.sleep(delay)

        raise RuntimeError(f"Notion API 요청 실패 (최대 재시도 초과): {last_exc}")

    def patch(self, path: str, body: dict) -> dict:
        """PATCH 요청 (동기)."""
        import httpx

        url = f"{NOTION_BASE_URL}{path}"
        resp = httpx.patch(url, headers=self._headers(), json=body, timeout=30)
        resp.raise_for_status()
        return resp.json()


# ── Markdown → Notion 블록 변환 ─────────────────────────────────────────────

def markdown_to_notion_blocks(markdown: str) -> list[dict]:
    """Markdown 텍스트를 Notion 블록 리스트로 변환합니다.

    지원 변환:
    - # H1 → heading_2 (Notion의 페이지 제목이 h1이므로 h2부터 사용)
    - ## H2 → heading_2
    - ### H3 → heading_3
    - - / * bullet → bulleted_list_item
    - 1. 2. ordered → numbered_list_item
    - 빈 줄 → paragraph (빈)
    - 일반 텍스트 → paragraph
    - **bold** 인라인 bold 지원

    Args:
        markdown: Markdown 형식의 텍스트.

    Returns:
        Notion blocks 리스트.

    Note:
        Notion API는 한 번에 최대 100블록까지 허용합니다.
        이 함수는 분할 없이 모든 블록을 반환하므로 호출 측에서 100개씩 나눠 업로드해야 합니다.
    """
    import re

    blocks: list[dict] = []
    lines = markdown.split("\n")

    def _rich_text(text: str) -> list[dict]:
        """간단한 **bold** 파싱을 지원하는 rich_text 변환."""
        parts: list[dict] = []
        # **bold** 패턴 분리
        for chunk in re.split(r"(\*\*[^*]+\*\*)", text):
            if not chunk:
                continue
            if chunk.startswith("**") and chunk.endswith("**"):
                parts.append({
                    "type": "text",
                    "text": {"content": chunk[2:-2]},
                    "annotations": {"bold": True},
                })
            else:
                # 텍스트 2000자 제한 (Notion API 제약)
                while len(chunk) > 2000:
                    parts.append({"type": "text", "text": {"content": chunk[:2000]}})
                    chunk = chunk[2000:]
                if chunk:
                    parts.append({"type": "text", "text": {"content": chunk}})
        return parts or [{"type": "text", "text": {"content": ""}}]

    def _block(block_type: str, content: str) -> dict:
        return {
            "object": "block",
            "type": block_type,
            block_type: {"rich_text": _rich_text(content)},
        }

    for line in lines:
        stripped = line.rstrip()

        if stripped.startswith("### "):
            blocks.append(_block("heading_3", stripped[4:]))
        elif stripped.startswith("## ") or stripped.startswith("# "):
            # H1은 heading_2로 변환 (페이지 제목과 구분)
            content = re.sub(r"^#{1,2} ", "", stripped)
            blocks.append(_block("heading_2", content))
        elif stripped.startswith(("- ", "* ")):
            blocks.append(_block("bulleted_list_item", stripped[2:]))
        elif re.match(r"^\d+\. ", stripped):
            content = re.sub(r"^\d+\. ", "", stripped)
            blocks.append(_block("numbered_list_item", content))
        elif stripped == "---" or stripped == "***":
            blocks.append({"object": "block", "type": "divider", "divider": {}})
        elif stripped == "":
            blocks.append({"object": "block", "type": "paragraph", "paragraph": {"rich_text": []}})
        else:
            blocks.append(_block("paragraph", stripped))

    return blocks


def _chunk_blocks(blocks: list[dict], size: int = 100) -> list[list[dict]]:
    """Notion API 100블록 제한에 맞게 청크로 분할합니다."""
    return [blocks[i: i + size] for i in range(0, len(blocks), size)]


# ── DB 레코드 생성 ───────────────────────────────────────────────────────────

def create_article_page(
    *,
    title: str,
    article: str,
    project: str = "",
    ai_provider: str = "gemini",
    drive_url: str = "",
    tags: list[str] | None = None,
    db_id: str | None = None,
    api_key: str | None = None,
) -> dict:
    """Notion DB에 아티클 레코드와 페이지 본문을 생성합니다.

    Args:
        title: 아티클 제목.
        article: Markdown 형식의 아티클 본문.
        project: 프로젝트 이름 (Select 속성).
        ai_provider: 사용한 AI 모델 이름 (Select 속성).
        drive_url: 원본 자료 Google Drive URL.
        tags: 태그 리스트.
        db_id: Notion DB ID. None이면 환경 변수 NOTEBOOKLM_NOTION_DB_ID 사용.
        api_key: Notion API 키. None이면 환경 변수 NOTION_API_KEY 사용.

    Returns:
        {"page_id": str, "page_url": str, "title": str, "status": "created"}

    Raises:
        ValueError: db_id / api_key 없음.
        RuntimeError: Notion API 오류.
    """
    db_id = db_id or os.environ.get("NOTEBOOKLM_NOTION_DB_ID")
    if not db_id:
        raise ValueError(
            "Notion DB ID 필요: NOTEBOOKLM_NOTION_DB_ID 환경 변수 또는 --db-id 인자 설정"
        )

    client = NotionClient(api_key)
    now_iso = datetime.now(timezone.utc).isoformat()

    # ── DB 레코드 (properties) 구성 ─────────────────────────────────────────
    properties: dict = {
        "제목": {"title": [{"text": {"content": title[:2000]}}]},
        "작성일": {"date": {"start": now_iso}},
        "상태": {"status": {"name": "초안"}},
        "AI 모델": {"select": {"name": ai_provider}},
    }

    if project:
        properties["프로젝트"] = {"select": {"name": project}}

    if drive_url:
        properties["원본 자료"] = {"url": drive_url}

    if tags:
        properties["태그"] = {"multi_select": [{"name": t} for t in tags[:10]]}

    # 페이지 생성 (본문 없이 먼저 생성)
    page_body = {
        "parent": {"database_id": db_id.replace("-", "")},
        "properties": properties,
    }

    logger.info("[NotionUploader] 페이지 생성 중: %s", title[:50])
    page = client.post("/pages", page_body)
    page_id = page["id"]
    page_url = page.get("url", f"https://notion.so/{page_id.replace('-', '')}")
    logger.info("[NotionUploader] 페이지 생성 완료: %s", page_url)

    # ── 본문 블록 추가 ───────────────────────────────────────────────────────
    blocks = markdown_to_notion_blocks(article)
    chunks = _chunk_blocks(blocks, size=100)

    for i, chunk in enumerate(chunks):
        client.patch(f"/blocks/{page_id}/children", {"children": chunk})
        if i < len(chunks) - 1:
            import time
            time.sleep(0.3)  # Rate limit 방지

    logger.info("[NotionUploader] 본문 블록 추가 완료 (%d블록, %d청크)", len(blocks), len(chunks))

    return {
        "page_id": page_id,
        "page_url": page_url,
        "title": title,
        "status": "created",
        "block_count": len(blocks),
    }


# ── CLI 엔트리포인트 ─────────────────────────────────────────────────────────

def main():
    """CLI 엔트리포인트."""
    parser = argparse.ArgumentParser(description="Notion 아티클 업로더")
    sub = parser.add_subparsers(dest="command", required=True)

    p_upload = sub.add_parser("upload", help="Notion 페이지 생성")
    p_upload.add_argument("--article-file", help="content_writer.py 출력 JSON 파일 경로")
    p_upload.add_argument("--title", help="아티클 제목 (--article-file 없을 때 필수)")
    p_upload.add_argument("--article", help="Markdown 본문 (--article-file 없을 때 필수)")
    p_upload.add_argument("--project", default="", help="프로젝트 이름")
    p_upload.add_argument("--provider", default="gemini", help="사용한 AI 모델")
    p_upload.add_argument("--drive-url", default="", help="원본 Google Drive URL")
    p_upload.add_argument("--tags", nargs="*", default=None, help="태그 목록")
    p_upload.add_argument("--db-id", default=None, help="Notion DB ID")

    args = parser.parse_args()

    if args.command == "upload":
        # JSON 파일에서 로드
        if args.article_file:
            data = json.loads(Path(args.article_file).read_text(encoding="utf-8"))
            title = data.get("title") or args.title or "제목 없음"
            article = data.get("article", "")
            provider = data.get("provider", args.provider)
            project = data.get("project", args.project)
        else:
            if not args.title or not args.article:
                print("✗ --article-file 또는 (--title + --article) 필요")
                raise SystemExit(1)
            title = args.title
            article = args.article
            provider = args.provider
            project = args.project

        result = create_article_page(
            title=title,
            article=article,
            project=project,
            ai_provider=provider,
            drive_url=args.drive_url,
            tags=args.tags,
            db_id=args.db_id,
        )
        print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
