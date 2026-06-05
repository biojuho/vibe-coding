from __future__ import annotations

from execution._ci_analyzers import BaseAnalyzer, JSAnalyzer, PythonAnalyzer, _make_issue


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


def test_python_analyzer_string_concat_loop_only_flags_stringish_augassigns() -> None:
    source = "\n".join(
        [
            "def render(items):",
            "    total = 0",
            "    text = ''",
            "    for item in items:",
            "        total += 1",
            "        text += str(item)",
            "    return text",
        ]
    )

    issues, _metrics = PythonAnalyzer().analyze(source, "sample.py")
    string_concat_issues = [issue for issue in issues if issue.rule_id == "PY009"]

    assert len(string_concat_issues) == 1
    assert string_concat_issues[0].line == 6
    assert string_concat_issues[0].code_snippet == "text += ..."


def test_python_analyzer_naming_helpers_keep_existing_exemptions() -> None:
    source = "\n".join(
        [
            "class bad_class:",
            "    pass",
            "",
            "def BadName(value):",
            "    return value",
            "",
            "def _PrivateName(value):",
            "    return value",
            "",
            "def visit_Name(node):",
            "    return node",
        ]
    )

    issues, _metrics = PythonAnalyzer().analyze(source, "sample.py")
    naming_issues = [(issue.rule_id, issue.line) for issue in issues if issue.rule_id in {"PY003", "PY004"}]

    assert naming_issues == [("PY004", 1), ("PY003", 4)]


def test_python_analyzer_type_hint_helper_flags_only_public_missing_args() -> None:
    source = "\n".join(
        [
            "def public_missing(value):",
            "    return value",
            "",
            "def public_no_args():",
            "    return 1",
            "",
            "def public_typed(value: str) -> str:",
            "    return value",
            "",
            "def _private_missing(value):",
            "    return value",
        ]
    )

    issues, _metrics = PythonAnalyzer().analyze(source, "sample.py")
    type_hint_issues = [issue for issue in issues if issue.rule_id == "PY007"]

    assert len(type_hint_issues) == 1
    assert type_hint_issues[0].line == 1
