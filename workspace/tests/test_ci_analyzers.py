from __future__ import annotations

from execution._ci_analyzers import BaseAnalyzer, JSAnalyzer, _make_issue


def test_make_issue_preserves_model_fields() -> None:
    issue = _make_issue(
        file="sample.py",
        line=3,
        column=9,
        category="readability",
        severity="low",
        rule_id="T001",
        message="message",
        code_snippet="snippet",
        suggestion_hint="hint",
    )

    assert issue.file == "sample.py"
    assert issue.line == 3
    assert issue.column == 9
    assert issue.rule_id == "T001"
    assert issue.suggestion_hint == "hint"


def test_base_analyzer_shared_issue_helpers_keep_generic_rules() -> None:
    analyzer = BaseAnalyzer()
    source = "\n".join(
        [
            "# TODO track this",
            "api_key = 'abcdefghijklmnopqrst'",
            "url = 'https://user:password@example.com/path'",
        ]
    )

    issues, metrics = analyzer.analyze(source, "sample.py")
    by_rule = {issue.rule_id for issue in issues}

    assert {"GEN003", "GEN004"}.issubset(by_rule)
    assert metrics.total_lines == 3
    assert metrics.code_lines == 2


def test_js_analyzer_rule_table_still_uses_shared_scan_path() -> None:
    issues, metrics = JSAnalyzer().analyze("var answer = 42\n", "app.js")

    assert [issue.rule_id for issue in issues] == ["JS001"]
    assert issues[0].message == "'var' is function-scoped. Use 'let' or 'const'."
    assert metrics.function_count == 0
