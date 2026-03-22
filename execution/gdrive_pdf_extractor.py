"""
Google Drive PDF 텍스트 추출기 (NotebookLM 파이프라인 Phase 1)

3계층 아키텍처의 Execution Layer 스크립트.
Google Drive에서 파일을 다운로드하고 PDF / 이미지에서 텍스트를 추출합니다.

n8n bridge_server를 통해 호출되거나 CLI로 직접 실행 가능합니다.

환경 변수:
    GOOGLE_DRIVE_SERVICE_ACCOUNT_JSON  서비스 계정 JSON 파일 경로
    GOOGLE_DRIVE_FOLDER_ID             모니터링할 Drive 폴더 ID (기본: root)

사용 예:
    python execution/gdrive_pdf_extractor.py extract --file-id 1ABC... --output .tmp/output.txt
    python execution/gdrive_pdf_extractor.py list-folder --folder-id 1XYZ...
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from execution._logging import logger

# ── Google API 의존성 확인 ──────────────────────────────────────────────────

def _check_deps() -> list[str]:
    """필요한 라이브러리 설치 여부 확인."""
    missing = []
    for pkg in ["google.oauth2", "googleapiclient", "pdfplumber"]:
        try:
            __import__(pkg.split(".")[0])
        except ImportError:
            missing.append(pkg)
    return missing


# ── Google Drive 클라이언트 ─────────────────────────────────────────────────

def _build_drive_service():
    """Google Drive API 서비스 객체를 구성합니다.

    서비스 계정 인증(권장) 또는 Application Default Credentials를 순서대로 시도합니다.
    """
    from google.oauth2 import service_account
    from googleapiclient.discovery import build

    sa_json_path = os.environ.get("GOOGLE_DRIVE_SERVICE_ACCOUNT_JSON", "")
    scopes = ["https://www.googleapis.com/auth/drive.readonly"]

    if sa_json_path and Path(sa_json_path).exists():
        creds = service_account.Credentials.from_service_account_file(
            sa_json_path, scopes=scopes
        )
        logger.info("[GDrive] 서비스 계정 인증 사용: %s", sa_json_path)
    else:
        # Application Default Credentials (로컬 gcloud auth 등)
        import google.auth
        creds, _ = google.auth.default(scopes=scopes)
        logger.info("[GDrive] Application Default Credentials 사용")

    return build("drive", "v3", credentials=creds, cache_discovery=False)


# ── 파일 목록 조회 ──────────────────────────────────────────────────────────

def list_folder_files(folder_id: str | None = None, *, max_results: int = 50) -> list[dict]:
    """Drive 폴더의 파일 목록을 반환합니다.

    Args:
        folder_id: Drive 폴더 ID. None이면 환경 변수 GOOGLE_DRIVE_FOLDER_ID 사용.
        max_results: 최대 결과 수.

    Returns:
        [{"id": str, "name": str, "mimeType": str, "modifiedTime": str, "size": str}, ...]
    """
    folder_id = folder_id or os.environ.get("GOOGLE_DRIVE_FOLDER_ID", "root")
    service = _build_drive_service()

    query = f"'{folder_id}' in parents and trashed = false"
    fields = "files(id, name, mimeType, modifiedTime, size)"

    result = (
        service.files()
        .list(q=query, pageSize=max_results, fields=fields, orderBy="modifiedTime desc")
        .execute()
    )
    files = result.get("files", [])
    logger.info("[GDrive] 폴더 %s에서 %d개 파일 조회", folder_id, len(files))
    return files


def list_new_files_since(
    folder_id: str | None = None,
    *,
    since_iso: str | None = None,
    mime_filter: list[str] | None = None,
) -> list[dict]:
    """지정 시각 이후 새로 추가된 파일 목록을 반환합니다.

    Args:
        folder_id: Drive 폴더 ID.
        since_iso: ISO 8601 기준 시각 (예: "2026-03-21T00:00:00Z").
        mime_filter: 허용할 MIME 타입 목록. None이면 모두 포함.
            예: ["application/pdf", "image/png"]

    Returns:
        파일 메타데이터 리스트.
    """
    folder_id = folder_id or os.environ.get("GOOGLE_DRIVE_FOLDER_ID", "root")
    service = _build_drive_service()

    query = f"'{folder_id}' in parents and trashed = false"
    if since_iso:
        query += f" and modifiedTime > '{since_iso}'"
    if mime_filter:
        mime_conditions = " or ".join(f"mimeType = '{m}'" for m in mime_filter)
        query += f" and ({mime_conditions})"

    fields = "files(id, name, mimeType, modifiedTime, size, webViewLink)"
    result = (
        service.files()
        .list(q=query, pageSize=100, fields=fields, orderBy="modifiedTime desc")
        .execute()
    )
    files = result.get("files", [])
    logger.info("[GDrive] %d개 신규 파일 감지 (since: %s)", len(files), since_iso)
    return files


# ── 파일 다운로드 ────────────────────────────────────────────────────────────

def download_file(file_id: str, *, dest_dir: str | Path | None = None) -> Path:
    """Drive 파일을 로컬에 다운로드합니다.

    Args:
        file_id: Google Drive 파일 ID.
        dest_dir: 저장 디렉토리. None이면 .tmp/gdrive_downloads/.

    Returns:
        다운로드된 로컬 파일 경로.

    Raises:
        RuntimeError: 다운로드 실패 시.
    """
    from googleapiclient.http import MediaIoBaseDownload
    import io

    service = _build_drive_service()

    # 파일 메타데이터 조회
    meta = service.files().get(fileId=file_id, fields="id,name,mimeType").execute()
    filename = meta.get("name", file_id)
    mime_type = meta.get("mimeType", "")

    # Google Docs/Slides는 export 필요
    export_mime = None
    if mime_type == "application/vnd.google-apps.presentation":
        export_mime = "application/pdf"
        filename = Path(filename).stem + ".pdf"
    elif mime_type == "application/vnd.google-apps.document":
        export_mime = "application/pdf"
        filename = Path(filename).stem + ".pdf"

    # 저장 경로 결정
    if dest_dir is None:
        dest_dir = Path(".tmp") / "gdrive_downloads"
    dest_dir = Path(dest_dir)
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest_path = dest_dir / filename

    # 다운로드 실행
    fh = io.FileIO(str(dest_path), "wb")
    try:
        if export_mime:
            request = service.files().export_media(fileId=file_id, mimeType=export_mime)
        else:
            request = service.files().get_media(fileId=file_id)

        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while not done:
            _, done = downloader.next_chunk()
    finally:
        fh.close()

    logger.info("[GDrive] 다운로드 완료: %s (%.1f KB)", dest_path, dest_path.stat().st_size / 1024)
    return dest_path


# ── 텍스트 추출 ──────────────────────────────────────────────────────────────

def extract_text_from_pdf(pdf_path: str | Path) -> str:
    """PDF 파일에서 텍스트를 추출합니다.

    Args:
        pdf_path: PDF 파일 경로.

    Returns:
        추출된 텍스트 (페이지 구분자 포함).

    Raises:
        ImportError: pdfplumber 미설치 시.
        FileNotFoundError: 파일이 없을 때.
    """
    import pdfplumber

    pdf_path = Path(pdf_path)
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF 파일 없음: {pdf_path}")

    pages_text: list[str] = []
    with pdfplumber.open(str(pdf_path)) as pdf:
        for i, page in enumerate(pdf.pages, 1):
            text = page.extract_text() or ""
            text = text.strip()
            if text:
                pages_text.append(f"[페이지 {i}]\n{text}")

    full_text = "\n\n".join(pages_text)
    logger.info("[PDF Extract] %s — %d페이지 추출 완료 (%d자)", pdf_path.name, len(pages_text), len(full_text))

    if not full_text.strip():
        logger.warning("[PDF Extract] 텍스트 없음 (스캔 PDF일 가능성). OCR 필요.")

    return full_text


def extract_text_from_image(image_path: str | Path) -> str:
    """이미지 파일에서 OCR로 텍스트를 추출합니다.

    pytesseract가 없으면 빈 문자열을 반환하고 경고를 기록합니다.
    Google Vision API 대안은 향후 Phase 2에서 구현 예정.

    Args:
        image_path: 이미지 파일 경로 (PNG/JPG 등).

    Returns:
        추출된 텍스트.
    """
    try:
        import pytesseract
        from PIL import Image

        img = Image.open(str(image_path))
        text = pytesseract.image_to_string(img, lang="kor+eng")
        logger.info("[OCR] %s 텍스트 추출 완료 (%d자)", Path(image_path).name, len(text))
        return text.strip()
    except ImportError:
        logger.warning("[OCR] pytesseract 미설치 — 이미지 OCR 스킵. Phase 2에서 지원 예정.")
        return ""


def extract_text(file_path: str | Path) -> dict:
    """파일 경로를 기반으로 파일 형식에 맞게 텍스트를 추출합니다.

    Args:
        file_path: 로컬 파일 경로.

    Returns:
        {"text": str, "file": str, "mime_type": str, "char_count": int, "warning": str | None}
    """
    file_path = Path(file_path)
    suffix = file_path.suffix.lower()

    warning = None

    if suffix == ".pdf":
        text = extract_text_from_pdf(file_path)
        mime = "application/pdf"
        if not text.strip():
            warning = "PDF에서 텍스트 추출 실패 (스캔 PDF). OCR 도구가 필요합니다."
    elif suffix in (".png", ".jpg", ".jpeg", ".webp"):
        text = extract_text_from_image(file_path)
        mime = f"image/{suffix.lstrip('.')}"
        if not text.strip():
            warning = "이미지 OCR 실패 또는 pytesseract 미설치."
    elif suffix == ".txt":
        text = file_path.read_text(encoding="utf-8", errors="replace")
        mime = "text/plain"
    else:
        text = ""
        mime = "application/octet-stream"
        warning = f"지원하지 않는 파일 형식: {suffix}. PDF/PNG/JPG/TXT만 지원합니다."
        logger.warning("[Extract] %s", warning)

    return {
        "text": text,
        "file": str(file_path),
        "mime_type": mime,
        "char_count": len(text),
        "warning": warning,
    }


# ── 원스톱 파이프라인 ────────────────────────────────────────────────────────

def download_and_extract(file_id: str, *, dest_dir: str | Path | None = None) -> dict:
    """Drive 파일 다운로드 + 텍스트 추출을 한 번에 실행합니다.

    Args:
        file_id: Google Drive 파일 ID.
        dest_dir: 임시 저장 디렉토리.

    Returns:
        {"file_id": str, "file_name": str, "text": str, "char_count": int,
         "drive_url": str, "warning": str | None}
    """
    logger.info("[GDrive Pipeline] 파일 다운로드 시작: %s", file_id)

    # 메타데이터 먼저 가져오기
    service = _build_drive_service()
    meta = service.files().get(
        fileId=file_id, fields="id,name,mimeType,webViewLink"
    ).execute()

    local_path = download_file(file_id, dest_dir=dest_dir)
    extracted = extract_text(local_path)

    return {
        "file_id": file_id,
        "file_name": meta.get("name", ""),
        "text": extracted["text"],
        "char_count": extracted["char_count"],
        "drive_url": meta.get("webViewLink", f"https://drive.google.com/file/d/{file_id}/view"),
        "warning": extracted.get("warning"),
        "local_path": str(local_path),
    }


# ── CLI 엔트리포인트 ─────────────────────────────────────────────────────────

def main():
    """CLI 엔트리포인트."""
    # 의존성 체크
    missing = _check_deps()
    if missing:
        print(f"⚠ 필수 라이브러리 미설치: {', '.join(missing)}")
        print("  설치: pip install google-api-python-client google-auth pdfplumber")

    parser = argparse.ArgumentParser(description="Google Drive PDF 텍스트 추출기")
    sub = parser.add_subparsers(dest="command", required=True)

    # extract: 파일 ID → 다운로드 + 텍스트 추출
    p_extract = sub.add_parser("extract", help="파일 다운로드 + 텍스트 추출")
    p_extract.add_argument("--file-id", required=True, help="Google Drive 파일 ID")
    p_extract.add_argument("--output", help="텍스트 저장 파일 경로 (없으면 stdout)")
    p_extract.add_argument("--dest-dir", default=None, help="임시 다운로드 디렉토리")

    # list-folder: 폴더 파일 목록
    p_list = sub.add_parser("list-folder", help="폴더 파일 목록 조회")
    p_list.add_argument("--folder-id", default=None, help="Drive 폴더 ID")
    p_list.add_argument("--since", default=None, help="ISO 8601 기준 시각 (신규 파일만)")
    p_list.add_argument(
        "--mime",
        nargs="*",
        default=["application/pdf", "image/png", "image/jpeg"],
        help="필터할 MIME 타입",
    )

    args = parser.parse_args()

    if args.command == "extract":
        result = download_and_extract(args.file_id, dest_dir=args.dest_dir)
        if args.output:
            out = Path(args.output)
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(result["text"], encoding="utf-8")
            print(f"✓ 텍스트 저장: {args.output} ({result['char_count']}자)")
        else:
            print(json.dumps(result, ensure_ascii=False, indent=2))

    elif args.command == "list-folder":
        if args.since:
            files = list_new_files_since(args.folder_id, since_iso=args.since, mime_filter=args.mime)
        else:
            files = list_folder_files(args.folder_id)
        print(json.dumps(files, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
