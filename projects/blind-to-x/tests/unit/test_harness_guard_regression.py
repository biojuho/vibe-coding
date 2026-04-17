from pathlib import Path


def test_regression_get_project_root_dynamic_resolution(tmp_path):
    """
    [QA 수정] 경로 결합 방지 회귀 테스트:
    pyproject.toml을 찾을 수 있을 때 그 경로를 루트로 반환하는지 확인.
    """
    # Create fake project context
    fake_project = tmp_path / "fake-project"
    fake_project.mkdir()
    (fake_project / "pyproject.toml").touch()

    fake_pipeline = fake_project / "pipeline"
    fake_pipeline.mkdir()

    fake_module = fake_pipeline / "harness_guard.py"
    fake_module.touch()

    # Monkeypatch __file__ for harness_guard inside test
    import pipeline.harness_guard as hg

    original_file = getattr(hg, "__file__", None)

    try:
        hg.__file__ = str(fake_module)
        root = hg._get_project_root()
        assert Path(root).resolve() == Path(fake_project).resolve()
    finally:
        if original_file:
            hg.__file__ = original_file
