"""
YouTube Shorts 업로드 자동화.

YouTube Data API v3 + OAuth2를 사용하여 영상을 업로드합니다.
초기 인증 시 브라우저가 열리며, 이후에는 token.json으로 자동 갱신됩니다.

Usage:
    python execution/youtube_uploader.py auth-check
    python execution/youtube_uploader.py upload --video /path/to/video.mp4 --title "제목"
    python execution/youtube_uploader.py upload-pending --limit 3

Prerequisites:
    pip install google-api-python-client google-auth-oauthlib
    - Google Cloud Console에서 OAuth 2.0 클라이언트 ID 생성
    - credentials.json을 프로젝트 루트에 배치
"""

from __future__ import annotations

import argparse
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_ROOT = Path(__file__).resolve().parent.parent
CREDENTIALS_PATH = _ROOT / "credentials.json"
TOKEN_PATH = _ROOT / "token.json"

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
API_SERVICE_NAME = "youtube"
API_VERSION = "v3"


def _get_credentials():
    """OAuth2 자격 증명 로드/갱신. 없으면 브라우저 인증 플로우."""
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow

    creds = None
    if TOKEN_PATH.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_PATH), SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not CREDENTIALS_PATH.exists():
                raise FileNotFoundError(
                    f"OAuth credentials not found: {CREDENTIALS_PATH}\n"
                    "Google Cloud Console에서 OAuth 2.0 클라이언트 ID를 생성하고 "
                    "credentials.json을 프로젝트 루트에 배치하세요."
                )
            flow = InstalledAppFlow.from_client_secrets_file(str(CREDENTIALS_PATH), SCOPES)
            creds = flow.run_local_server(port=0)

        TOKEN_PATH.write_text(creds.to_json(), encoding="utf-8")

    return creds


def _build_youtube_service():
    """YouTube API 서비스 빌드."""
    from googleapiclient.discovery import build

    creds = _get_credentials()
    return build(API_SERVICE_NAME, API_VERSION, credentials=creds)


def get_auth_status() -> dict[str, Any]:
    """업로드 가능 상태를 반환한다."""
    status = {
        "has_credentials_file": CREDENTIALS_PATH.exists(),
        "has_token_file": TOKEN_PATH.exists(),
        "token_valid_or_refreshable": False,
        "ready": False,
        "reason": "",
    }
    if not status["has_credentials_file"]:
        status["reason"] = "credentials.json 없음"
        return status

    try:
        from google.oauth2.credentials import Credentials

        if not status["has_token_file"]:
            status["ready"] = True
            status["reason"] = "token.json 없음 - 첫 업로드 시 브라우저 인증 진행"
            return status

        creds = Credentials.from_authorized_user_file(str(TOKEN_PATH), SCOPES)
        status["token_valid_or_refreshable"] = bool(creds and (creds.valid or creds.refresh_token))
        status["ready"] = True
        status["reason"] = (
            "토큰 준비 완료"
            if status["token_valid_or_refreshable"]
            else "refresh 필요 또는 재인증 필요"
        )
        return status
    except Exception as exc:
        status["ready"] = False
        status["reason"] = f"인증 상태 확인 실패: {exc}"
        return status


def is_authenticated() -> bool:
    """OAuth 토큰 유효 여부 확인."""
    return bool(get_auth_status()["token_valid_or_refreshable"])


def _build_video_body(
    title: str,
    description: str = "",
    tags: list[str] | None = None,
    privacy_status: str = "private",
    category_id: str = "22",
) -> dict[str, Any]:
    return {
        "snippet": {
            "title": title[:100],
            "description": description[:5000],
            "tags": (tags or [])[:500],
            "categoryId": category_id,
        },
        "status": {
            "privacyStatus": privacy_status,
            "selfDeclaredMadeForKids": False,
        },
    }


def _trim_error(exc: Exception | str, limit: int = 300) -> str:
    return str(exc)[:limit]


def _build_description_and_tags(item: dict[str, Any]) -> tuple[str, list[str]]:
    topic = item["topic"]
    channel = item.get("channel", "")
    description = f"#{channel} #{topic}" if channel else f"#{topic}"
    tags = [channel, "shorts"] if channel else ["shorts"]
    return description, tags


def _reset_upload_fields(item_id: int, update_job_fn) -> None:
    update_job_fn(
        item_id,
        youtube_video_id="",
        youtube_status="",
        youtube_url="",
        youtube_uploaded_at="",
        youtube_error="",
    )


def _upload_db_item(
    item: dict[str, Any],
    *,
    update_job_fn,
    privacy_status: str = "private",
    reset_first: bool = False,
) -> dict[str, Any]:
    item_id = item["id"]
    title = item.get("title", "") or item["topic"]
    description, tags = _build_description_and_tags(item)

    if reset_first:
        _reset_upload_fields(item_id, update_job_fn)

    result = upload_video(
        video_path=item["video_path"],
        title=title,
        description=description,
        tags=tags,
        privacy_status=privacy_status,
    )
    update_job_fn(
        item_id,
        youtube_video_id=result["video_id"],
        youtube_status="uploaded",
        youtube_url=result["youtube_url"],
        youtube_uploaded_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        youtube_error="",
    )
    return {"item_id": item_id, **result}


def upload_video(
    video_path: str,
    title: str,
    description: str = "",
    tags: list[str] | None = None,
    privacy_status: str = "private",
    category_id: str = "22",  # People & Blogs
) -> dict[str, Any]:
    """
    YouTube 영상 업로드.

    Args:
        video_path: 업로드할 영상 파일 경로
        title: 영상 제목
        description: 영상 설명
        tags: 태그 리스트
        privacy_status: 공개 상태 (private/unlisted/public)
        category_id: YouTube 카테고리 ID

    Returns:
        {"video_id": "...", "youtube_url": "https://youtu.be/...", "status": "uploaded"}

    Raises:
        FileNotFoundError: 영상 파일 없음
        RuntimeError: 업로드 실패
    """
    from googleapiclient.http import MediaFileUpload

    video_file = Path(video_path)
    if not video_file.exists():
        raise FileNotFoundError(f"Video file not found: {video_path}")

    youtube = _build_youtube_service()

    body = _build_video_body(
        title=title,
        description=description,
        tags=tags,
        privacy_status=privacy_status,
        category_id=category_id,
    )

    media = MediaFileUpload(
        str(video_file),
        mimetype="video/mp4",
        resumable=True,
        chunksize=10 * 1024 * 1024,  # 10MB chunks
    )

    request = youtube.videos().insert(
        part="snippet,status",
        body=body,
        media_body=media,
    )

    MAX_RETRIES = 5
    response = None
    retry = 0
    while response is None:
        try:
            _, response = request.next_chunk()
        except Exception as chunk_err:
            retry += 1
            if retry > MAX_RETRIES:
                raise RuntimeError(
                    f"Upload failed after {MAX_RETRIES} retries: {chunk_err}"
                ) from chunk_err
            logger.warning("Upload chunk retry %d/%d: %s", retry, MAX_RETRIES, chunk_err)

    video_id = response.get("id", "")
    if not video_id:
        raise RuntimeError(f"Upload succeeded but no video ID returned: {response}")

    return {
        "video_id": video_id,
        "youtube_url": f"https://youtu.be/{video_id}",
        "status": "uploaded",
    }


def get_video_status(video_id: str) -> dict[str, Any]:
    """업로드된 영상의 처리 상태 확인."""
    youtube = _build_youtube_service()
    response = youtube.videos().list(
        part="status,processingDetails",
        id=video_id,
    ).execute()

    items = response.get("items", [])
    if not items:
        return {"video_id": video_id, "status": "not_found"}

    item = items[0]
    status = item.get("status", {})
    processing = item.get("processingDetails", {})
    return {
        "video_id": video_id,
        "upload_status": status.get("uploadStatus", ""),
        "privacy_status": status.get("privacyStatus", ""),
        "processing_status": processing.get("processingStatus", ""),
    }


def upload_pending_items(
    limit: int = 5,
    channel: str | None = None,
    retry_failed: bool = False,
    privacy_status: str = "private",
) -> list[dict[str, Any]]:
    """content_db에서 업로드 가능한 항목을 찾아 순차 업로드."""
    import sys
    _root = Path(__file__).resolve().parent.parent
    if str(_root) not in sys.path:
        sys.path.insert(0, str(_root))
    from execution.content_db import get_uploadable_items, init_db, update_job

    init_db()
    items = get_uploadable_items(channel=channel, limit=limit, include_failed=retry_failed)
    results: list[dict[str, Any]] = []

    for item in items:
        item_id = item["id"]
        ch = item.get("channel", "")
        title = item.get("title", "") or item["topic"]

        logger.info("[YT] 업로드 시작: [%s] %s", ch, title)
        try:
            result = _upload_db_item(
                item,
                update_job_fn=update_job,
                privacy_status=privacy_status,
                reset_first=item.get("youtube_status") == "failed",
            )
            logger.info("  -> 성공: %s", result["youtube_url"])
            results.append({"item_id": item_id, **result})
        except Exception as exc:
            update_job(item_id, youtube_status="failed", youtube_error=_trim_error(exc))
            logger.error("  -> 실패: %s", exc)
            results.append({"item_id": item_id, "status": "failed", "error": str(exc)})

    return results


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _cli() -> None:
    parser = argparse.ArgumentParser(description="YouTube Shorts Uploader")
    sub = parser.add_subparsers(dest="cmd")

    sub.add_parser("auth-check", help="OAuth 토큰 유효성 확인")

    upload_p = sub.add_parser("upload", help="단일 영상 업로드")
    upload_p.add_argument("--video", required=True, help="영상 파일 경로")
    upload_p.add_argument("--title", required=True, help="영상 제목")
    upload_p.add_argument("--description", default="", help="영상 설명")
    upload_p.add_argument("--privacy", default="private", choices=["private", "unlisted", "public"])

    pending_p = sub.add_parser("upload-pending", help="DB에서 대기 중인 영상 업로드")
    pending_p.add_argument("--limit", type=int, default=5)
    pending_p.add_argument("--channel", default="")
    pending_p.add_argument("--retry-failed", action="store_true", help="기존 업로드 실패 건도 재시도")
    pending_p.add_argument("--privacy", default="private", choices=["private", "unlisted", "public"])

    status_p = sub.add_parser("status", help="영상 처리 상태 확인")
    status_p.add_argument("--video-id", required=True)

    args = parser.parse_args()

    if args.cmd == "auth-check":
        auth = get_auth_status()
        if auth["token_valid_or_refreshable"]:
            print("[OK] YouTube OAuth 토큰 유효")
        elif auth["ready"]:
            print(f"[WARN] {auth['reason']}")
        else:
            print(f"[FAIL] {auth['reason']}")

    elif args.cmd == "upload":
        result = upload_video(
            video_path=args.video,
            title=args.title,
            description=args.description,
            privacy_status=args.privacy,
        )
        print(json.dumps(result, indent=2, ensure_ascii=False))

    elif args.cmd == "upload-pending":
        results = upload_pending_items(
            limit=args.limit,
            channel=args.channel or None,
            retry_failed=args.retry_failed,
            privacy_status=args.privacy,
        )
        print(f"\n업로드 완료: {len([r for r in results if r.get('status') == 'uploaded'])}건")

    elif args.cmd == "status":
        result = get_video_status(args.video_id)
        print(json.dumps(result, indent=2, ensure_ascii=False))

    else:
        parser.print_help()


if __name__ == "__main__":
    _cli()
