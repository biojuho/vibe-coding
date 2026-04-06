"""
_ci_models.py — code_improver 공유 데이터 모델 및 전역 상수.

code_improver 패키지 내 모든 서브모듈이 이 파일을 임포트합니다.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class Issue:
    file: str
    line: int
    column: int
    category: str  # readability | performance | security
    severity: str  # low | medium | high
    rule_id: str
    message: str
    code_snippet: str
    suggestion_hint: str


@dataclass
class FileMetrics:
    total_lines: int = 0
    code_lines: int = 0
    function_count: int = 0
    max_complexity: int = 0
    avg_function_length: float = 0.0


@dataclass
class FileReport:
    path: str
    language: str
    issues: List[Issue] = field(default_factory=list)
    metrics: Optional[FileMetrics] = None
    skipped: bool = False
    skipped_reason: str = ""


@dataclass
class AnalysisReport:
    files: List[FileReport] = field(default_factory=list)
    summary: Dict = field(default_factory=dict)
    timestamp: str = ""


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

LANGUAGE_MAP = {
    ".py": "python",
    ".js": "javascript",
    ".jsx": "javascript",
    ".mjs": "javascript",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".java": "java",
    ".go": "go",
    ".c": "c",
    ".h": "c",
    ".cpp": "cpp",
    ".cc": "cpp",
    ".cxx": "cpp",
    ".hpp": "cpp",
}

SEVERITY_ORDER = {"low": 0, "medium": 1, "high": 2}

DEFAULT_EXCLUDES = {
    "node_modules",
    "__pycache__",
    ".git",
    "venv",
    ".venv",
    "dist",
    "build",
    ".next",
    ".tmp",
    "vendor",
    "target",
    ".agent",
    ".agents",
    ".claude",
    ".codex",
}

FUNCTION_LENGTH_LIMIT = 180
FUNCTION_COMPLEXITY_LIMIT = 20

# [FIX #7] Bounded quantifiers to prevent ReDoS
SECRET_PATTERNS = [
    re.compile(
        r"(?:password|passwd|pwd|secret|api_?key|token|auth)"
        r"\s{0,5}[=:]\s{0,5}['\"][^'\"]{4,200}['\"]",
        re.IGNORECASE,
    ),
    re.compile(
        r"(?:AWS|AZURE|GCP|GITHUB|SLACK)\w{0,20}"
        r"(?:KEY|SECRET|TOKEN)\s{0,5}[=:]\s{0,5}['\"][^'\"]{1,200}['\"]",
        re.IGNORECASE,
    ),
]

URL_CANDIDATE_PATTERN = re.compile(r"""https?://[^\s"'`<>]+""", re.IGNORECASE)
HASHED_BUNDLE_PATTERN = re.compile(r".*[-.][a-f0-9]{8,}\.(?:js|mjs|cjs|css)$", re.IGNORECASE)


def detect_language(file_path: str) -> Optional[str]:
    """Return the canonical language name for a file extension, or None."""
    ext = Path(file_path).suffix.lower()
    return LANGUAGE_MAP.get(ext)
