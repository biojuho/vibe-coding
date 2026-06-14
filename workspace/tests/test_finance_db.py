from __future__ import annotations

import csv
import importlib
import io
import sys
import types

import execution.finance_db as fdb


def _patch_db(monkeypatch, tmp_path):
    monkeypatch.setattr(fdb, "DB_PATH", tmp_path / "finance.db")
    fdb.init_db()


# ---------------------------------------------------------------------------
# init_db / schema
# ---------------------------------------------------------------------------


def test_init_db_creates_tables(monkeypatch, tmp_path):
    monkeypatch.setattr(fdb, "DB_PATH", tmp_path / "finance.db")
    fdb.init_db()

    import sqlite3

    conn = sqlite3.connect(str(tmp_path / "finance.db"))
    tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
    assert "transactions" in tables
    assert "budgets" in tables
    conn.close()


def test_init_db_idempotent(monkeypatch, tmp_path):
    monkeypatch.setattr(fdb, "DB_PATH", tmp_path / "finance.db")
    fdb.init_db()
    fdb.init_db()  # 두 번 호출해도 오류 없어야 함


# ---------------------------------------------------------------------------
# add_transaction / get_transactions
# ---------------------------------------------------------------------------


def test_add_income_transaction(monkeypatch, tmp_path):
    _patch_db(monkeypatch, tmp_path)
    tid = fdb.add_transaction("income", 300000, "급여", "월급", "2026-02-01")
    assert isinstance(tid, int) and tid > 0

    rows = fdb.get_transactions()
    assert len(rows) == 1
    assert rows[0]["type"] == "income"
    assert rows[0]["amount"] == 300000
    assert rows[0]["category"] == "급여"


def test_add_expense_transaction(monkeypatch, tmp_path):
    _patch_db(monkeypatch, tmp_path)
    tid = fdb.add_transaction("expense", 12000, "식비", "점심", "2026-02-15")
    assert tid > 0
    rows = fdb.get_transactions()
    assert rows[0]["type"] == "expense"


def test_add_transaction_default_date(monkeypatch, tmp_path):
    _patch_db(monkeypatch, tmp_path)
    from datetime import date

    fdb.add_transaction("expense", 5000, "교통")
    rows = fdb.get_transactions()
    assert rows[0]["date"] == date.today().isoformat()


def test_get_transactions_filter_by_month(monkeypatch, tmp_path):
    _patch_db(monkeypatch, tmp_path)
    fdb.add_transaction("income", 100, "부업", dt="2026-01-10")
    fdb.add_transaction("expense", 200, "식비", dt="2026-02-05")

    jan_rows = fdb.get_transactions(month="2026-01")
    feb_rows = fdb.get_transactions(month="2026-02")
    assert len(jan_rows) == 1
    assert len(feb_rows) == 1


def test_get_transactions_filter_by_category(monkeypatch, tmp_path):
    _patch_db(monkeypatch, tmp_path)
    fdb.add_transaction("expense", 5000, "식비", dt="2026-02-01")
    fdb.add_transaction("expense", 3000, "교통", dt="2026-02-02")

    food = fdb.get_transactions(category="식비")
    assert all(r["category"] == "식비" for r in food)
    assert len(food) == 1


def test_get_transactions_limit(monkeypatch, tmp_path):
    _patch_db(monkeypatch, tmp_path)
    for i in range(10):
        fdb.add_transaction("expense", float(i * 1000), "기타지출", dt="2026-02-01")
    rows = fdb.get_transactions(limit=3)
    assert len(rows) == 3


# ---------------------------------------------------------------------------
# delete_transaction
# ---------------------------------------------------------------------------


def test_delete_transaction(monkeypatch, tmp_path):
    _patch_db(monkeypatch, tmp_path)
    tid = fdb.add_transaction("expense", 9000, "구독", dt="2026-02-10")
    assert len(fdb.get_transactions()) == 1

    result = fdb.delete_transaction(tid)
    assert result is True
    assert len(fdb.get_transactions()) == 0


# ---------------------------------------------------------------------------
# get_monthly_summary
# ---------------------------------------------------------------------------


def test_monthly_summary_net(monkeypatch, tmp_path):
    _patch_db(monkeypatch, tmp_path)
    fdb.add_transaction("income", 500000, "급여", dt="2026-02-01")
    fdb.add_transaction("expense", 120000, "식비", dt="2026-02-15")
    fdb.add_transaction("expense", 30000, "교통", dt="2026-02-20")

    summary = fdb.get_monthly_summary("2026-02")
    assert summary["income"] == 500000
    assert summary["expense"] == 150000
    assert summary["net"] == 350000
    assert summary["month"] == "2026-02"


def test_monthly_summary_empty_month(monkeypatch, tmp_path):
    _patch_db(monkeypatch, tmp_path)
    summary = fdb.get_monthly_summary("2099-01")
    assert summary["income"] == 0
    assert summary["expense"] == 0
    assert summary["net"] == 0


# ---------------------------------------------------------------------------
# get_category_breakdown
# ---------------------------------------------------------------------------


def test_category_breakdown(monkeypatch, tmp_path):
    _patch_db(monkeypatch, tmp_path)
    fdb.add_transaction("expense", 10000, "식비", dt="2026-02-01")
    fdb.add_transaction("expense", 5000, "식비", dt="2026-02-02")
    fdb.add_transaction("expense", 3000, "교통", dt="2026-02-03")

    breakdown = fdb.get_category_breakdown("2026-02")
    totals = {r["category"]: r["total"] for r in breakdown}
    assert totals["식비"] == 15000
    assert totals["교통"] == 3000


# ---------------------------------------------------------------------------
# get_trend
# ---------------------------------------------------------------------------


def test_get_trend_returns_list(monkeypatch, tmp_path):
    _patch_db(monkeypatch, tmp_path)
    fdb.add_transaction("income", 100000, "급여", dt="2026-01-01")
    fdb.add_transaction("expense", 40000, "식비", dt="2026-02-01")

    trend = fdb.get_trend(months=6)
    assert isinstance(trend, list)
    for item in trend:
        assert "month" in item
        assert "net" in item


# ---------------------------------------------------------------------------
# budget / check_budget_alerts
# ---------------------------------------------------------------------------


def test_set_and_get_budget(monkeypatch, tmp_path):
    _patch_db(monkeypatch, tmp_path)
    fdb.set_budget("식비", 200000)
    budgets = fdb.get_budgets()
    assert any(b["category"] == "식비" and b["monthly_limit"] == 200000 for b in budgets)


def test_set_budget_upsert(monkeypatch, tmp_path):
    _patch_db(monkeypatch, tmp_path)
    fdb.set_budget("식비", 100000)
    fdb.set_budget("식비", 250000)  # upsert
    budgets = fdb.get_budgets()
    food = [b for b in budgets if b["category"] == "식비"]
    assert len(food) == 1
    assert food[0]["monthly_limit"] == 250000


def test_budget_alert_triggers_at_80_percent(monkeypatch, tmp_path):
    _patch_db(monkeypatch, tmp_path)
    fdb.set_budget("식비", 100000)
    fdb.add_transaction("expense", 85000, "식비", dt="2026-02-01")  # 85%

    alerts = fdb.check_budget_alerts("2026-02")
    assert len(alerts) == 1
    assert alerts[0]["category"] == "식비"
    assert alerts[0]["ratio"] == 0.85
    assert alerts[0]["over"] is False


def test_budget_alert_over_budget(monkeypatch, tmp_path):
    _patch_db(monkeypatch, tmp_path)
    fdb.set_budget("쇼핑", 50000)
    fdb.add_transaction("expense", 70000, "쇼핑", dt="2026-02-10")

    alerts = fdb.check_budget_alerts("2026-02")
    assert alerts[0]["over"] is True


def test_budget_alert_below_threshold(monkeypatch, tmp_path):
    _patch_db(monkeypatch, tmp_path)
    fdb.set_budget("의료", 100000)
    fdb.add_transaction("expense", 50000, "의료", dt="2026-02-01")  # 50%

    alerts = fdb.check_budget_alerts("2026-02")
    assert alerts == []


# ---------------------------------------------------------------------------
# export_csv
# ---------------------------------------------------------------------------


def test_export_csv_format(monkeypatch, tmp_path):
    _patch_db(monkeypatch, tmp_path)
    fdb.add_transaction("income", 200000, "급여", "월급", "2026-02-01")
    fdb.add_transaction("expense", 15000, "식비", "저녁", "2026-02-02")

    csv_text = fdb.export_csv(month="2026-02")
    reader = csv.DictReader(io.StringIO(csv_text))
    rows = list(reader)
    assert len(rows) == 2
    categories = {r["category"] for r in rows}
    assert "급여" in categories
    assert "식비" in categories


# ---------------------------------------------------------------------------
# finance_tracker page helpers
# ---------------------------------------------------------------------------


class _FinanceTrackerFakeContext:
    def __init__(self, streamlit_module):
        self._streamlit = streamlit_module

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return None

    def __getattr__(self, name):
        return getattr(self._streamlit, name)


class _FinanceTrackerFakeStreamlit(types.ModuleType):
    def __init__(self):
        super().__init__("streamlit")
        self.events = []

    def _record(self, name, payload=None, **kwargs):
        self.events.append((name, payload, kwargs))

    def set_page_config(self, **kwargs):
        self._record("set_page_config", kwargs)

    def markdown(self, payload, **kwargs):
        self._record("markdown", payload, **kwargs)

    def plotly_chart(self, payload, **kwargs):
        self._record("plotly_chart", payload, **kwargs)

    def columns(self, spec):
        count = spec if isinstance(spec, int) else len(spec)
        return [_FinanceTrackerFakeContext(self) for _ in range(count)]

    def form(self, _key):
        return _FinanceTrackerFakeContext(self)

    def text_input(self, _label, value="", **_kwargs):
        return value

    def selectbox(self, _label, options, **_kwargs):
        return options[0]

    def number_input(self, _label, **kwargs):
        return int(kwargs.get("value", kwargs.get("min_value", 0)) or 0)

    def form_submit_button(self, *_args, **_kwargs):
        return False

    def button(self, *_args, **_kwargs):
        return False

    def checkbox(self, *_args, **_kwargs):
        return False

    def download_button(self, *args, **kwargs):
        self._record("download_button", args[0] if args else None, **kwargs)

    def stop(self):
        raise RuntimeError("streamlit stop called")

    def __getattr__(self, name):
        def fallback(payload=None, *args, **kwargs):
            if args:
                kwargs["_args"] = args
            self._record(name, payload, **kwargs)

        return fallback


class _FinanceTrackerFakeFigure:
    def add_trace(self, *_args, **_kwargs):
        return None

    def update_layout(self, **_kwargs):
        return None

    def update_xaxes(self, **_kwargs):
        return None

    def update_yaxes(self, **_kwargs):
        return None


_FINANCE_TRACKER_STUB_MODULES = (
    "streamlit",
    "execution.finance_db",
    "plotly",
    "plotly.express",
    "plotly.graph_objects",
)


def _fake_finance_db_module():
    fake_finance_db = types.ModuleType("execution.finance_db")
    fake_finance_db.CATEGORIES = {"expense": ["food"], "income": ["salary"]}
    fake_finance_db.init_db = lambda: None
    fake_finance_db.get_monthly_summary = lambda _month: {"income": 0, "expense": 0, "net": 0}
    fake_finance_db.check_budget_alerts = lambda _month: []
    fake_finance_db.get_category_breakdown = lambda _month: []
    fake_finance_db.get_trend = lambda _months: []
    fake_finance_db.get_transactions = lambda **_kwargs: []
    fake_finance_db.get_budgets = lambda: []
    fake_finance_db.export_csv = lambda _month=None: "type,amount\n"
    fake_finance_db.add_transaction = lambda *_args, **_kwargs: 1
    fake_finance_db.delete_transaction = lambda *_args, **_kwargs: True
    fake_finance_db.set_budget = lambda *_args, **_kwargs: None
    return fake_finance_db


def _fake_plotly_modules():
    plotly = types.ModuleType("plotly")
    express = types.ModuleType("plotly.express")
    graph_objects = types.ModuleType("plotly.graph_objects")
    express.pie = lambda **_kwargs: _FinanceTrackerFakeFigure()
    graph_objects.Figure = _FinanceTrackerFakeFigure
    graph_objects.Scatter = lambda **kwargs: ("scatter", kwargs)
    plotly.express = express
    plotly.graph_objects = graph_objects
    return plotly, express, graph_objects


def _restore_modules(originals):
    for name, original in originals.items():
        if original is None:
            sys.modules.pop(name, None)
        else:
            sys.modules[name] = original


def _install_finance_tracker_page_stubs():
    fake_streamlit = _FinanceTrackerFakeStreamlit()
    fake_finance_db = _fake_finance_db_module()
    plotly, express, graph_objects = _fake_plotly_modules()

    originals = {name: sys.modules.get(name) for name in _FINANCE_TRACKER_STUB_MODULES}
    sys.modules["streamlit"] = fake_streamlit
    sys.modules["execution.finance_db"] = fake_finance_db
    sys.modules["plotly"] = plotly
    sys.modules["plotly.express"] = express
    sys.modules["plotly.graph_objects"] = graph_objects
    sys.modules.pop("execution.pages.finance_tracker", None)
    module = importlib.import_module("execution.pages.finance_tracker")
    _restore_modules(originals)
    return module, fake_streamlit


_FINANCE_TRACKER_PAGE, _FINANCE_TRACKER_ST = _install_finance_tracker_page_stubs()

from execution.pages.finance_tracker import (  # noqa: E402
    PLOTLY_CHART_CONFIG,
    TYPE_LABELS,
    _format_month_label,
    _format_transaction_type,
    _inject_finance_mobile_css,
    _month_start,
    _parse_transaction_date,
    _render_plotly_chart,
)


def test_finance_tracker_page_helpers_are_imported_and_executable():
    from datetime import date

    _FINANCE_TRACKER_ST.events.clear()
    assert _format_transaction_type("income") == TYPE_LABELS["income"]
    assert _format_transaction_type("other") == "other"
    assert _month_start("2026-06") == date(2026, 6, 1)
    assert _format_month_label("2026-06") == "2026.06"
    assert _parse_transaction_date(" 2026-06-08 ") == "2026-06-08"
    assert _parse_transaction_date("2026/06/08") is None

    _inject_finance_mobile_css()
    assert _FINANCE_TRACKER_ST.events[-1][0] == "markdown"
    assert _FINANCE_TRACKER_ST.events[-1][2]["unsafe_allow_html"] is True

    figure = object()
    _render_plotly_chart(figure)
    assert _FINANCE_TRACKER_ST.events[-1] == (
        "plotly_chart",
        figure,
        {"width": "stretch", "config": PLOTLY_CHART_CONFIG},
    )


def test_export_csv_no_filter(monkeypatch, tmp_path):
    _patch_db(monkeypatch, tmp_path)
    fdb.add_transaction("income", 100, "부업", dt="2026-01-01")
    fdb.add_transaction("expense", 200, "교통", dt="2026-02-01")

    csv_text = fdb.export_csv()
    reader = csv.DictReader(io.StringIO(csv_text))
    rows = list(reader)
    assert len(rows) == 2
