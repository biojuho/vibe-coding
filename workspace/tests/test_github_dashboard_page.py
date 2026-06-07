from pathlib import Path


WORKSPACE_ROOT = Path(__file__).resolve().parents[1]
PAGE_SOURCE = WORKSPACE_ROOT / "execution" / "pages" / "github_dashboard.py"


def _source() -> str:
    return PAGE_SOURCE.read_text(encoding="utf-8")


def test_github_dashboard_page_inserts_workspace_root_for_execution_imports():
    source = _source()

    assert "WORKSPACE_ROOT = Path(__file__).resolve().parents[2]" in source
    assert "sys.path.insert(0, str(WORKSPACE_ROOT))" in source
    assert "Path(__file__).resolve().parent.parent" not in source


def test_github_dashboard_page_surfaces_release_boundary_before_remote_stats():
    source = _source()

    assert 'page_title="GitHub 운영 - Joolife"' in source
    assert 'st.title("GitHub 운영 현황")' in source
    assert 'st.subheader("릴리스 경계")' in source
    assert "root-quality-gate" in source
    assert "active-project-matrix" in source
    assert "명시적 승인 전 push하지 말고" in source
    assert "`GITHUB_PERSONAL_ACCESS_TOKEN`이 없어" in source
    assert "GitHub activity & repository stats" not in source
    assert 'st.title("GitHub Dashboard")' not in source


def test_github_dashboard_page_hides_plotly_modebar_and_uses_current_width_api():
    source = _source()

    assert 'PLOTLY_CHART_CONFIG = {"displayModeBar": False, "displaylogo": False, "responsive": True}' in source
    assert 'st.plotly_chart(fig, width="stretch", config=PLOTLY_CHART_CONFIG)' in source
    assert "use_container_width=True" not in source


def test_github_dashboard_page_has_mobile_touch_target_css():
    source = _source()

    assert "def _inject_mobile_touch_target_styles()" in source
    assert 'div[data-testid="stSelectbox"] [role="combobox"]' in source
    assert 'div[data-testid="stSlider"] [role="slider"]' in source
    assert 'div[data-testid="stExpander"] summary' in source
    assert "min-height: 44px !important" in source
    assert "min-width: 44px !important" in source
