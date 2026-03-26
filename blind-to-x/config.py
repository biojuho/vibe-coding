"""Shared configuration, error constants, and logging setup."""

import logging
import os
import shutil

import yaml
from dotenv import load_dotenv

# ── Error constants ──────────────────────────────────────────────────
ERROR_NOTION_CONFIG_MISSING = "NOTION_CONFIG_MISSING"
ERROR_NOTION_SCHEMA_FETCH_FAILED = "NOTION_SCHEMA_FETCH_FAILED"
ERROR_NOTION_SCHEMA_MISMATCH = "NOTION_SCHEMA_MISMATCH"
ERROR_NOTION_DUPLICATE_CHECK_FAILED = "NOTION_DUPLICATE_CHECK_FAILED"
ERROR_NOTION_UPLOAD_FAILED = "NOTION_UPLOAD_FAILED"
ERROR_DUPLICATE_URL = "DUPLICATE_URL"
ERROR_SCRAPE_FAILED = "SCRAPE_FAILED"
ERROR_SCRAPE_FEED_FAILED = "SCRAPE_FEED_FAILED"
ERROR_SCRAPE_PARSE_FAILED = "SCRAPE_PARSE_FAILED"
ERROR_FILTERED_SHORT = "FILTERED_SHORT"
ERROR_FILTERED_SPAM = "FILTERED_SPAM"
ERROR_FILTERED_LOW_QUALITY = "FILTERED_LOW_QUALITY"
ERROR_DUPLICATE_CONTENT = "DUPLICATE_CONTENT"
QUALITY_SCORE_THRESHOLD = 55


def _is_ascii_path(path: str) -> bool:
    try:
        path.encode("ascii")
    except UnicodeEncodeError:
        return False
    return True


def _get_windows_short_path(path: str) -> str:
    """Return an ASCII-friendly 8.3 path when available on Windows."""
    if os.name != "nt":
        return ""

    try:
        import ctypes

        get_short_path_name = ctypes.windll.kernel32.GetShortPathNameW
        required = get_short_path_name(path, None, 0)
        if required <= 0:
            return ""

        buffer = ctypes.create_unicode_buffer(required)
        resolved = get_short_path_name(path, buffer, required)
        if resolved <= 0:
            return ""
        return buffer.value
    except Exception:
        return ""


def _ascii_ca_bundle_candidates() -> list[str]:
    system_drive = os.environ.get("SystemDrive", "C:")
    public_root = os.environ.get("PUBLIC") or os.path.join(system_drive, "Users", "Public")
    program_data = os.environ.get("ProgramData") or os.path.join(system_drive, "ProgramData")

    candidates = [
        os.path.join(public_root, "btx-cert"),
        os.path.join(program_data, "btx-cert"),
    ]

    unique_candidates: list[str] = []
    for candidate in candidates:
        if candidate and candidate not in unique_candidates and _is_ascii_path(candidate):
            unique_candidates.append(candidate)
    return unique_candidates


def _resolve_ascii_curl_ca_bundle(cert_source: str) -> str:
    """Materialize certifi's CA bundle at an ASCII-only path for curl_cffi."""
    if not cert_source:
        return cert_source

    for bundle_dir in _ascii_ca_bundle_candidates():
        bundle_path = os.path.join(bundle_dir, "certifi-cacert.pem")
        try:
            os.makedirs(bundle_dir, exist_ok=True)
            source_size = os.path.getsize(cert_source)
            if not os.path.exists(bundle_path) or os.path.getsize(bundle_path) != source_size:
                shutil.copyfile(cert_source, bundle_path)
            return bundle_path
        except OSError:
            continue

    short_path = _get_windows_short_path(cert_source)
    if short_path and _is_ascii_path(short_path):
        return short_path

    return cert_source


def setup_logging():
    """Configure logging with file + stream handlers. Call once at startup."""
    log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".tmp")
    os.makedirs(log_dir, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler(os.path.join(log_dir, "app_debug.log"), encoding="utf-8"),
            logging.StreamHandler(),
        ],
    )


def load_env():
    """Load .env with stable precedence.

    Priority:
    1) BLIND_TO_X_ENV_PATH (explicit override)
    2) project-local .env (blind-to-x/.env)
    3) workspace-root .env (for backward compatibility)
    """
    this_dir = os.path.dirname(os.path.abspath(__file__))
    parent_dir = os.path.dirname(this_dir)

    candidate_paths = []
    explicit_env_path = os.environ.get("BLIND_TO_X_ENV_PATH", "").strip()
    if explicit_env_path:
        candidate_paths.append(os.path.abspath(explicit_env_path))
    candidate_paths.append(os.path.join(this_dir, ".env"))
    candidate_paths.append(os.path.join(parent_dir, ".env"))

    loaded_any = False
    for path in candidate_paths:
        if path and os.path.exists(path):
            # Keep first-loaded values as highest priority.
            load_dotenv(path, override=False)
            loaded_any = True

    if not loaded_any:
        load_dotenv(override=False)

    # curl_cffi CA Error 77 우회 (Windows 한글 경로 + Python 3.14)
    # certifi의 원본 경로가 비ASCII일 수 있어 ASCII-only 위치로 복사한 번들을 우선 사용한다.
    if not os.environ.get("CURL_CA_BUNDLE"):
        try:
            import certifi

            os.environ["CURL_CA_BUNDLE"] = _resolve_ascii_curl_ca_bundle(certifi.where())
        except ImportError:
            pass


logger = logging.getLogger(__name__)


class ConfigValidationError(Exception):
    """config.yaml 필수 키 누락 또는 잘못된 값."""


class ConfigManager:
    # 런타임 필수 키 (없으면 파이프라인 동작 불가)
    _REQUIRED_KEYS: list[str] = [
        "request.timeout_seconds",
        "scrape_quality.min_content_length",
        "scrape_quality.min_korean_ratio",
        "ranking.weights.scrape_quality",
        "ranking.weights.publishability",
        "ranking.weights.performance",
    ]
    # Notion 연동 필수 키: config 또는 env 중 하나
    _NOTION_ENV_KEYS: dict[str, str] = {
        "notion.api_key": "NOTION_API_KEY",
        "notion.database_id": "NOTION_DATABASE_ID",
    }

    def __init__(self, config_path="config.yaml"):
        self.config_path = config_path
        self.config = self._load_config()

    def _load_config(self):
        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                return yaml.safe_load(f) or {}
        except FileNotFoundError:
            logger.warning(f"Config file {self.config_path} not found. Falling back to environment variables.")
            return {}
        except Exception as e:
            logger.error(f"Failed to load config file: {e}")
            return {}

    def get(self, key, default=None):
        keys = key.split(".")
        val = self.config
        for k in keys:
            if isinstance(val, dict):
                val = val.get(k)
            else:
                return default
        return val if val is not None else default

    def validate(self) -> list[str]:
        """설정 값 검증. 비치명적 경고 리스트를 반환하며 치명적 오류는 ConfigValidationError 발생.

        Returns:
            warnings: 비치명적 경고 문자열 리스트.
        Raises:
            ConfigValidationError: 필수 키 누락 등 치명적 오류.
        """
        import os

        errors: list[str] = []
        warnings: list[str] = []

        for key in self._REQUIRED_KEYS:
            if self.get(key) is None:
                errors.append(f"Missing required config key: {key}")

        for config_key, env_name in self._NOTION_ENV_KEYS.items():
            config_val = str(self.get(config_key, "") or "")
            env_val = os.environ.get(env_name, "")
            if config_val.startswith("${") and not env_val:
                warnings.append(
                    f"'{config_key}'가 미치환 상태이며 env '{env_name}'도 미설정 → Notion 업로드 불가."
                )
            elif not config_val and not env_val:
                warnings.append(
                    f"'{config_key}' 및 env '{env_name}' 모두 비어있음 → Notion 업로드 불가."
                )

        budget = self.get("limits.daily_api_budget_usd")
        if budget is not None and float(budget) <= 0:
            warnings.append(f"limits.daily_api_budget_usd={budget} ≤ 0: 첫 API 호출부터 차단됩니다.")

        w_total = sum(
            float(self.get(f"ranking.weights.{k}", 0) or 0)
            for k in ("scrape_quality", "publishability", "performance")
        )
        if abs(w_total - 1.0) > 0.01:
            warnings.append(f"ranking.weights 합계={w_total:.3f} (기대 1.0) → 랭킹 점수 부정확 가능.")

        if errors:
            raise ConfigValidationError(
                "Config validation failed:\n" + "\n".join(f"  - {e}" for e in errors)
            )

        for w in warnings:
            logger.warning("Config warning: %s", w)

        return warnings


class ProxyManager:
    def __init__(self, config):
        self.enabled = config.get("proxy.enabled", False)
        self.proxy_list = config.get("proxy.list", [])

    def get_random_proxy(self):
        import random

        if not self.enabled or not self.proxy_list:
            return None
        return random.choice(self.proxy_list)
