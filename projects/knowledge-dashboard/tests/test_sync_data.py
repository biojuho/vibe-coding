from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import SimpleNamespace


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


def test_github_remote_base_url_normalizes_https_and_ssh():
    module = load_sync_data_module()

    assert (
        module.github_remote_base_url("origin\thttps://github.com/biojuho/vibe-coding.git (fetch)")
        == "https://github.com/biojuho/vibe-coding"
    )
    assert (
        module.github_remote_base_url("origin\tgit@github.com:biojuho/vibe-coding.git (push)")
        == "https://github.com/biojuho/vibe-coding"
    )


def test_local_project_to_github_repo_links_subproject_to_tree():
    module = load_sync_data_module()

    repo = module.local_project_to_github_repo(
        {
            "path": "projects/knowledge-dashboard",
            "markers": ["package.json", "CLAUDE.md"],
            "has_readme": True,
            "test_file_count": 14,
            "workflows": [],
        },
        "https://github.com/biojuho/vibe-coding",
        "main",
    )

    assert repo["name"] == "knowledge-dashboard"
    assert repo["html_url"] == ("https://github.com/biojuho/vibe-coding/tree/main/projects/knowledge-dashboard")
    assert repo["language"] == "TypeScript"
    assert "14 test file(s)" in repo["description"]


def test_fetch_github_repos_falls_back_to_local_inventory_without_token(monkeypatch):
    module = load_sync_data_module()
    monkeypatch.setattr(module, "GITHUB_TOKEN", "")
    monkeypatch.setattr(
        module,
        "fetch_local_workspace_projects",
        lambda: [{"name": "local-project", "html_url": "https://github.com/x/y"}],
    )

    assert module.fetch_github_repos() == [{"name": "local-project", "html_url": "https://github.com/x/y"}]


def test_build_product_readiness_uses_default_project_qc_artifact(tmp_path, monkeypatch):
    module = load_sync_data_module()
    captured_kwargs = {}

    def fake_build_report(repo_root, **kwargs):
        captured_kwargs.update(kwargs)
        return {"overall": {"score": 96, "state": "blocked"}}

    monkeypatch.setitem(
        sys.modules,
        "product_readiness_score",
        SimpleNamespace(build_report=fake_build_report),
    )
    monkeypatch.setattr(module, "READINESS_FILE", tmp_path / "product_readiness.json")

    report = module.build_product_readiness()

    assert report["overall"]["score"] == 96
    assert captured_kwargs == {}
