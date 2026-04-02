"""
_ci_analyzers.py — 언어별 정적 분석 Analyzer 모음.

포함 클래스:
- BaseAnalyzer          : 모든 언어 공통 규칙 (GEN*) + _scan_lines/_scan_rules 헬퍼
- PythonAnalyzer        : AST 기반 Python 규칙 (PY*)
- JSAnalyzer            : regex 기반 JS/TS 규칙 (JS*, TS*) — 룰 테이블 방식
- JavaAnalyzer          : regex 기반 Java 규칙 (JV*) — 룰 테이블 방식
- GoAnalyzer            : regex 기반 Go 규칙 (GO*) — 룰 테이블 방식
- CAnalyzer             : regex 기반 C/C++ 규칙 (CC*) — 룰 테이블 방식
"""

from __future__ import annotations

import ast
import re
from pathlib import Path
from typing import List, NamedTuple, Tuple

from execution._ci_models import (
    FUNCTION_COMPLEXITY_LIMIT,
    FUNCTION_LENGTH_LIMIT,
    SECRET_PATTERNS,
    FileMetrics,
    Issue,
)
from execution._ci_utils import (
    _find_embedded_credential_url,
    _first_code_line,
    _in_comment_or_string,
    _python_cyclomatic,
)


# ---------------------------------------------------------------------------
# Rule table entry (used by _scan_rules / _scan_lines)
# ---------------------------------------------------------------------------


class _Rule(NamedTuple):
    pattern: re.Pattern
    category: str
    severity: str
    rule_id: str
    message: str
    suggestion_hint: str
    check_comment: bool = False  # if True, skip when match is inside comment/string
    comment_prefix: str = "//"


# ---------------------------------------------------------------------------
# Base Analyzer (cross-language rules)
# ---------------------------------------------------------------------------


class BaseAnalyzer:
    language = "generic"
    comment_chars = "#"

    def analyze(self, source: str, file_path: str) -> Tuple[List[Issue], FileMetrics]:
        lines = source.split("\n")
        issues = []
        issues.extend(self._check_line_length(lines, file_path))
        issues.extend(self._check_file_length(lines, file_path))
        issues.extend(self._check_todo_fixme(lines, file_path))
        issues.extend(self._check_hardcoded_credentials(lines, file_path))
        metrics = FileMetrics(
            total_lines=len(lines),
            code_lines=sum(1 for ln in lines if ln.strip() and not ln.strip().startswith(self.comment_chars)),
        )
        return issues, metrics

    # ------------------------------------------------------------------
    # Generic helpers: _scan_lines, _scan_rules
    # ------------------------------------------------------------------

    def _scan_lines(
        self,
        lines: List[str],
        fp: str,
        pattern: re.Pattern,
        category: str,
        severity: str,
        rule_id: str,
        message: str,
        suggestion_hint: str,
        check_comment: bool = False,
        comment_prefix: str = "//",
    ) -> List[Issue]:
        """Scan each line for a pattern and emit an Issue per match."""
        issues = []
        for i, line in enumerate(lines, 1):
            m = pattern.search(line)
            if not m:
                continue
            if check_comment and _in_comment_or_string(line, m.start(), comment_prefix):
                continue
            issues.append(
                Issue(
                    file=fp,
                    line=i,
                    column=0,
                    category=category,
                    severity=severity,
                    rule_id=rule_id,
                    message=message,
                    code_snippet=line.strip(),
                    suggestion_hint=suggestion_hint,
                )
            )
        return issues

    def _scan_rules(self, lines: List[str], fp: str, rules: List[_Rule]) -> List[Issue]:
        """Apply a list of _Rule entries to every line and collect issues."""
        issues = []
        for rule in rules:
            issues.extend(
                self._scan_lines(
                    lines,
                    fp,
                    rule.pattern,
                    rule.category,
                    rule.severity,
                    rule.rule_id,
                    rule.message,
                    rule.suggestion_hint,
                    check_comment=rule.check_comment,
                    comment_prefix=rule.comment_prefix,
                )
            )
        return issues

    def _check_line_length(self, lines: List[str], fp: str, limit: int = 120) -> List[Issue]:
        issues = []
        for i, line in enumerate(lines, 1):
            if len(line) > limit:
                issues.append(
                    Issue(
                        file=fp,
                        line=i,
                        column=limit,
                        category="readability",
                        severity="low",
                        rule_id="GEN001",
                        message=f"Line is {len(line)} characters (limit {limit}).",
                        code_snippet=line[:140] + "..." if len(line) > 140 else line,
                        suggestion_hint="Break long lines for readability.",
                    )
                )
        return issues

    def _check_file_length(self, lines: List[str], fp: str, limit: int = 500) -> List[Issue]:
        if len(lines) > limit:
            return [
                Issue(
                    file=fp,
                    line=1,
                    column=0,
                    category="readability",
                    severity="low",
                    rule_id="GEN005",
                    message=f"File has {len(lines)} lines (>{limit}). Consider splitting.",
                    code_snippet="",
                    suggestion_hint="Split into smaller modules.",
                )
            ]
        return []

    # [FIX #6] Only match TODO/FIXME in actual comments, not string literals
    def _check_todo_fixme(self, lines: List[str], fp: str) -> List[Issue]:
        issues = []
        if self.comment_chars == "#":
            pattern = re.compile(r"^\s*#\s*(TODO|FIXME|HACK|XXX)\b", re.IGNORECASE)
        else:
            pattern = re.compile(r"^\s*(?://|/\*)\s*(TODO|FIXME|HACK|XXX)\b", re.IGNORECASE)
        for i, line in enumerate(lines, 1):
            m = pattern.search(line)
            if m:
                issues.append(
                    Issue(
                        file=fp,
                        line=i,
                        column=m.start(),
                        category="readability",
                        severity="medium",
                        rule_id="GEN003",
                        message=f"Unresolved {m.group(0)} comment found.",
                        code_snippet=line.strip(),
                        suggestion_hint="Resolve or track in issue tracker.",
                    )
                )
        return issues

    def _check_hardcoded_credentials(self, lines: List[str], fp: str) -> List[Issue]:
        issues = []
        for i, line in enumerate(lines, 1):
            secret_detected = False
            for pat in SECRET_PATTERNS:
                if pat.search(line):
                    issues.append(
                        Issue(
                            file=fp,
                            line=i,
                            column=0,
                            category="security",
                            severity="high",
                            rule_id="GEN004",
                            message="Possible hardcoded secret/credential.",
                            code_snippet=line.strip(),
                            suggestion_hint="Use environment variables or a secrets manager.",
                        )
                    )
                    secret_detected = True
                    break
            if secret_detected:
                continue

            credential_url = _find_embedded_credential_url(line)
            if credential_url:
                issues.append(
                    Issue(
                        file=fp,
                        line=i,
                        column=0,
                        category="security",
                        severity="high",
                        rule_id="GEN004",
                        message="URL contains embedded credentials.",
                        code_snippet=credential_url,
                        suggestion_hint="Remove credentials from URLs; use auth headers.",
                    )
                )
        return issues


# ---------------------------------------------------------------------------
# Python Analyzer (AST-based)
# ---------------------------------------------------------------------------


class PythonAnalyzer(BaseAnalyzer):
    language = "python"
    comment_chars = "#"

    def analyze(self, source: str, file_path: str) -> Tuple[List[Issue], FileMetrics]:
        issues, metrics = super().analyze(source, file_path)
        lines = source.split("\n")

        try:
            tree = ast.parse(source, filename=file_path)
        except SyntaxError:
            return issues, metrics

        issues.extend(self._check_star_imports(tree, file_path))
        issues.extend(self._check_bare_except(tree, file_path))
        issues.extend(self._check_eval_exec(tree, file_path))
        issues.extend(self._check_mutable_defaults(tree, file_path))
        issues.extend(self._check_naming(tree, file_path))
        issues.extend(self._check_function_length(tree, file_path))
        issues.extend(self._check_complexity(tree, file_path))
        issues.extend(self._check_nesting_depth(source, lines, file_path))
        issues.extend(self._check_type_hints(tree, file_path))
        issues.extend(self._check_assert_non_test(tree, file_path))
        issues.extend(self._check_sql_injection(lines, file_path))
        issues.extend(self._check_string_concat_loop(tree, file_path))

        funcs = [n for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
        metrics.function_count = len(funcs)
        if funcs:
            lengths = []
            complexities = []
            for f in funcs:
                body_lines = (f.end_lineno or f.lineno) - f.lineno + 1
                lengths.append(body_lines)
                complexities.append(_python_cyclomatic(f))
            metrics.avg_function_length = sum(lengths) / len(lengths)
            metrics.max_complexity = max(complexities) if complexities else 0

        return issues, metrics

    def _check_star_imports(self, tree: ast.AST, fp: str) -> List[Issue]:
        issues = []
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                for alias in node.names:
                    if alias.name == "*":
                        issues.append(
                            Issue(
                                file=fp,
                                line=node.lineno,
                                column=0,
                                category="readability",
                                severity="low",
                                rule_id="PY001",
                                message=f"Star import from '{node.module}' pollutes namespace.",
                                code_snippet=f"from {node.module} import *",
                                suggestion_hint="Import specific names instead.",
                            )
                        )
        return issues

    def _check_bare_except(self, tree: ast.AST, fp: str) -> List[Issue]:
        issues = []
        for node in ast.walk(tree):
            if isinstance(node, ast.ExceptHandler) and node.type is None:
                issues.append(
                    Issue(
                        file=fp,
                        line=node.lineno,
                        column=0,
                        category="security",
                        severity="medium",
                        rule_id="PY013",
                        message="Bare 'except:' catches SystemExit and KeyboardInterrupt.",
                        code_snippet="except:",
                        suggestion_hint="Use 'except Exception:' instead.",
                    )
                )
        return issues

    def _check_eval_exec(self, tree: ast.AST, fp: str) -> List[Issue]:
        issues = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                if node.func.id in ("eval", "exec"):
                    issues.append(
                        Issue(
                            file=fp,
                            line=node.lineno,
                            column=node.col_offset,
                            category="security",
                            severity="high",
                            rule_id="PY011",
                            message=f"Use of {node.func.id}() allows arbitrary code execution.",
                            code_snippet=f"{node.func.id}(...)",
                            suggestion_hint="Use ast.literal_eval() or a safer alternative.",
                        )
                    )
        return issues

    def _check_mutable_defaults(self, tree: ast.AST, fp: str) -> List[Issue]:
        issues = []
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                for default in node.args.defaults + node.args.kw_defaults:
                    if default and isinstance(default, (ast.List, ast.Dict, ast.Set)):
                        issues.append(
                            Issue(
                                file=fp,
                                line=node.lineno,
                                column=0,
                                category="performance",
                                severity="medium",
                                rule_id="PY008",
                                message=f"Mutable default argument in '{node.name}()'. Shared across calls.",
                                code_snippet=f"def {node.name}(...)",
                                suggestion_hint="Use None as default; create mutable inside function body.",
                            )
                        )
        return issues

    # [FIX #4] Exempt ast.NodeVisitor visit_* methods and _-prefixed private classes
    def _check_naming(self, tree: ast.AST, fp: str) -> List[Issue]:
        issues = []
        snake_re = re.compile(r"^[a-z_][a-z0-9_]*$")
        pascal_re = re.compile(r"^_?[A-Z][a-zA-Z0-9]*$")
        visitor_method_re = re.compile(r"^visit_[A-Z]")

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                name = node.name
                if name.startswith("_"):
                    continue
                if visitor_method_re.match(name):
                    continue
                if name.startswith("test"):
                    continue
                if not snake_re.match(name):
                    issues.append(
                        Issue(
                            file=fp,
                            line=node.lineno,
                            column=0,
                            category="readability",
                            severity="low",
                            rule_id="PY003",
                            message=f"Function '{name}' should be snake_case.",
                            code_snippet=f"def {name}(...):",
                            suggestion_hint="Rename to snake_case.",
                        )
                    )
            elif isinstance(node, ast.ClassDef):
                if not pascal_re.match(node.name):
                    issues.append(
                        Issue(
                            file=fp,
                            line=node.lineno,
                            column=0,
                            category="readability",
                            severity="low",
                            rule_id="PY004",
                            message=f"Class '{node.name}' should be PascalCase.",
                            code_snippet=f"class {node.name}:",
                            suggestion_hint="Rename to PascalCase.",
                        )
                    )
        return issues

    def _is_test_context(self, fp: str, func_name: str) -> bool:
        norm = fp.replace("\\", "/").lower()
        if "/tests/" in norm or Path(fp).name.startswith("test_"):
            return True
        if func_name.startswith("test_"):
            return True
        return False

    def _is_data_heavy_function(self, node: ast.AST) -> bool:
        """Detect functions mostly used for big literal initialization blocks."""
        for child in ast.walk(node):
            if isinstance(child, ast.List) and len(child.elts) >= 150:
                return True
            if isinstance(child, ast.Tuple) and len(child.elts) >= 150:
                return True
            if isinstance(child, ast.Set) and len(child.elts) >= 150:
                return True
            if isinstance(child, ast.Dict) and len(child.keys) >= 100:
                return True
        return False

    def _is_dispatcher_function(self, node: ast.AST) -> bool:
        """Detect large intent-routing/dispatcher functions where branch count is expected."""
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            return False
        length = (node.end_lineno or node.lineno) - node.lineno + 1
        if length < 120:
            return False

        if_count = 0
        return_count = 0
        for child in ast.walk(node):
            if isinstance(child, ast.If):
                if_count += 1
            elif isinstance(child, ast.Return):
                return_count += 1
        return if_count >= 8 and return_count >= 6

    def _check_function_length(self, tree: ast.AST, fp: str, limit: int = FUNCTION_LENGTH_LIMIT) -> List[Issue]:
        """Check function length. The `lines` parameter from the original signature is removed
        as it was not actually used in the body."""
        issues = []
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if self._is_test_context(fp, node.name):
                    continue
                if node.name == "main":
                    continue
                if self._is_data_heavy_function(node):
                    continue
                length = (node.end_lineno or node.lineno) - node.lineno + 1
                if length > limit:
                    issues.append(
                        Issue(
                            file=fp,
                            line=node.lineno,
                            column=0,
                            category="readability",
                            severity="medium",
                            rule_id="PY002",
                            message=f"Function '{node.name}' is {length} lines (>{limit}).",
                            code_snippet=f"def {node.name}(...):",
                            suggestion_hint="Extract helper functions to reduce length.",
                        )
                    )
        return issues

    def _check_complexity(self, tree: ast.AST, fp: str, limit: int = FUNCTION_COMPLEXITY_LIMIT) -> List[Issue]:
        issues = []
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if self._is_test_context(fp, node.name):
                    continue
                if node.name == "main":
                    continue
                if self._is_dispatcher_function(node):
                    continue
                cc = _python_cyclomatic(node)
                if cc > limit:
                    issues.append(
                        Issue(
                            file=fp,
                            line=node.lineno,
                            column=0,
                            category="readability",
                            severity="medium",
                            rule_id="PY005",
                            message=f"Function '{node.name}' has cyclomatic complexity {cc} (>{limit}).",
                            code_snippet=f"def {node.name}(...):",
                            suggestion_hint="Simplify logic; extract conditions or use early returns.",
                        )
                    )
        return issues

    # [FIX #5] Skip lines before first code statement (docstrings, etc.)
    def _check_nesting_depth(self, source: str, lines: List[str], fp: str, limit: int = 4) -> List[Issue]:
        issues = []
        first_code = _first_code_line(source)
        for i, line in enumerate(lines, 1):
            if i < first_code:
                continue
            if not line.strip():
                continue
            indent = len(line) - len(line.lstrip())
            depth = indent // 4
            if depth > limit and not line.strip().startswith("#"):
                issues.append(
                    Issue(
                        file=fp,
                        line=i,
                        column=0,
                        category="readability",
                        severity="low",
                        rule_id="PY006",
                        message=f"Nesting depth {depth} exceeds {limit}.",
                        code_snippet=line.rstrip(),
                        suggestion_hint="Use early returns or extract nested logic.",
                    )
                )
                break  # Report once per file to avoid noise
        return issues

    def _check_type_hints(self, tree: ast.AST, fp: str) -> List[Issue]:
        issues = []
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if node.name.startswith("_"):
                    continue
                non_self_args = [a for a in node.args.args if a.arg not in ("self", "cls")]
                if not non_self_args:
                    continue
                args_all_missing = all(a.annotation is None for a in non_self_args)
                return_missing = node.returns is None
                if args_all_missing and return_missing:
                    issues.append(
                        Issue(
                            file=fp,
                            line=node.lineno,
                            column=0,
                            category="readability",
                            severity="low",
                            rule_id="PY007",
                            message=f"Function '{node.name}' has no type hints.",
                            code_snippet=f"def {node.name}(...):",
                            suggestion_hint="Add type annotations for parameters and return type.",
                        )
                    )
        return issues

    def _check_assert_non_test(self, tree: ast.AST, fp: str) -> List[Issue]:
        if "test" in Path(fp).stem.lower():
            return []
        issues = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Assert):
                issues.append(
                    Issue(
                        file=fp,
                        line=node.lineno,
                        column=0,
                        category="security",
                        severity="low",
                        rule_id="PY015",
                        message="assert used for validation (stripped with python -O).",
                        code_snippet="assert ...",
                        suggestion_hint="Use if/raise for validation instead of assert.",
                    )
                )
                break
        return issues

    def _check_sql_injection(self, lines: List[str], fp: str) -> List[Issue]:
        issues = []
        sql_pattern = re.compile(
            r"(?:execute|cursor\.execute)\s*\(\s*f['\"]"
            r"|(?:execute|cursor\.execute)\s*\(\s*['\"].*%s"
            r"|(?:execute|cursor\.execute)\s*\(\s*['\"].*\bformat\(",
            re.IGNORECASE,
        )
        # VACUUM INTO requires f-string path injection by design (no bind params in SQLite VACUUM)
        vacuum_pattern = re.compile(r"\bVACUUM\b", re.IGNORECASE)
        for i, line in enumerate(lines, 1):
            if sql_pattern.search(line) and not vacuum_pattern.search(line):
                issues.append(
                    Issue(
                        file=fp,
                        line=i,
                        column=0,
                        category="security",
                        severity="high",
                        rule_id="PY014",
                        message="SQL query built with string formatting (injection risk).",
                        code_snippet=line.strip(),
                        suggestion_hint="Use parameterized queries with placeholders.",
                    )
                )
        return issues

    # [FIX #3] Only flag when the augmented value is a string (not integer +=)
    def _check_string_concat_loop(self, tree: ast.AST, fp: str) -> List[Issue]:
        issues = []
        for node in ast.walk(tree):
            if isinstance(node, (ast.For, ast.While)):
                for child in ast.walk(node):
                    if isinstance(child, ast.AugAssign) and isinstance(child.op, ast.Add):
                        if isinstance(child.target, ast.Name):
                            val = child.value
                            is_string_op = False
                            if isinstance(val, ast.Constant) and isinstance(val.value, str):
                                is_string_op = True
                            elif isinstance(val, ast.JoinedStr):
                                is_string_op = True
                            elif isinstance(val, ast.BinOp) and isinstance(val.op, ast.Add):
                                is_string_op = True
                            elif isinstance(val, ast.Call):
                                # e.g., str(...) or .format(...)
                                is_string_op = True
                            if is_string_op:
                                issues.append(
                                    Issue(
                                        file=fp,
                                        line=child.lineno,
                                        column=0,
                                        category="performance",
                                        severity="low",
                                        rule_id="PY009",
                                        message="String concatenation in loop may be slow.",
                                        code_snippet=f"{child.target.id} += ...",
                                        suggestion_hint="Collect in a list and use ''.join().",
                                    )
                                )
                                break
        return issues


# ---------------------------------------------------------------------------
# JavaScript / TypeScript Analyzer (regex-based, rule-table refactored)
# ---------------------------------------------------------------------------


class JSAnalyzer(BaseAnalyzer):
    language = "javascript"
    comment_chars = "//"

    # JS rules applied to all JS/TS files
    _JS_RULES: List[_Rule] = [
        _Rule(
            pattern=re.compile(r"\bvar\s+\w+"),
            category="readability",
            severity="medium",
            rule_id="JS001",
            message="'var' is function-scoped. Use 'let' or 'const'.",
            suggestion_hint="Replace var with let or const.",
            check_comment=True,
            comment_prefix="//",
        ),
        _Rule(
            pattern=re.compile(r"[^=!]==[^=]|[^!]!=[^=]"),
            category="performance",
            severity="low",
            rule_id="JS005",
            message="Loose equality (==). Use strict equality (===).",
            suggestion_hint="Replace == with === and != with !==.",
            check_comment=True,
            comment_prefix="//",
        ),
        _Rule(
            pattern=re.compile(r"\bconsole\.\w+\("),
            category="readability",
            severity="low",
            rule_id="JS002",
            message="console.log left in code.",
            suggestion_hint="Remove or replace with a proper logger.",
            check_comment=True,
            comment_prefix="//",
        ),
        _Rule(
            pattern=re.compile(r"\beval\s*\("),
            category="security",
            severity="high",
            rule_id="JS006",
            message="eval() allows arbitrary code execution.",
            suggestion_hint="Use JSON.parse() or a safer alternative.",
            check_comment=True,
            comment_prefix="//",
        ),
        _Rule(
            pattern=re.compile(r"\.innerHTML\s*="),
            category="security",
            severity="high",
            rule_id="JS007",
            message="innerHTML assignment is an XSS risk.",
            suggestion_hint="Use textContent or a sanitization library.",
            check_comment=False,
        ),
        _Rule(
            pattern=re.compile(r"\bdocument\.write\s*\("),
            category="security",
            severity="medium",
            rule_id="JS009",
            message="document.write() blocks parsing and is an XSS risk.",
            suggestion_hint="Use DOM manipulation methods instead.",
            check_comment=False,
        ),
        _Rule(
            pattern=re.compile(r"""(?:query|execute)\s*\(\s*[`'"].*\$\{"""),
            category="security",
            severity="medium",
            rule_id="JS008",
            message="SQL query built with template literals (injection risk).",
            suggestion_hint="Use parameterized queries.",
            check_comment=False,
        ),
    ]

    # Additional rules applied only when is_typescript=True
    _TS_RULES: List[_Rule] = [
        _Rule(
            pattern=re.compile(r":\s*any\b"),
            category="readability",
            severity="medium",
            rule_id="TS001",
            message="'any' type defeats TypeScript's type safety.",
            suggestion_hint="Use a specific type or 'unknown'.",
            check_comment=True,
            comment_prefix="//",
        ),
        _Rule(
            pattern=re.compile(r"@ts-ignore|@ts-nocheck"),
            category="readability",
            severity="low",
            rule_id="TS002",
            message="@ts-ignore suppresses type checking.",
            suggestion_hint="Fix the type error instead of suppressing.",
            check_comment=False,
        ),
    ]

    def __init__(self, is_typescript: bool = False) -> None:
        self.is_typescript = is_typescript

    def analyze(self, source: str, file_path: str) -> Tuple[List[Issue], FileMetrics]:
        issues, metrics = super().analyze(source, file_path)
        lines = source.split("\n")

        issues.extend(self._scan_rules(lines, file_path, self._JS_RULES))
        issues.extend(self._check_callback_nesting(lines, file_path))

        if self.is_typescript:
            issues.extend(self._scan_rules(lines, file_path, self._TS_RULES))

        func_pattern = re.compile(r"\bfunction\b|=>")
        metrics.function_count = sum(1 for ln in lines if func_pattern.search(ln))

        return issues, metrics

    # [FIX #10] Skip comment lines; use function( pattern not bare keyword
    def _check_callback_nesting(self, lines: List[str], fp: str, limit: int = 3) -> List[Issue]:
        issues = []
        depth = 0
        max_depth = 0
        max_line = 0
        func_open = re.compile(r"\bfunction\s*\(|=>\s*\{")
        for i, line in enumerate(lines, 1):
            stripped = line.strip()
            if stripped.startswith("//") or stripped.startswith("/*") or stripped.startswith("*"):
                continue
            opens = len(func_open.findall(line))
            closes = line.count("}")
            depth += opens
            if depth > max_depth:
                max_depth = depth
                max_line = i
            depth = max(0, depth - closes)
        if max_depth > limit:
            issues.append(
                Issue(
                    file=fp,
                    line=max_line,
                    column=0,
                    category="readability",
                    severity="medium",
                    rule_id="JS003",
                    message=f"Callback nesting depth {max_depth} (>{limit}).",
                    code_snippet=lines[max_line - 1].strip() if max_line <= len(lines) else "",
                    suggestion_hint="Use async/await or extract named functions.",
                )
            )
        return issues


# ---------------------------------------------------------------------------
# Java Analyzer (regex-based, rule-table refactored)
# ---------------------------------------------------------------------------


class JavaAnalyzer(BaseAnalyzer):
    language = "java"
    comment_chars = "//"

    _JAVA_RULES: List[_Rule] = [
        _Rule(
            pattern=re.compile(r"\b(List|Map|Set|Collection|ArrayList|HashMap|HashSet)\s+\w+\s*[=;]"),
            category="readability",
            severity="low",
            rule_id="JV004",
            message="Raw generic type. Use parameterized types.",
            suggestion_hint="Add type parameter e.g., List<String>.",
            check_comment=False,
        ),
        _Rule(
            pattern=re.compile(r"System\.exit\s*\("),
            category="security",
            severity="medium",
            rule_id="JV007",
            message="System.exit() terminates the JVM abruptly.",
            suggestion_hint="Throw an exception or use proper shutdown hooks.",
            check_comment=False,
        ),
        _Rule(
            pattern=re.compile(r"""(?:executeQuery|executeUpdate|prepareStatement)\s*\(\s*["'].*\+"""),
            category="security",
            severity="high",
            rule_id="JV006",
            message="SQL query built with string concatenation.",
            suggestion_hint="Use PreparedStatement with parameterized queries.",
            check_comment=False,
        ),
        _Rule(
            pattern=re.compile(r"System\.out\.print"),
            category="readability",
            severity="low",
            rule_id="JV008",
            message="System.out.println used (use a logger instead).",
            suggestion_hint="Use SLF4J/Log4j logger.",
            check_comment=False,
        ),
    ]

    def analyze(self, source: str, file_path: str) -> Tuple[List[Issue], FileMetrics]:
        issues, metrics = super().analyze(source, file_path)
        lines = source.split("\n")

        issues.extend(self._check_empty_catch(source, file_path))
        issues.extend(self._check_string_concat_loop(lines, file_path))
        issues.extend(self._scan_rules(lines, file_path, self._JAVA_RULES))

        # Raw types rule needs extra guard: skip when line contains '<'
        # (already handled above via _JAVA_RULES, but raw_types needs special filter)
        # We post-filter JV004: remove issues where source line has '<'
        issues = [i for i in issues if not (i.rule_id == "JV004" and "<" in lines[i.line - 1])]

        metrics.function_count = len(re.findall(r"\b(?:public|private|protected)\s+\w+\s+\w+\s*\(", source))
        return issues, metrics

    def _check_empty_catch(self, source: str, fp: str) -> List[Issue]:
        """Signature simplified: `lines` parameter removed (source is sufficient)."""
        issues = []
        pat = re.compile(r"catch\s*\([^)]*\)\s*\{\s*\}", re.DOTALL)
        for m in pat.finditer(source):
            line_num = source[: m.start()].count("\n") + 1
            issues.append(
                Issue(
                    file=fp,
                    line=line_num,
                    column=0,
                    category="readability",
                    severity="medium",
                    rule_id="JV001",
                    message="Empty catch block swallows exception.",
                    code_snippet=m.group(0).strip(),
                    suggestion_hint="Log the exception or handle it properly.",
                )
            )
        return issues

    # [FIX #11] Use brace depth counter instead of boolean for nested blocks
    def _check_string_concat_loop(self, lines: List[str], fp: str) -> List[Issue]:
        issues = []
        loop_pat = re.compile(r"\b(for|while)\s*\(")
        concat_pat = re.compile(r'\+\s*=\s*"|\+\s*=\s*\w+')
        brace_depth = 0
        in_loop = False
        for i, line in enumerate(lines, 1):
            if loop_pat.search(line):
                in_loop = True
                brace_depth = line.count("{") - line.count("}")
            elif in_loop:
                brace_depth += line.count("{") - line.count("}")
                if brace_depth <= 0:
                    in_loop = False
                    brace_depth = 0
                    continue
                if concat_pat.search(line):
                    issues.append(
                        Issue(
                            file=fp,
                            line=i,
                            column=0,
                            category="performance",
                            severity="medium",
                            rule_id="JV003",
                            message="String concatenation in loop. Use StringBuilder.",
                            code_snippet=line.strip(),
                            suggestion_hint="Replace with StringBuilder.append().",
                        )
                    )
        return issues


# ---------------------------------------------------------------------------
# Go Analyzer (regex-based, rule-table refactored)
# ---------------------------------------------------------------------------


class GoAnalyzer(BaseAnalyzer):
    language = "go"
    comment_chars = "//"

    _GO_RULES: List[_Rule] = [
        _Rule(
            pattern=re.compile(r"\bpanic\s*\("),
            category="readability",
            severity="low",
            rule_id="GO006",
            message="panic() used. Prefer error returns in library code.",
            suggestion_hint="Return an error instead of panicking.",
            check_comment=True,
            comment_prefix="//",
        ),
        _Rule(
            pattern=re.compile(r"""(?:Query|Exec)\s*\(\s*(?:fmt\.Sprintf|"[^"]*"\s*\+)"""),
            category="security",
            severity="medium",
            rule_id="GO004",
            message="SQL query built with string formatting.",
            suggestion_hint="Use parameterized queries with $1, $2 placeholders.",
            check_comment=False,
        ),
    ]

    def analyze(self, source: str, file_path: str) -> Tuple[List[Issue], FileMetrics]:
        issues, metrics = super().analyze(source, file_path)
        lines = source.split("\n")

        issues.extend(self._check_error_ignored(lines, file_path))
        issues.extend(self._check_defer_in_loop(lines, file_path))
        issues.extend(self._scan_rules(lines, file_path, self._GO_RULES))

        metrics.function_count = len(re.findall(r"\bfunc\s+", source))
        return issues, metrics

    # [FIX #8] Removed unused `pat` variable, added _ discard detection
    def _check_error_ignored(self, lines: List[str], fp: str) -> List[Issue]:
        issues = []
        err_assign = re.compile(r"\w+\s*,\s*err\s*:?=")
        err_discard = re.compile(r"\w+\s*,\s*_\s*:?=")
        err_check = re.compile(r"if\s+err\s*!=\s*nil")
        for i, line in enumerate(lines, 1):
            # Check for explicitly discarded errors: result, _ := ...
            if err_discard.search(line) and not _in_comment_or_string(line, 0, "//"):
                issues.append(
                    Issue(
                        file=fp,
                        line=i,
                        column=0,
                        category="readability",
                        severity="high",
                        rule_id="GO001",
                        message="Error return value explicitly discarded with '_'.",
                        code_snippet=line.strip(),
                        suggestion_hint="Check error with 'if err != nil { ... }'.",
                    )
                )
                continue
            # Check for err assigned but not checked
            if err_assign.search(line):
                checked = False
                for j in range(i, min(i + 8, len(lines))):
                    if err_check.search(lines[j]):
                        checked = True
                        break
                if not checked:
                    issues.append(
                        Issue(
                            file=fp,
                            line=i,
                            column=0,
                            category="readability",
                            severity="high",
                            rule_id="GO001",
                            message="Error return value not checked.",
                            code_snippet=line.strip(),
                            suggestion_hint="Check error with 'if err != nil { ... }'.",
                        )
                    )
        return issues

    # [FIX #11] Use brace depth counter for nested blocks
    def _check_defer_in_loop(self, lines: List[str], fp: str) -> List[Issue]:
        issues = []
        in_loop = False
        brace_depth = 0
        for i, line in enumerate(lines, 1):
            stripped = line.strip()
            if re.match(r"\bfor\b", stripped):
                in_loop = True
                brace_depth = stripped.count("{") - stripped.count("}")
            elif in_loop:
                brace_depth += stripped.count("{") - stripped.count("}")
                if brace_depth <= 0:
                    in_loop = False
                    brace_depth = 0
                    continue
                if "defer " in stripped:
                    issues.append(
                        Issue(
                            file=fp,
                            line=i,
                            column=0,
                            category="performance",
                            severity="low",
                            rule_id="GO005",
                            message="defer inside loop accumulates deferred calls.",
                            code_snippet=stripped,
                            suggestion_hint="Move defer outside loop or use explicit close.",
                        )
                    )
        return issues


# ---------------------------------------------------------------------------
# C/C++ Analyzer (regex-based, rule-table refactored)
# ---------------------------------------------------------------------------


class CAnalyzer(BaseAnalyzer):
    language = "c"
    comment_chars = "//"

    _C_RULES: List[_Rule] = [
        _Rule(
            pattern=re.compile(r"\bprintf\s*\(\s*\w+\s*\)"),
            category="security",
            severity="medium",
            rule_id="CC004",
            message="printf() called with variable as format string.",
            suggestion_hint='Use printf("%s", var) to prevent format string attacks.',
            check_comment=False,
        ),
        _Rule(
            pattern=re.compile(r"\bsystem\s*\("),
            category="security",
            severity="high",
            rule_id="CC008",
            message="system() call allows command injection.",
            suggestion_hint="Use exec family (execvp) with argument arrays.",
            check_comment=True,
            comment_prefix="//",
        ),
    ]

    def analyze(self, source: str, file_path: str) -> Tuple[List[Issue], FileMetrics]:
        issues, metrics = super().analyze(source, file_path)
        lines = source.split("\n")

        issues.extend(self._check_unsafe_functions(lines, file_path))
        issues.extend(self._scan_rules(lines, file_path, self._C_RULES))

        metrics.function_count = len(re.findall(r"\w+\s+\w+\s*\([^)]*\)\s*\{", source))
        return issues, metrics

    def _check_unsafe_functions(self, lines: List[str], fp: str) -> List[Issue]:
        issues = []
        unsafe = {
            "gets": ("CC001", "gets() has no bounds checking (buffer overflow)."),
            "strcpy": ("CC002", "strcpy() has no bounds checking."),
            "strcat": ("CC002", "strcat() has no bounds checking."),
            "sprintf": ("CC003", "sprintf() has no bounds checking."),
        }
        safe_alt = {"gets": "fgets", "strcpy": "strncpy", "strcat": "strncat", "sprintf": "snprintf"}
        for i, line in enumerate(lines, 1):
            for func, (rule, msg) in unsafe.items():
                pat = re.compile(rf"\b{func}\s*\(")
                m = pat.search(line)
                if m and not _in_comment_or_string(line, m.start(), "//"):
                    issues.append(
                        Issue(
                            file=fp,
                            line=i,
                            column=0,
                            category="security",
                            severity="high",
                            rule_id=rule,
                            message=msg,
                            code_snippet=line.strip(),
                            suggestion_hint=f"Use {safe_alt[func]}() with explicit size.",
                        )
                    )
        return issues
