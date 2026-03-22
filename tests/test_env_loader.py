"""_env_loader 단위 테스트."""

import execution._env_loader as loader


def test_load_all_env_runs_without_error():
    loader._loaded = False
    loader.load_all_env()
    assert loader._loaded is True


def test_load_all_env_skips_when_already_loaded():
    loader._loaded = True
    loader.load_all_env()  # should not raise
    assert loader._loaded is True


def test_load_all_env_force_reloads():
    loader._loaded = True
    loader.load_all_env(force=True)
    assert loader._loaded is True


def test_env_files_list_not_empty():
    assert len(loader._ENV_FILES) >= 1
