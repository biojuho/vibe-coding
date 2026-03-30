from __future__ import annotations

import json
import sys
from types import SimpleNamespace

import execution.gdrive_pdf_extractor as extractor


class _FakeDriveService:
    def __init__(self, *, files_payload=None, metadata=None) -> None:
        self.files_payload = files_payload or []
        self.metadata = metadata or {"id": "file-1", "name": "sample.pdf", "webViewLink": "https://drive/file-1"}
        self.list_calls: list[dict] = []
        self.get_calls: list[dict] = []

    def files(self):
        return self

    def list(self, **kwargs):
        self.list_calls.append(kwargs)
        return SimpleNamespace(execute=lambda: {"files": self.files_payload})

    def get(self, **kwargs):
        self.get_calls.append(kwargs)
        return SimpleNamespace(execute=lambda: self.metadata)


def test_list_folder_files_builds_parent_query(monkeypatch) -> None:
    service = _FakeDriveService(files_payload=[{"id": "1"}])
    monkeypatch.setattr(extractor, "_build_drive_service", lambda: service)

    result = extractor.list_folder_files("folder-123", max_results=5)

    assert result == [{"id": "1"}]
    assert service.list_calls[0]["q"] == "'folder-123' in parents and trashed = false"
    assert service.list_calls[0]["pageSize"] == 5


def test_list_new_files_since_adds_time_and_mime_filters(monkeypatch) -> None:
    service = _FakeDriveService(files_payload=[{"id": "2"}])
    monkeypatch.setattr(extractor, "_build_drive_service", lambda: service)

    extractor.list_new_files_since(
        "folder-xyz",
        since_iso="2026-03-20T00:00:00Z",
        mime_filter=["application/pdf", "image/png"],
    )

    query = service.list_calls[0]["q"]
    assert "modifiedTime > '2026-03-20T00:00:00Z'" in query
    assert "mimeType = 'application/pdf'" in query
    assert "mimeType = 'image/png'" in query


def test_extract_text_routes_supported_suffixes(tmp_path, monkeypatch) -> None:
    txt_path = tmp_path / "sample.txt"
    txt_path.write_text("plain text", encoding="utf-8")

    monkeypatch.setattr(extractor, "extract_text_from_pdf", lambda path: "pdf body")
    monkeypatch.setattr(extractor, "extract_text_from_image", lambda path: "ocr body")

    pdf_result = extractor.extract_text(tmp_path / "sample.pdf")
    image_result = extractor.extract_text(tmp_path / "sample.png")
    txt_result = extractor.extract_text(txt_path)
    unknown_result = extractor.extract_text(tmp_path / "sample.bin")

    assert pdf_result["text"] == "pdf body"
    assert image_result["text"] == "ocr body"
    assert txt_result["text"] == "plain text"
    assert "지원하지 않는 파일 형식" in str(unknown_result["warning"])


def test_download_and_extract_combines_metadata_and_text(monkeypatch, tmp_path) -> None:
    service = _FakeDriveService(
        metadata={
            "id": "abc",
            "name": "report.pdf",
            "mimeType": "application/pdf",
            "webViewLink": "https://drive/report",
        }
    )
    local_path = tmp_path / "report.pdf"
    local_path.write_text("placeholder", encoding="utf-8")

    monkeypatch.setattr(extractor, "_build_drive_service", lambda: service)
    monkeypatch.setattr(extractor, "download_file", lambda file_id, dest_dir=None: local_path)
    monkeypatch.setattr(
        extractor,
        "extract_text",
        lambda path: {"text": "extracted body", "char_count": 14, "warning": None},
    )

    result = extractor.download_and_extract("abc", dest_dir=tmp_path)

    assert result["file_name"] == "report.pdf"
    assert result["text"] == "extracted body"
    assert result["drive_url"] == "https://drive/report"
    assert result["local_path"] == str(local_path)


def test_main_extract_writes_output_text(tmp_path, monkeypatch, capsys) -> None:
    output_path = tmp_path / "out.txt"
    monkeypatch.setattr(
        extractor,
        "download_and_extract",
        lambda file_id, dest_dir=None: {"text": "hello world", "char_count": 11},
    )
    monkeypatch.setattr(
        sys,
        "argv",
        ["gdrive_pdf_extractor.py", "extract", "--file-id", "file-1", "--output", str(output_path)],
    )

    extractor.main()

    stdout = capsys.readouterr().out
    assert "텍스트 저장" in stdout
    assert output_path.read_text(encoding="utf-8") == "hello world"


def test_main_list_folder_prints_json(monkeypatch, capsys) -> None:
    monkeypatch.setattr(extractor, "_check_deps", lambda: [])
    monkeypatch.setattr(extractor, "list_folder_files", lambda folder_id: [{"id": "1", "name": "file"}])
    monkeypatch.setattr(
        sys,
        "argv",
        ["gdrive_pdf_extractor.py", "list-folder", "--folder-id", "folder-1"],
    )

    extractor.main()

    payload = json.loads(capsys.readouterr().out)
    assert payload[0]["name"] == "file"
