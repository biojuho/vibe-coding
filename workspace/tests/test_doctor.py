from __future__ import annotations

from pathlib import Path

import scripts.doctor as doctor


def _find_result(results, name: str):
    for item in results:
        if item.name == name:
            return item
    raise AssertionError(f"Result not found: {name}")


def _configure_common_success(monkeypatch, tmp_path: Path) -> None:
    fake_venv_python = tmp_path / "venv" / "Scripts" / "python.exe"
    fake_venv_python.parent.mkdir(parents=True, exist_ok=True)
    fake_venv_python.write_text("", encoding="utf-8")

    env_file = tmp_path / ".env"
    env_file.write_text("OPENAI_API_KEY=test-key\n", encoding="utf-8")

    monkeypatch.setattr(doctor, "VENV_PYTHON", fake_venv_python)
    monkeypatch.setattr(doctor, "ROOT_ENV", env_file)
    monkeypatch.setattr(doctor, "WORKSPACE_ENV", tmp_path / "workspace" / ".env")
    monkeypatch.setattr(doctor, "_read_env_file", lambda _path: {"OPENAI_API_KEY": "test-key"})

    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    monkeypatch.delenv("LLM_PROVIDER", raising=False)


def test_run_checks_interpreter_warn_when_not_workspace_venv(monkeypatch, tmp_path):
    _configure_common_success(monkeypatch, tmp_path)
    monkeypatch.setattr(doctor, "_module_exists", lambda _name: True)

    results = doctor.run_checks()
    interpreter = _find_result(results, "Interpreter")
    assert interpreter.status == "WARN"
    assert "Current python is not workspace venv" in interpreter.detail


def test_run_checks_marks_missing_required_package_as_fail(monkeypatch, tmp_path):
    _configure_common_success(monkeypatch, tmp_path)

    def fake_module_exists(module_name: str) -> bool:
        if module_name == "gtts":
            return False
        return True

    monkeypatch.setattr(doctor, "_module_exists", fake_module_exists)

    results = doctor.run_checks()
    package = _find_result(results, "Package:gTTS")
    assert package.status == "FAIL"
    assert "missing" in package.detail.lower()


def test_run_checks_warns_for_google_provider_without_google_key(monkeypatch, tmp_path):
    _configure_common_success(monkeypatch, tmp_path)
    monkeypatch.setattr(doctor, "_module_exists", lambda _name: True)
    monkeypatch.setattr(doctor, "_read_env_file", lambda _path: {"LLM_PROVIDER": "google"})

    results = doctor.run_checks()
    llm_key = _find_result(results, "LLM Key")
    assert llm_key.status == "WARN"
    assert "LLM_PROVIDER=google" in llm_key.detail
