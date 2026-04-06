"""Tests for pipeline.daily_digest pure formatting and extraction helpers."""

from __future__ import annotations

from pipeline.daily_digest import (
    DailyDigest,
    DigestGenerator,
    DigestEntry,
    _escape_telegram_md,
    format_digest_newsletter,
    format_digest_telegram,
)


# ── _escape_telegram_md ──────────────────────────────────────────────────────


class TestEscapeTelegramMd:
    def test_asterisks(self):
        assert _escape_telegram_md("*bold*") == "\\*bold\\*"

    def test_underscores(self):
        assert _escape_telegram_md("_italic_") == "\\_italic\\_"

    def test_backticks(self):
        assert _escape_telegram_md("`code`") == "\\`code\\`"

    def test_brackets(self):
        assert _escape_telegram_md("[link]") == "\\[link\\]"

    def test_no_special_chars(self):
        assert _escape_telegram_md("hello world") == "hello world"

    def test_mixed(self):
        result = _escape_telegram_md("*bold* and _italic_ and [link]")
        assert "\\" in result
        assert "\\*" in result
        assert "\\_" in result
        assert "\\[" in result


# ── Notion property extractors ───────────────────────────────────────────────


class TestNotionExtractors:
    def test_extract_title_primary_key(self):
        props = {"콘텐츠": {"title": [{"plain_text": "제목입니다"}]}}
        assert DigestGenerator._extract_title(props) == "제목입니다"

    def test_extract_title_name_fallback(self):
        props = {"Name": {"title": [{"plain_text": "이름"}]}}
        assert DigestGenerator._extract_title(props) == "이름"

    def test_extract_title_missing(self):
        assert DigestGenerator._extract_title({}) == ""

    def test_extract_title_empty_array(self):
        props = {"콘텐츠": {"title": []}}
        assert DigestGenerator._extract_title(props) == ""

    def test_extract_rich_text(self):
        props = {"URL": {"rich_text": [{"plain_text": "https://example.com"}]}}
        assert DigestGenerator._extract_rich_text(props, "URL") == "https://example.com"

    def test_extract_rich_text_empty(self):
        assert DigestGenerator._extract_rich_text({}, "URL") == ""

    def test_extract_select(self):
        props = {"토픽": {"select": {"name": "경제"}}}
        assert DigestGenerator._extract_select(props, "토픽") == "경제"

    def test_extract_select_none(self):
        props = {"토픽": {"select": None}}
        assert DigestGenerator._extract_select(props, "토픽") == ""

    def test_extract_number(self):
        props = {"점수": {"number": 85}}
        assert DigestGenerator._extract_number(props, "점수") == 85.0

    def test_extract_number_none(self):
        props = {"점수": {"number": None}}
        assert DigestGenerator._extract_number(props, "점수") == 0.0

    def test_extract_number_missing(self):
        assert DigestGenerator._extract_number({}, "점수") == 0.0


# ── _compute_topic_distribution ──────────────────────────────────────────────


class TestComputeTopicDistribution:
    def _make_generator(self):
        return DigestGenerator.__new__(DigestGenerator)

    def test_basic_aggregation(self):
        gen = self._make_generator()
        entries = [
            DigestEntry("t1", "u1", "s1", "경제", "분노", 80),
            DigestEntry("t2", "u2", "s2", "경제", "공감", 70),
            DigestEntry("t3", "u3", "s3", "IT", "웃김", 60),
        ]
        dist = gen._compute_topic_distribution(entries)
        assert dist["경제"] == 2
        assert dist["IT"] == 1
        # Sorted desc
        keys = list(dist.keys())
        assert keys[0] == "경제"

    def test_empty_entries(self):
        gen = self._make_generator()
        assert gen._compute_topic_distribution([]) == {}

    def test_missing_topic(self):
        gen = self._make_generator()
        entries = [DigestEntry("t1", "u1", "s1", "", "분노", 50)]
        dist = gen._compute_topic_distribution(entries)
        assert dist.get("unknown") == 1


# ── format_digest_telegram ───────────────────────────────────────────────────


def _make_digest(**overrides) -> DailyDigest:
    defaults = dict(
        date="2026-04-05",
        total_collected=100,
        total_published=15,
        top_posts=[
            DigestEntry("Top *Post* 1", "http://a", "blind", "경제", "분노", 95.0),
            DigestEntry("Post 2", "http://b", "reddit", "IT", "공감", 80.0),
        ],
        trending_emotions=[
            {"keyword": "빡치", "spike_ratio": 2.5, "direction": "rising", "count": 10},
        ],
        topic_distribution={"경제": 5, "IT": 3},
        summary="오늘은 경제 이슈가 화제",
    )
    defaults.update(overrides)
    return DailyDigest(**defaults)


class TestFormatDigestTelegram:
    def test_header(self):
        msg = format_digest_telegram(_make_digest())
        assert "*Daily Digest - 2026-04-05*" in msg
        assert "100" in msg

    def test_summary_escaped(self):
        msg = format_digest_telegram(_make_digest())
        # Summary should appear (escaped)
        assert "오늘은" in msg

    def test_top_posts_escaped(self):
        msg = format_digest_telegram(_make_digest())
        # Asterisks in title should be escaped
        assert "\\*Post\\*" in msg

    def test_trending_rising(self):
        msg = format_digest_telegram(_make_digest())
        assert "빡치" in msg
        assert "!" in msg  # rising indicator

    def test_empty_digest(self):
        msg = format_digest_telegram(
            _make_digest(top_posts=[], trending_emotions=[], topic_distribution={}, summary="")
        )
        assert "2026-04-05" in msg


class TestFormatDigestNewsletter:
    def test_markdown_structure(self):
        text = format_digest_newsletter(_make_digest())
        assert text.startswith("# Daily Content Digest")
        assert "## Top Stories" in text

    def test_bar_graph(self):
        text = format_digest_newsletter(_make_digest())
        assert "++++" in text  # at least some + signs

    def test_trend_arrows(self):
        text = format_digest_newsletter(
            _make_digest(
                trending_emotions=[
                    {"keyword": "up", "spike_ratio": 2.0, "direction": "rising"},
                    {"keyword": "down", "spike_ratio": 0.5, "direction": "falling"},
                    {"keyword": "flat", "spike_ratio": 1.0, "direction": "stable"},
                ]
            )
        )
        assert "^" in text
        assert "v" in text
        assert "=" in text

    def test_empty_newsletter(self):
        text = format_digest_newsletter(_make_digest(top_posts=[], trending_emotions=[], topic_distribution={}))
        assert "Top Stories" not in text
        assert "Topic Breakdown" not in text
