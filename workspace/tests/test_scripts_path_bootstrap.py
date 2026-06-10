from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType


WORKSPACE_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = WORKSPACE_ROOT / "scripts"


def _load_script(module_name: str, script_name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(module_name, SCRIPTS_DIR / script_name)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def test_path_bootstrap_adds_workspace_root_when_loaded(monkeypatch) -> None:
    original_sys_path = list(sys.path)
    monkeypatch.setattr(sys, "path", [entry for entry in original_sys_path if entry != str(WORKSPACE_ROOT)])

    module = _load_script("workspace_scripts_path_bootstrap_test", "_path_bootstrap.py")

    assert module.WORKSPACE == WORKSPACE_ROOT
    assert sys.path[0] == str(WORKSPACE_ROOT)


def test_workspace_scripts_import_path_contract_through_bootstrap(monkeypatch) -> None:
    monkeypatch.syspath_prepend(str(SCRIPTS_DIR))

    loaded = {
        "backup_data": _load_script("workspace_backup_data_test", "backup_data.py"),
        "doctor": _load_script("workspace_doctor_test", "doctor.py"),
        "smoke_check": _load_script("workspace_smoke_check_test", "smoke_check.py"),
        "update_all": _load_script("workspace_update_all_test", "update_all.py"),
    }

    assert loaded["backup_data"].WORKSPACE == WORKSPACE_ROOT
    assert loaded["doctor"].WORKSPACE == WORKSPACE_ROOT
    assert loaded["smoke_check"].WORKSPACE_ROOT == WORKSPACE_ROOT
    assert loaded["update_all"].WORKSPACE == WORKSPACE_ROOT
    assert loaded["backup_data"].REPO_ROOT.exists()
    assert loaded["doctor"].REPO_ROOT == loaded["update_all"].REPO_ROOT
