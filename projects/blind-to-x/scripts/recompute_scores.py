from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path
from typing import Any

BTX_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SAMPLE_INPUT_PATH = BTX_ROOT / ".tmp" / "recompute_scores_fixture.json"
sys.path.insert(0, str(BTX_ROOT))

ConfigManager = None
load_env = None
setup_logging = None
build_content_profile = None
FeedbackLoop = None
NotionUploader = None


def _load_runtime_dependencies() -> None:
    global ConfigManager, FeedbackLoop, NotionUploader, build_content_profile, load_env, setup_logging
    if ConfigManager is not None:
        return

    from config import ConfigManager as _ConfigManager
    from config import load_env as _load_env
    from config import setup_logging as _setup_logging
    from pipeline.content_intelligence import build_content_profile as _build_content_profile
    from pipeline.feedback_loop import FeedbackLoop as _FeedbackLoop
    from pipeline.notion_upload import NotionUploader as _NotionUploader

    ConfigManager = _ConfigManager
    load_env = _load_env
    setup_logging = _setup_logging
    build_content_profile = _build_content_profile
    FeedbackLoop = _FeedbackLoop
    NotionUploader = _NotionUploader


def _score_update_from_record(
    record: dict[str, Any],
    *,
    top_examples: list[dict[str, Any]],
    ranking_weights: dict[str, float],
) -> dict[str, Any]:
    content = record.get("memo") or record.get("text") or ""
    post_data = {
        "title": record.get("title", ""),
        "content": content,
        "likes": record.get("likes", 0) or 0,
        "comments": 0,
    }
    raw_scrape_quality_score = record.get("scrape_quality_score")
    scrape_quality_score = 70.0 if raw_scrape_quality_score in (None, "") else float(raw_scrape_quality_score)
    profile = build_content_profile(
        post_data,
        scrape_quality_score=scrape_quality_score,
        historical_examples=top_examples,
        ranking_weights=ranking_weights,
    ).to_dict()
    return {
        "page_id": record["page_id"],
        "title": record.get("title", ""),
        "properties": {
            "topic_cluster": profile["topic_cluster"],
            "hook_type": profile["hook_type"],
            "emotion_axis": profile["emotion_axis"],
            "audience_fit": profile["audience_fit"],
            "scrape_quality_score": profile["scrape_quality_score"],
            "publishability_score": profile["publishability_score"],
            "performance_score": profile["performance_score"],
            "final_rank_score": profile["final_rank_score"],
            "chosen_draft_type": profile["recommended_draft_type"],
        },
    }


def _score_sample(update: dict[str, Any]) -> dict[str, Any]:
    properties = update["properties"]
    return {
        "page_id": update["page_id"],
        "title": update.get("title", ""),
        "topic_cluster": properties.get("topic_cluster"),
        "hook_type": properties.get("hook_type"),
        "final_rank_score": properties.get("final_rank_score"),
        "chosen_draft_type": properties.get("chosen_draft_type"),
    }


def _coerce_weight_map(value: Any, *, field_name: str) -> dict[str, float] | None:
    if value is None:
        return None
    if not isinstance(value, dict):
        raise ValueError(f"recompute_scores {field_name} must be a JSON object")
    weights: dict[str, float] = {}
    for key, raw in value.items():
        if not isinstance(key, str):
            raise ValueError(f"recompute_scores {field_name} keys must be strings")
        try:
            weights[key] = float(raw)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"recompute_scores {field_name}.{key} must be numeric") from exc
    return weights


def _load_input_records(input_path: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, float] | None]:
    payload = json.loads(Path(input_path).read_text(encoding="utf-8"))
    if isinstance(payload, list):
        records = payload
        examples: list[dict[str, Any]] = []
        candidate_ranking_weights = None
    elif isinstance(payload, dict):
        records = next((payload[key] for key in ("records", "pages", "items") if key in payload), None)
        examples = payload["historical_examples"] if "historical_examples" in payload else []
        candidate_ranking_weights = _coerce_weight_map(
            payload.get("candidate_ranking_weights"),
            field_name="candidate_ranking_weights",
        )
    else:
        raise ValueError("recompute_scores input must be a JSON object or array")

    if not isinstance(records, list):
        raise ValueError("recompute_scores input must include a records/pages/items array")
    if not isinstance(examples, list):
        raise ValueError("recompute_scores historical_examples must be an array")
    if not all(isinstance(record, dict) for record in records):
        raise ValueError("recompute_scores input records must be JSON objects")
    if not all(isinstance(example, dict) for example in examples):
        raise ValueError("recompute_scores historical_examples entries must be JSON objects")
    return records, examples, candidate_ranking_weights


def _validate_input_records(
    records: list[dict[str, Any]],
    candidate_ranking_weights: dict[str, float] | None,
) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    seen_page_ids: set[str] = set()

    if not records:
        warnings.append("records_empty")

    for index, record in enumerate(records):
        prefix = f"records[{index}]"
        page_id = record.get("page_id")
        if not isinstance(page_id, str) or not page_id.strip():
            errors.append(f"{prefix}.page_id_missing")
        elif page_id in seen_page_ids:
            warnings.append(f"{prefix}.page_id_duplicate:{page_id}")
        else:
            seen_page_ids.add(page_id)

        if not str(record.get("title") or "").strip():
            warnings.append(f"{prefix}.title_missing")
        if not str(record.get("memo") or record.get("text") or "").strip():
            warnings.append(f"{prefix}.content_missing")

        scrape_quality = record.get("scrape_quality_score")
        if scrape_quality not in (None, ""):
            try:
                float(scrape_quality)
            except (TypeError, ValueError):
                errors.append(f"{prefix}.scrape_quality_score_not_numeric")

    if candidate_ranking_weights is None:
        warnings.append("candidate_ranking_weights_missing")

    return errors, warnings


def _build_input_validation(input_path: str) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    records: list[dict[str, Any]] = []
    examples: list[dict[str, Any]] = []
    candidate_ranking_weights: dict[str, float] | None = None

    try:
        records, examples, candidate_ranking_weights = _load_input_records(input_path)
    except FileNotFoundError:
        errors.append("input_file_not_found")
    except json.JSONDecodeError as exc:
        errors.append(f"invalid_json:line={exc.lineno}:column={exc.colno}")
    except ValueError as exc:
        errors.append(str(exc))

    if not errors:
        validation_errors, validation_warnings = _validate_input_records(records, candidate_ranking_weights)
        errors.extend(validation_errors)
        warnings.extend(validation_warnings)

    ok = not errors
    candidate_keys = sorted(candidate_ranking_weights) if candidate_ranking_weights else []
    operator_action = (
        "Run recompute_scores --assert-runtime-contract, then --input with --dry-run --json when ready."
        if ok
        else "Fix recompute_scores fixture errors before scoring dry-run."
    )
    return {
        "status": "ok" if ok else "fail",
        "ok": ok,
        "input_source": input_path,
        "record_count": len(records),
        "historical_example_count": len(examples),
        "candidate_ranking_weights_present": candidate_ranking_weights is not None,
        "candidate_ranking_weight_keys": candidate_keys,
        "errors": errors,
        "warnings": warnings,
        "safety": {
            "notion_reads": False,
            "notion_writes": False,
            "x_posts": False,
            "auto_publish_default": False,
            "manual_publish_required": True,
        },
        "runtime_contract": {
            "validation": {
                "loads_runtime_dependencies": False,
                "scoring_runs": False,
                "notion_reads": False,
                "notion_writes": False,
                "x_posts": False,
            },
            "scoring_dry_run": _runtime_notes(input_path),
        },
        "operator_action": operator_action,
    }


def _format_input_validation(payload: dict[str, Any]) -> str:
    warnings = payload.get("warnings") or []
    errors = payload.get("errors") or []
    return (
        "recompute_scores_fixture "
        f"status={payload['status']} "
        f"records={payload['record_count']} "
        f"historical_examples={payload['historical_example_count']} "
        f"candidate_ranking_weights={str(payload['candidate_ranking_weights_present']).lower()} "
        f"errors={len(errors)} "
        f"warnings={len(warnings)} "
        f"notion_reads={str(payload['safety']['notion_reads']).lower()} "
        f"notion_writes={str(payload['safety']['notion_writes']).lower()} "
        f"scoring_dependencies=may_initialize "
        f"operator_action={payload['operator_action']}"
    )


def validate_input(input_path: str, *, json_output: bool = False) -> int:
    payload = _build_input_validation(input_path)
    if json_output:
        print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
    else:
        print(_format_input_validation(payload))
    return 0 if payload["ok"] else 1


def _runtime_contract_gate_errors(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if payload.get("ok") is not True:
        errors.append("validation_not_ok")
    if payload.get("errors"):
        errors.append("validation_errors_present")

    safety = payload.get("safety") or {}
    if safety.get("notion_reads") is not False:
        errors.append("safety.notion_reads_not_false")
    if safety.get("notion_writes") is not False:
        errors.append("safety.notion_writes_not_false")
    if safety.get("x_posts") is not False:
        errors.append("safety.x_posts_not_false")

    runtime_contract = payload.get("runtime_contract") or {}
    validation = runtime_contract.get("validation") or {}
    if validation.get("loads_runtime_dependencies") is not False:
        errors.append("runtime_contract.validation.loads_runtime_dependencies_not_false")
    if validation.get("scoring_runs") is not False:
        errors.append("runtime_contract.validation.scoring_runs_not_false")
    if validation.get("x_posts") is not False:
        errors.append("runtime_contract.validation.x_posts_not_false")

    scoring_dry_run = runtime_contract.get("scoring_dry_run") or {}
    if scoring_dry_run.get("scoring_dependencies_may_initialize") is not True:
        errors.append("runtime_contract.scoring_dry_run.scoring_dependencies_may_initialize_not_true")
    if scoring_dry_run.get("notion_reads") is not False:
        errors.append("runtime_contract.scoring_dry_run.notion_reads_not_false")
    if scoring_dry_run.get("notion_writes") is not False:
        errors.append("runtime_contract.scoring_dry_run.notion_writes_not_false")
    return errors


def _format_runtime_contract_gate(payload: dict[str, Any]) -> str:
    runtime_contract = payload["runtime_contract"]
    validation = runtime_contract["validation"]
    scoring_dry_run = runtime_contract["scoring_dry_run"]
    return (
        "recompute_scores_runtime_contract "
        f"status={payload['status']} "
        f"ok={str(payload['ok']).lower()} "
        f"input_source={payload['input_source']} "
        f"errors={len(payload['errors'])} "
        f"gate_errors={len(payload['gate_errors'])} "
        f"notion_reads={str(payload['safety']['notion_reads']).lower()} "
        f"notion_writes={str(payload['safety']['notion_writes']).lower()} "
        "validation_loads_runtime_dependencies="
        f"{str(validation['loads_runtime_dependencies']).lower()} "
        f"validation_scoring_runs={str(validation['scoring_runs']).lower()} "
        "scoring_dependencies_may_initialize="
        f"{str(scoring_dry_run['scoring_dependencies_may_initialize']).lower()} "
        f"operator_action={payload['operator_action']}"
    )


def assert_runtime_contract(input_path: str, *, json_output: bool = False) -> int:
    validation = _build_input_validation(input_path)
    gate_errors = _runtime_contract_gate_errors(validation)
    ok = not gate_errors
    payload = {
        "status": "ok" if ok else "fail",
        "ok": ok,
        "input_source": validation["input_source"],
        "validation_status": validation["status"],
        "validation_ok": validation["ok"],
        "record_count": validation["record_count"],
        "candidate_ranking_weights_present": validation["candidate_ranking_weights_present"],
        "gate_errors": gate_errors,
        "errors": validation["errors"],
        "warnings": validation["warnings"],
        "safety": validation["safety"],
        "runtime_contract": validation["runtime_contract"],
        "operator_action": (
            "Runtime contract gate passed; scoring dry-run may proceed for manual review."
            if ok
            else "Fix runtime contract gate errors before scoring dry-run."
        ),
    }
    if json_output:
        print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
    else:
        print(_format_runtime_contract_gate(payload))
    return 0 if ok else 1


def _sample_input_payload() -> dict[str, Any]:
    return {
        "schema_version": 1,
        "records": [
            {
                "page_id": "fixture-1",
                "title": "Career timing question",
                "memo": "Office worker asks whether to switch teams before promotion review.",
                "likes": 42,
                "scrape_quality_score": 72,
            },
            {
                "page_id": "fixture-2",
                "title": "Compensation rumor discussion",
                "memo": "Employees compare bonus expectations and ask for safer framing.",
                "likes": 18,
                "scrape_quality_score": 66,
            },
        ],
        "historical_examples": [{"title": "Promotion timing thread", "final_rank_score": 82}],
        "candidate_ranking_weights": {
            "scrape_quality": 0.25,
            "publishability": 0.45,
            "performance": 0.3,
        },
    }


def _format_sample_input_writer(payload: dict[str, Any]) -> str:
    validation = payload["validation"]
    return (
        "recompute_scores_fixture_writer "
        f"status={payload['status']} "
        f"output={payload['output_path']} "
        f"overwritten={str(payload['overwritten']).lower()} "
        f"records={validation['record_count']} "
        f"errors={len(validation['errors'])} "
        f"warnings={len(validation['warnings'])} "
        f"notion_reads={str(payload['safety']['notion_reads']).lower()} "
        f"notion_writes={str(payload['safety']['notion_writes']).lower()} "
        f"scoring_dependencies=may_initialize "
        f"operator_action={payload['operator_action']}"
    )


def write_sample_input(output_path: str | None = None, *, json_output: bool = False) -> int:
    target = Path(output_path) if output_path else DEFAULT_SAMPLE_INPUT_PATH
    if not target.is_absolute():
        target = BTX_ROOT / target
    target = target.resolve()

    target.parent.mkdir(parents=True, exist_ok=True)
    overwritten = target.exists()
    target.write_text(
        json.dumps(_sample_input_payload(), ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    validation = _build_input_validation(str(target))
    payload = {
        "status": validation["status"],
        "ok": validation["ok"],
        "output_path": str(target),
        "overwritten": overwritten,
        "validation": {
            "record_count": validation["record_count"],
            "historical_example_count": validation["historical_example_count"],
            "candidate_ranking_weights_present": validation["candidate_ranking_weights_present"],
            "candidate_ranking_weight_keys": validation["candidate_ranking_weight_keys"],
            "errors": validation["errors"],
            "warnings": validation["warnings"],
        },
        "safety": validation["safety"],
        "runtime_contract": validation["runtime_contract"],
        "operator_action": (
            "Run recompute_scores --validate-input, then --assert-runtime-contract, then --input with --dry-run --json."
            if validation["ok"]
            else "Fix generated recompute_scores fixture before scoring dry-run."
        ),
    }
    if json_output:
        print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
    else:
        print(_format_sample_input_writer(payload))
    return 0 if validation["ok"] else 1


def _average(values: list[float]) -> float | None:
    if not values:
        return None
    return round(sum(values) / len(values), 2)


def _score_value(update: dict[str, Any]) -> float | None:
    value = update.get("properties", {}).get("final_rank_score")
    try:
        return round(float(value), 2)
    except (TypeError, ValueError):
        return None


def _build_score_comparison(
    *,
    current_updates: list[dict[str, Any]],
    candidate_updates: list[dict[str, Any]],
    candidate_ranking_weights: dict[str, float] | None,
    sample_limit: int,
) -> dict[str, Any]:
    if candidate_ranking_weights is None:
        return {"enabled": False}

    current_scores: list[float] = []
    candidate_scores: list[float] = []
    samples: list[dict[str, Any]] = []
    improved_count = 0
    regressed_count = 0
    unchanged_count = 0

    for current, candidate in zip(current_updates, candidate_updates, strict=False):
        current_score = _score_value(current)
        candidate_score = _score_value(candidate)
        if current_score is not None:
            current_scores.append(current_score)
        if candidate_score is not None:
            candidate_scores.append(candidate_score)
        delta = None
        if current_score is not None and candidate_score is not None:
            delta = round(candidate_score - current_score, 2)
            if delta > 0:
                improved_count += 1
            elif delta < 0:
                regressed_count += 1
            else:
                unchanged_count += 1
        if len(samples) < sample_limit:
            samples.append(
                {
                    "page_id": current["page_id"],
                    "title": current.get("title", ""),
                    "current_final_rank_score": current_score,
                    "candidate_final_rank_score": candidate_score,
                    "score_delta": delta,
                }
            )

    current_average = _average(current_scores)
    candidate_average = _average(candidate_scores)
    average_delta = (
        round(candidate_average - current_average, 2)
        if current_average is not None and candidate_average is not None
        else None
    )
    operator_action_required = bool(regressed_count or average_delta is None or average_delta <= 0)
    if regressed_count:
        operator_action = "Review regressed fixture items before applying candidate ranking.weights."
    elif average_delta is not None and average_delta > 0:
        operator_action = (
            "Candidate ranking.weights improved the local fixture average; review manually before config changes."
        )
    else:
        operator_action = "Keep current ranking.weights unless a larger fixture supports the candidate."

    return {
        "enabled": True,
        "candidate_ranking_weights": candidate_ranking_weights,
        "metric": "final_rank_score",
        "current_average_final_rank_score": current_average,
        "candidate_average_final_rank_score": candidate_average,
        "average_score_delta": average_delta,
        "improved_count": improved_count,
        "regressed_count": regressed_count,
        "unchanged_count": unchanged_count,
        "samples": samples,
        "variants": {
            "current": {
                "name": "current_ranking_weights",
                "signals": {
                    "success": True,
                    "provider": "local_scoring",
                    "model": "ranking_weights.current",
                    "token_cost_estimate": 0.0,
                    "latency_ms": None,
                    "final_rank_score": current_average,
                    "draft_quality_score": None,
                    "safety_risk_flags": [],
                    "duplicate_or_near_duplicate": False,
                    "operator_action_required": False,
                },
            },
            "candidate": {
                "name": "candidate_ranking_weights",
                "signals": {
                    "success": not operator_action_required,
                    "provider": "local_scoring",
                    "model": "ranking_weights.candidate",
                    "token_cost_estimate": 0.0,
                    "latency_ms": None,
                    "final_rank_score": candidate_average,
                    "draft_quality_score": None,
                    "safety_risk_flags": ["score_regression"] if regressed_count else [],
                    "duplicate_or_near_duplicate": False,
                    "operator_action_required": operator_action_required,
                },
            },
        },
        "operator_action": operator_action,
    }


def _operator_action(summary: dict[str, Any]) -> str:
    score_comparison = summary.get("score_comparison")
    if isinstance(score_comparison, dict) and score_comparison.get("enabled"):
        return str(score_comparison.get("operator_action") or "Review score comparison before config changes.")
    if summary["dry_run"] and summary["safety"].get("notion_reads") is False:
        return "Review local fixture score_update_samples; no Notion read or write occurred."
    if summary["dry_run"]:
        return "Review planned score_update_samples, then rerun without --dry-run to update Notion scores."
    if summary["failed"]:
        return "Inspect Notion retry diagnostics or run notion_doctor before rerunning failed score updates."
    return "No operator action required."


def _format_summary(summary: dict[str, Any]) -> str:
    sample_scores = ", ".join(
        f"{sample['page_id']}:{sample['final_rank_score']}" for sample in summary["score_update_samples"]
    )
    if not sample_scores:
        sample_scores = "-"
    score_delta = "-"
    score_comparison = summary.get("score_comparison")
    if isinstance(score_comparison, dict) and score_comparison.get("enabled"):
        score_delta = str(score_comparison.get("average_score_delta"))
    runtime_notes = summary.get("runtime_notes") or {}
    scoring_dependencies = "may_initialize" if runtime_notes.get("scoring_dependencies_may_initialize") else "standard"
    return (
        "recompute_scores complete: "
        f"updated={summary['updated']} total={summary['total']} days={summary['days']} "
        f"mode={summary['mode']} planned={summary['planned']} failed={summary['failed']} "
        f"notion_reads={str(summary['safety']['notion_reads']).lower()} "
        f"notion_writes={str(summary['safety']['notion_writes']).lower()} "
        f"scoring_dependencies={scoring_dependencies} "
        f"score_delta={score_delta} "
        f"sample_final_rank_scores={sample_scores} "
        f"operator_action={summary['operator_action']}"
    )


def _runtime_notes(input_path: str | None) -> dict[str, Any]:
    if not input_path:
        return {
            "input_fixture": False,
            "scoring_dependencies_may_initialize": True,
            "dependency_scope": "notion_recent_pages_and_content_intelligence_scoring",
        }
    return {
        "input_fixture": True,
        "scoring_dependencies_may_initialize": True,
        "dependency_scope": "content_intelligence_scoring_and_optional_ml_model_cache",
        "notion_reads": False,
        "notion_writes": False,
        "zero_dependency_validation_command": "scripts/recompute_scores.py --validate-input --input <path> --json",
        "runtime_contract_gate_command": (
            "scripts/recompute_scores.py --assert-runtime-contract --input <path> --json"
        ),
        "offline_hint": "Prepare ML model caches first before using HF_HUB_OFFLINE=1 for scoring dry-runs.",
    }


async def run(
    days: int,
    limit: int,
    config_path: str,
    *,
    dry_run: bool = False,
    json_output: bool = False,
    sample_limit: int = 3,
    input_path: str | None = None,
) -> int:
    if input_path and not dry_run:
        raise ValueError("--input requires --dry-run so local fixtures cannot update Notion pages")

    _load_runtime_dependencies()
    config_mgr = ConfigManager(config_path)
    notion_reads = input_path is None
    candidate_ranking_weights: dict[str, float] | None = None
    if input_path:
        raw_records, top_examples, candidate_ranking_weights = _load_input_records(input_path)
        pages = raw_records[:limit]

        def extract_record(page: dict[str, Any]) -> dict[str, Any]:
            return page

        update_page_properties = None
    else:
        notion_uploader = NotionUploader(config_mgr)
        feedback_loop = FeedbackLoop(notion_uploader, config_mgr)
        top_examples = await feedback_loop.get_few_shot_examples()
        pages = await notion_uploader.get_recent_pages(days=days, limit=limit)
        extract_record = notion_uploader.extract_page_record
        update_page_properties = notion_uploader.update_page_properties

    updated = 0
    failed = 0
    planned = 0
    samples: list[dict[str, Any]] = []
    current_updates: list[dict[str, Any]] = []
    candidate_updates: list[dict[str, Any]] = []
    for page in pages:
        record = extract_record(page)
        update = _score_update_from_record(
            record,
            top_examples=top_examples,
            ranking_weights=config_mgr.get("ranking.weights", {}),
        )
        current_updates.append(update)
        if candidate_ranking_weights is not None:
            candidate_updates.append(
                _score_update_from_record(
                    record,
                    top_examples=top_examples,
                    ranking_weights=candidate_ranking_weights,
                )
            )
        planned += 1
        if len(samples) < sample_limit:
            samples.append(_score_sample(update))
        if dry_run:
            continue

        if update_page_properties is None:
            raise RuntimeError("update_page_properties unavailable outside Notion write mode")
        ok = await update_page_properties(update["page_id"], update["properties"])
        if ok:
            updated += 1
        else:
            failed += 1

    summary = {
        "mode": "dry-run" if dry_run else "write",
        "dry_run": dry_run,
        "days": days,
        "limit": limit,
        "input_source": str(input_path) if input_path else "notion_recent_pages",
        "total": len(pages),
        "planned": planned,
        "updated": updated,
        "failed": failed,
        "score_update_samples": samples,
        "score_comparison": _build_score_comparison(
            current_updates=current_updates,
            candidate_updates=candidate_updates,
            candidate_ranking_weights=candidate_ranking_weights,
            sample_limit=sample_limit,
        ),
        "safety": {
            "notion_reads": notion_reads,
            "notion_writes": not dry_run,
            "x_posts": False,
            "auto_publish_default": False,
            "manual_publish_required": True,
        },
        "runtime_notes": _runtime_notes(input_path),
    }
    summary["operator_action"] = _operator_action(summary)
    if json_output:
        print(json.dumps(summary, ensure_ascii=False, sort_keys=True))
    else:
        print(_format_summary(summary))
    return 0


def main():
    parser = argparse.ArgumentParser(description="Recompute Blind-to-X Notion scores.")
    parser.add_argument("--config", default="config.yaml")
    parser.add_argument("--days", type=int, default=30)
    parser.add_argument("--limit", type=int, default=100)
    parser.add_argument("--dry-run", action="store_true", help="Compute score updates without writing Notion pages.")
    parser.add_argument("--json", action="store_true", help="Print a structured recompute summary.")
    parser.add_argument(
        "--write-sample-input",
        nargs="?",
        const=str(DEFAULT_SAMPLE_INPUT_PATH),
        metavar="PATH",
        help="Write a known-good local recompute score fixture under .tmp by default.",
    )
    parser.add_argument(
        "--validate-input",
        action="store_true",
        help="Validate a local recompute score fixture without Notion, provider, or browser IO.",
    )
    parser.add_argument(
        "--assert-runtime-contract",
        action="store_true",
        help="Assert the validate-input runtime contract without scoring or runtime dependency loading.",
    )
    parser.add_argument(
        "--input",
        dest="input_path",
        help=(
            "Read local JSON records for an offline score dry-run. Requires --dry-run unless "
            "--validate-input or --assert-runtime-contract is set."
        ),
    )
    args = parser.parse_args()
    if args.write_sample_input is not None:
        raise SystemExit(write_sample_input(args.write_sample_input, json_output=args.json))
    if args.assert_runtime_contract:
        if not args.input_path:
            parser.error("--assert-runtime-contract requires --input")
        raise SystemExit(assert_runtime_contract(args.input_path, json_output=args.json))
    if args.validate_input:
        if not args.input_path:
            parser.error("--validate-input requires --input")
        raise SystemExit(validate_input(args.input_path, json_output=args.json))
    if args.input_path and not args.dry_run:
        parser.error("--input requires --dry-run so local fixtures cannot update Notion pages")

    _load_runtime_dependencies()
    load_env()
    setup_logging()
    raise SystemExit(
        asyncio.run(
            run(
                days=args.days,
                limit=args.limit,
                config_path=args.config,
                dry_run=args.dry_run,
                json_output=args.json,
                input_path=args.input_path,
            )
        )
    )


if __name__ == "__main__":
    main()
