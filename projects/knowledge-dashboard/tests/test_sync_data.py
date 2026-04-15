from __future__ import annotations

import importlib.util
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
MODULE_PATH = REPO_ROOT / "projects" / "knowledge-dashboard" / "scripts" / "sync_data.py"


def load_sync_data_module():
    spec = importlib.util.spec_from_file_location("knowledge_dashboard_sync_data", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_resolve_notebooklm_token_path_prefers_env_override(tmp_path, monkeypatch):
    module = load_sync_data_module()
    custom_path = tmp_path / "custom-auth.json"
    custom_path.write_text("{}", encoding="utf-8")

    monkeypatch.setenv(module.NOTEBOOKLM_AUTH_TOKEN_ENV_VAR, str(custom_path))

    resolved = module.resolve_notebooklm_token_path(repo_root=tmp_path)

    assert resolved == custom_path


def test_resolve_notebooklm_token_path_prefers_local_file(tmp_path, monkeypatch):
    module = load_sync_data_module()
    token_dir = tmp_path / "infrastructure" / "notebooklm-mcp" / "tokens"
    token_dir.mkdir(parents=True)
    template_path = token_dir / "auth.json"
    local_path = token_dir / "auth.local.json"
    template_path.write_text("{}", encoding="utf-8")
    local_path.write_text("{}", encoding="utf-8")

    monkeypatch.delenv(module.NOTEBOOKLM_AUTH_TOKEN_ENV_VAR, raising=False)

    resolved = module.resolve_notebooklm_token_path(repo_root=tmp_path)

    assert resolved == local_path


def test_is_notebooklm_token_template_detects_placeholders():
    module = load_sync_data_module()

    assert module.is_notebooklm_token_template(
        {
            "cookies": {"SID": "replace-with-local-cookie"},
            "csrf_token": "",
            "session_id": "",
        }
    )


def test_is_notebooklm_token_template_allows_realish_payload():
    module = load_sync_data_module()

    assert not module.is_notebooklm_token_template(
        {
            "cookies": {"SID": "real-cookie-value", "HSID": "another-cookie"},
            "csrf_token": "",
            "session_id": "",
        }
    )
