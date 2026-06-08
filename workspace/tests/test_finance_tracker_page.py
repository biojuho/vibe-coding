from __future__ import annotations

import importlib
import sys
import types
from datetime import date
from pathlib import Path

WORKSPACE_ROOT = Path(__file__).resolve().parents[1]


class _FakeContext:
    def __init__(self, streamlit_module: "_FakeStreamlit") -> None:
        self._streamlit = streamlit_module

    def __enter__(self) -> "_FakeContext":
        return self

    def __exit__(self, *_args: object) -> None:
        return None

    def __getattr__(self, name: str):
        return getattr(self._streamlit, name)


class _FakeStreamlit(types.ModuleType):
    def __init__(self) -> None:
        super().__init__("streamlit")
        self.events: list[tuple[str, object, dict]] = []

    def _record(self, name: str, payload: object = None, **kwargs: object) -> None:
        self.events.append((name, payload, kwargs))

    def set_page_config(self, **kwargs: object) -> None:
        self._record("set_page_config", kwargs)

    def markdown(self, payload: object, **kwargs: object) -> None:
        self._record("markdown", payload, **kwargs)

    def plotly_chart(self, payload: object, **kwargs: object) -> None:
        self._record("plotly_chart", payload, **kwargs)

    def columns(self, spec: object) -> list[_FakeContext]:
        count = spec if isinstance(spec, int) else len(spec)
        return [_FakeContext(self) for _ in range(count)]

    def form(self, _key: str) -> _FakeContext:
        return _FakeContext(self)

    def text_input(self, _label: str, value: str = "", **_kwargs: object) -> str:
        return value

    def selectbox(self, _label: str, options: list[str], **_kwargs: object) -> str:
        return options[0]

    def number_input(self, _label: str, **kwargs: object) -> int:
        return int(kwargs.get("value", kwargs.get("min_value", 0)) or 0)

    def form_submit_button(self, *_args: object, **_kwargs: object) -> bool:
        return False

    def button(self, *_args: object, **_kwargs: object) -> bool:
        return False

    def checkbox(self, *_args: object, **_kwargs: object) -> bool:
        return False

    def download_button(self, *args: object, **kwargs: object) -> None:
        self._record("download_button", args[0] if args else None, **kwargs)

    def stop(self) -> None:
        raise RuntimeError("streamlit stop called")

    def __getattr__(self, name: str):
        def _fallback(payload: object = None, *args: object, **kwargs: object) -> None:
            if args:
                kwargs["_args"] = args
            self._record(name, payload, **kwargs)

        return _fallback


def _fake_finance_db() -> types.ModuleType:
    module = types.ModuleType("execution.finance_db")
    module.CATEGORIES = {"expense": ["food"], "income": ["salary"]}
    module.init_db = lambda: None
    module.get_monthly_summary = lambda _month: {"income": 0, "expense": 0, "net": 0}
    module.check_budget_alerts = lambda _month: []
    module.get_category_breakdown = lambda _month: []
    module.get_trend = lambda _months: []
    module.get_transactions = lambda **_kwargs: []
    module.get_budgets = lambda: []
    module.export_csv = lambda _month=None: "type,amount\n"
    module.add_transaction = lambda *_args, **_kwargs: 1
    module.delete_transaction = lambda *_args, **_kwargs: True
    module.set_budget = lambda *_args, **_kwargs: None
    return module


class _FakeFigure:
    def add_trace(self, *_args: object, **_kwargs: object) -> None:
        return None

    def update_layout(self, **_kwargs: object) -> None:
        return None

    def update_xaxes(self, **_kwargs: object) -> None:
        return None

    def update_yaxes(self, **_kwargs: object) -> None:
        return None


def _install_fake_plotly(monkeypatch) -> None:
    plotly = types.ModuleType("plotly")
    express = types.ModuleType("plotly.express")
    graph_objects = types.ModuleType("plotly.graph_objects")
    express.pie = lambda **_kwargs: _FakeFigure()
    graph_objects.Figure = _FakeFigure
    graph_objects.Scatter = lambda **kwargs: ("scatter", kwargs)
    plotly.express = express
    plotly.graph_objects = graph_objects
    monkeypatch.setitem(sys.modules, "plotly", plotly)
    monkeypatch.setitem(sys.modules, "plotly.express", express)
    monkeypatch.setitem(sys.modules, "plotly.graph_objects", graph_objects)


def _import_finance_tracker(monkeypatch):
    module_name = "execution.pages.finance_tracker"
    sys.modules.pop(module_name, None)
    fake_streamlit = _FakeStreamlit()
    monkeypatch.setitem(sys.modules, "streamlit", fake_streamlit)
    monkeypatch.setitem(sys.modules, "execution.finance_db", _fake_finance_db())
    _install_fake_plotly(monkeypatch)
    module = importlib.import_module(module_name)
    return module, fake_streamlit


def test_finance_tracker_helpers_execute_with_fake_streamlit(monkeypatch) -> None:
    module, fake_streamlit = _import_finance_tracker(monkeypatch)
    fake_streamlit.events.clear()

    assert module._format_transaction_type("income") == module.TYPE_LABELS["income"]
    assert module._format_transaction_type("other") == "other"
    assert module._month_start("2026-06") == date(2026, 6, 1)
    assert module._format_month_label("2026-06") == "2026.06"
    assert module._parse_transaction_date(" 2026-06-08 ") == "2026-06-08"
    assert module._parse_transaction_date("2026/06/08") is None

    module._inject_finance_mobile_css()
    assert fake_streamlit.events[-1][0] == "markdown"
    assert fake_streamlit.events[-1][2]["unsafe_allow_html"] is True

    figure = object()
    module._render_plotly_chart(figure)
    assert fake_streamlit.events[-1] == (
        "plotly_chart",
        figure,
        {"width": "stretch", "config": module.PLOTLY_CHART_CONFIG},
    )


def test_finance_tracker_inserts_workspace_root_for_direct_streamlit_execution() -> None:
    source = (WORKSPACE_ROOT / "execution" / "pages" / "finance_tracker.py").read_text(encoding="utf-8")

    assert "WORKSPACE_ROOT = Path(__file__).resolve().parents[2]" in source
    assert "sys.path.insert(0, str(WORKSPACE_ROOT))" in source
    assert "Path(__file__).resolve().parent.parent)" not in source


def test_finance_tracker_injects_mobile_touch_target_css() -> None:
    source = (WORKSPACE_ROOT / "execution" / "pages" / "finance_tracker.py").read_text(encoding="utf-8")

    assert "MOBILE_TOUCH_TARGET_CSS" in source
    assert "@media (max-width: 640px)" in source
    assert "min-height: 44px !important" in source
    assert 'div[data-testid="stDownloadButton"] button' in source
    assert 'div[data-testid="stFormSubmitButton"] button' in source
    assert 'div[data-testid="stHeader"] button' in source
    assert 'div[data-testid="stHeaderActionElements"] a' in source
    assert 'div[data-baseweb="select"]' in source
    assert 'a[href^="#"]' in source
    assert "unsafe_allow_html=True" in source


def test_finance_tracker_uses_current_chart_and_stretch_button_contracts() -> None:
    source = (WORKSPACE_ROOT / "execution" / "pages" / "finance_tracker.py").read_text(encoding="utf-8")

    assert 'st.plotly_chart(fig, width="stretch", config=PLOTLY_CHART_CONFIG)' in source
    assert '"displayModeBar": False' in source
    assert 'st.form_submit_button("추가", type="primary", width="stretch")' in source
    assert 'st.button("삭제", key=f"del_tx_{tx[\'id\']}", width="stretch")' in source
    assert 'icon=":material/delete:"' not in source
    assert "st.download_button(" in source
    assert 'width="stretch",' in source


def test_finance_tracker_keeps_quick_add_before_charts() -> None:
    source = (WORKSPACE_ROOT / "execution" / "pages" / "finance_tracker.py").read_text(encoding="utf-8")

    assert source.index('st.subheader("거래 추가", anchor=False)') < source.index(
        'st.subheader("분류별 지출", anchor=False)'
    )
    assert source.index('st.subheader("거래 추가", anchor=False)') < source.index(
        'st.subheader("6개월 추이", anchor=False)'
    )
    assert source.index('st.subheader("분류별 지출", anchor=False)') < source.index(
        'st.subheader("거래 내역", anchor=False)'
    )


def test_finance_tracker_uses_korean_operator_copy() -> None:
    source = (WORKSPACE_ROOT / "execution" / "pages" / "finance_tracker.py").read_text(encoding="utf-8")

    assert 'st.set_page_config(page_title="가계부 - Joolife"' in source
    assert 'st.title("💵 가계부", anchor=False)' in source
    assert 'st.caption("수입과 지출을 한 화면에서 기록하고 월별 흐름을 확인합니다")' in source
    assert 'st.metric("수입"' in source
    assert 'st.metric("지출"' in source
    assert 'st.metric("잔액"' in source
    assert 'st.selectbox("구분", ["expense", "income"], format_func=_format_transaction_type)' in source
    assert 'st.text_input("날짜 (YYYY-MM-DD)", value=date.today().isoformat(), placeholder="2026-06-08")' in source
    assert "st.date_input(" not in source
    assert 'show_budget_settings = st.checkbox("예산 설정 열기")' in source
    assert 'st.expander("예산 설정")' not in source
    assert 'st.error("날짜는 YYYY-MM-DD 형식으로 입력하세요.")' in source
    assert 'st.warning("금액을 0보다 크게 입력하세요.")' in source
    assert 'st.download_button(\n    "CSV 다운로드",' in source

    forbidden_visible_copy = [
        "Finance Tracker",
        "Personal income & expense management",
        "Add Transaction",
        "Category Breakdown",
        "6-Month Trend",
        "Transaction History",
        "Budget Settings",
        "Download CSV",
        "Save Budgets",
        "Transaction #",
    ]
    for text in forbidden_visible_copy:
        assert text not in source


def test_finance_tracker_disables_streamlit_heading_anchor_links() -> None:
    source = (WORKSPACE_ROOT / "execution" / "pages" / "finance_tracker.py").read_text(encoding="utf-8")

    assert source.count("anchor=False") == 5
    assert 'st.title("💵 가계부", anchor=False)' in source
    assert 'st.subheader("거래 추가", anchor=False)' in source
    assert 'st.subheader("분류별 지출", anchor=False)' in source
    assert 'st.subheader("6개월 추이", anchor=False)' in source
    assert 'st.subheader("거래 내역", anchor=False)' in source


def test_finance_tracker_formats_monthly_trend_axis_for_mobile() -> None:
    source = (WORKSPACE_ROOT / "execution" / "pages" / "finance_tracker.py").read_text(encoding="utf-8")

    assert 'trend_months = [_month_start(t["month"]) for t in trend]' in source
    assert 'trend_labels = [_format_month_label(t["month"]) for t in trend]' in source
    assert 'title="월별 수입/지출"' in source
    assert 'fig.update_xaxes(dtick="M1", tickformat="%Y.%m", ticklabelmode="period", title_text="월")' in source
    assert 'fig.update_yaxes(tickprefix="₩", separatethousands=True, title_text="금액")' in source
    assert 'hovertemplate="%{customdata}<br>수입: ₩%{y:,.0f}<extra></extra>"' in source
