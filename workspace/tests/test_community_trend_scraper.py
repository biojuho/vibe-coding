"""community_trend_scraper 래퍼 테스트."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import execution.community_trend_scraper as cts


# ---------------------------------------------------------------------------
# _load_config
# ---------------------------------------------------------------------------
def test_load_config_missing_file():
    result = cts._load_config("/nonexistent/config.yaml")
    assert result == {}


def test_load_config_valid(tmp_path):
    cfg = tmp_path / "config.yaml"
    cfg.write_text("dopamine_bot:\n  scrapers:\n    fmkorea:\n      enabled: true\n", encoding="utf-8")
    result = cts._load_config(str(cfg))
    assert result["dopamine_bot"]["scrapers"]["fmkorea"]["enabled"] is True


def test_load_config_invalid_yaml(tmp_path):
    cfg = tmp_path / "config.yaml"
    cfg.write_bytes(b"\x80\x81\x82")  # invalid yaml
    result = cts._load_config(str(cfg))
    assert result == {}


# ---------------------------------------------------------------------------
# get_community_trends — 기본 동작
# ---------------------------------------------------------------------------
def test_get_community_trends_no_scrapers():
    """스크래퍼가 모두 None이면 빈 리스트."""
    with patch.object(cts, "_FMKoreaScraper", None), patch.object(cts, "_PpomppuScraper", None):
        result = cts.get_community_trends()
    assert result == []


def test_get_community_trends_unknown_source():
    result = cts.get_community_trends(sources=["unknown_site"])
    assert result == []


def test_get_community_trends_fmkorea_only():
    mock_cls = MagicMock()
    mock_instance = MagicMock()
    mock_instance.scrape.return_value = [
        {
            "title": "FM 트렌드1",
            "source": "fmkorea",
            "views": "50000",
            "recommendations": "200",
            "link": "https://fmkorea.com/1",
        },
        {
            "title": "FM 트렌드2",
            "source": "fmkorea",
            "views": "30000",
            "recommendations": "100",
            "link": "https://fmkorea.com/2",
        },
    ]
    mock_cls.return_value = mock_instance

    with patch.object(cts, "_FMKoreaScraper", mock_cls), patch.object(cts, "_PpomppuScraper", None):
        result = cts.get_community_trends(sources=["fmkorea"])
    assert len(result) == 2
    assert result[0]["source"] == "fmkorea"


def test_get_community_trends_ppomppu_only():
    mock_cls = MagicMock()
    mock_instance = MagicMock()
    mock_instance.scrape.return_value = [
        {
            "title": "뽐뿌 핫딜",
            "source": "ppomppu",
            "views": "10000",
            "recommendations": "50",
            "link": "https://ppomppu.co.kr/1",
        },
    ]
    mock_cls.return_value = mock_instance

    with patch.object(cts, "_FMKoreaScraper", None), patch.object(cts, "_PpomppuScraper", mock_cls):
        result = cts.get_community_trends(sources=["ppomppu"])
    assert len(result) == 1
    assert result[0]["source"] == "ppomppu"


def test_get_community_trends_both_sources():
    fm_cls = MagicMock()
    fm_cls.return_value.scrape.return_value = [
        {"title": "FM1", "source": "fmkorea", "views": "0", "recommendations": "0", "link": ""}
    ]
    pp_cls = MagicMock()
    pp_cls.return_value.scrape.return_value = [
        {"title": "PP1", "source": "ppomppu", "views": "0", "recommendations": "0", "link": ""}
    ]

    with patch.object(cts, "_FMKoreaScraper", fm_cls), patch.object(cts, "_PpomppuScraper", pp_cls):
        result = cts.get_community_trends()
    assert len(result) == 2
    titles = {p["title"] for p in result}
    assert titles == {"FM1", "PP1"}


def test_get_community_trends_source_failure_continues():
    """한 소스가 예외를 던져도 다른 소스는 정상 수집."""
    fm_cls = MagicMock()
    fm_cls.return_value.scrape.side_effect = RuntimeError("네트워크 오류")
    pp_cls = MagicMock()
    pp_cls.return_value.scrape.return_value = [
        {"title": "PP1", "source": "ppomppu", "views": "0", "recommendations": "0", "link": ""}
    ]

    with patch.object(cts, "_FMKoreaScraper", fm_cls), patch.object(cts, "_PpomppuScraper", pp_cls):
        result = cts.get_community_trends()
    assert len(result) == 1
    assert result[0]["title"] == "PP1"


def test_get_community_trends_limit():
    mock_cls = MagicMock()
    mock_cls.return_value.scrape.return_value = [
        {"title": f"T{i}", "source": "fmkorea", "views": "0", "recommendations": "0", "link": ""} for i in range(20)
    ]

    with patch.object(cts, "_FMKoreaScraper", mock_cls), patch.object(cts, "_PpomppuScraper", None):
        result = cts.get_community_trends(limit=5)
    assert len(result) == 5


def test_get_community_trends_disabled_source(tmp_path):
    """config에서 비활성화된 소스는 건너뜀."""
    cfg = tmp_path / "config.yaml"
    cfg.write_text(
        "dopamine_bot:\n  scrapers:\n    fmkorea:\n      enabled: false\n    ppomppu:\n      enabled: false\n",
        encoding="utf-8",
    )
    fm_cls = MagicMock()
    pp_cls = MagicMock()

    with patch.object(cts, "_FMKoreaScraper", fm_cls), patch.object(cts, "_PpomppuScraper", pp_cls):
        result = cts.get_community_trends(config_path=str(cfg))
    assert result == []
    fm_cls.return_value.scrape.assert_not_called()
    pp_cls.return_value.scrape.assert_not_called()


# ---------------------------------------------------------------------------
# get_community_trend_titles
# ---------------------------------------------------------------------------
def test_get_community_trend_titles_returns_strings():
    mock_cls = MagicMock()
    mock_cls.return_value.scrape.return_value = [
        {"title": "제목A", "source": "fmkorea", "views": "0", "recommendations": "0", "link": ""},
        {"title": "제목B", "source": "fmkorea", "views": "0", "recommendations": "0", "link": ""},
    ]

    with patch.object(cts, "_FMKoreaScraper", mock_cls), patch.object(cts, "_PpomppuScraper", None):
        titles = cts.get_community_trend_titles(sources=["fmkorea"])
    assert titles == ["제목A", "제목B"]
    assert all(isinstance(t, str) for t in titles)


def test_get_community_trend_titles_empty_on_failure():
    with patch.object(cts, "_FMKoreaScraper", None), patch.object(cts, "_PpomppuScraper", None):
        titles = cts.get_community_trend_titles()
    assert titles == []


def test_get_community_trend_titles_skips_empty():
    mock_cls = MagicMock()
    mock_cls.return_value.scrape.return_value = [
        {"title": "있는제목", "source": "fmkorea", "views": "0", "recommendations": "0", "link": ""},
        {"title": "", "source": "fmkorea", "views": "0", "recommendations": "0", "link": ""},
        {"source": "fmkorea", "views": "0", "recommendations": "0", "link": ""},
    ]

    with patch.object(cts, "_FMKoreaScraper", mock_cls), patch.object(cts, "_PpomppuScraper", None):
        titles = cts.get_community_trend_titles(sources=["fmkorea"])
    assert titles == ["있는제목"]


# ---------------------------------------------------------------------------
# main() CLI function (lines 125-145)
# ---------------------------------------------------------------------------


def test_main_json_output(monkeypatch, capsys):
    """main()이 --json 플래그로 JSON 출력."""
    import json as _json

    mock_cls = MagicMock()
    mock_cls.return_value.scrape.return_value = [
        {"title": "CLI제목", "source": "fmkorea", "views": "100", "recommendations": "5", "link": "https://x.com/1"},
    ]

    monkeypatch.setattr("sys.argv", ["community_trend_scraper.py", "--json", "--source", "fmkorea"])
    with patch.object(cts, "_FMKoreaScraper", mock_cls), patch.object(cts, "_PpomppuScraper", None):
        ret = cts.main()
    assert ret == 0
    captured = capsys.readouterr().out
    data = _json.loads(captured)
    assert isinstance(data, list)
    assert data[0]["title"] == "CLI제목"


def test_main_text_output(monkeypatch, capsys):
    """main()이 기본(텍스트) 형식으로 출력."""
    mock_cls = MagicMock()
    mock_cls.return_value.scrape.return_value = [
        {"title": "텍스트제목", "source": "ppomppu", "views": "200", "recommendations": "10", "link": ""},
    ]

    monkeypatch.setattr("sys.argv", ["community_trend_scraper.py", "--source", "ppomppu", "--limit", "5"])
    with patch.object(cts, "_FMKoreaScraper", None), patch.object(cts, "_PpomppuScraper", mock_cls):
        ret = cts.main()
    assert ret == 0
    captured = capsys.readouterr().out
    assert "1건 수집" in captured
    assert "텍스트제목" in captured
    assert "ppomppu" in captured


def test_main_no_source_flag(monkeypatch, capsys):
    """main()이 --source 없이 모든 소스 수집."""
    monkeypatch.setattr("sys.argv", ["community_trend_scraper.py", "--json"])
    with patch.object(cts, "_FMKoreaScraper", None), patch.object(cts, "_PpomppuScraper", None):
        ret = cts.main()
    assert ret == 0
    captured = capsys.readouterr().out
    assert "[]" in captured
