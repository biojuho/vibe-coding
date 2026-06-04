#!/usr/bin/env python3
"""Deterministic A/B decision helper for auto-research cycles."""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any


VALID_DIRECTIONS = {"higher", "lower", "equal"}


def _load_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise SystemExit(f"manifest not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise SystemExit(f"invalid JSON in {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise SystemExit("manifest root must be a JSON object")
    return data


def _section(data: dict[str, Any], name: str) -> dict[str, Any]:
    value = data.get(name)
    if not isinstance(value, dict):
        raise SystemExit(f"manifest must include object section: {name}")
    return value


def _metrics(section: dict[str, Any], name: str) -> dict[str, float]:
    raw = section.get("metrics")
    if not isinstance(raw, dict):
        raise SystemExit(f"{name}.metrics must be an object")
    metrics: dict[str, float] = {}
    for key, value in raw.items():
        if isinstance(value, bool):
            continue
        if isinstance(value, (int, float)) and math.isfinite(float(value)):
            metrics[str(key)] = float(value)
    return metrics


def _gate_map(data: dict[str, Any], section_name: str, section: dict[str, Any]) -> dict[str, bool]:
    gates = section.get("gates")
    if gates is None:
        all_gates = data.get("gates")
        if isinstance(all_gates, dict):
            gates = all_gates.get(section_name)
    if gates is None:
        return {}
    if not isinstance(gates, dict):
        raise SystemExit(f"{section_name}.gates must be an object when provided")
    return {str(key): bool(value) for key, value in gates.items()}


def _weighted_delta(baseline: float, candidate: float, direction: str) -> float:
    denominator = abs(baseline) if abs(baseline) > 1e-12 else 1.0
    if direction == "higher":
        return (candidate - baseline) / denominator
    if direction == "lower":
        return (baseline - candidate) / denominator
    if direction == "equal":
        return -abs(candidate - baseline) / denominator
    raise SystemExit(f"invalid metric direction: {direction}")


def decide(data: dict[str, Any]) -> dict[str, Any]:
    baseline_section = _section(data, "baseline")
    candidate_section = _section(data, "candidate")
    baseline_metrics = _metrics(baseline_section, "baseline")
    candidate_metrics = _metrics(candidate_section, "candidate")

    directions = data.get("directions") or {}
    weights = data.get("weights") or {}
    if not isinstance(directions, dict):
        raise SystemExit("directions must be an object when provided")
    if not isinstance(weights, dict):
        raise SystemExit("weights must be an object when provided")

    common = sorted(set(baseline_metrics) & set(candidate_metrics))
    if not common:
        raise SystemExit("baseline and candidate must share at least one numeric metric")

    contributions: dict[str, dict[str, float | str]] = {}
    score_delta = 0.0
    total_weight = 0.0
    warnings: list[str] = []

    for metric in common:
        direction = str(directions.get(metric, "higher")).lower()
        if direction not in VALID_DIRECTIONS:
            raise SystemExit(f"{metric} direction must be one of: {', '.join(sorted(VALID_DIRECTIONS))}")
        weight_value = weights.get(metric, 1.0)
        if isinstance(weight_value, bool) or not isinstance(weight_value, (int, float)):
            raise SystemExit(f"{metric} weight must be numeric")
        weight = float(weight_value)
        if weight < 0 or not math.isfinite(weight):
            raise SystemExit(f"{metric} weight must be a finite non-negative number")
        if weight == 0:
            warnings.append(f"{metric} has zero weight")
            continue

        delta = _weighted_delta(baseline_metrics[metric], candidate_metrics[metric], direction)
        contribution = delta * weight
        score_delta += contribution
        total_weight += weight
        contributions[metric] = {
            "baseline": baseline_metrics[metric],
            "candidate": candidate_metrics[metric],
            "direction": direction,
            "weight": weight,
            "relative_delta": delta,
            "contribution": contribution,
        }

    if total_weight <= 0:
        raise SystemExit("at least one shared metric must have a positive weight")

    normalized_delta = score_delta / total_weight
    min_delta = float(data.get("min_delta", 0.0))
    required_gates = data.get("required_gates") or []
    if not isinstance(required_gates, list):
        raise SystemExit("required_gates must be a list when provided")

    candidate_gates = _gate_map(data, "candidate", candidate_section)
    baseline_gates = _gate_map(data, "baseline", baseline_section)
    failed_gates = [str(gate) for gate in required_gates if not candidate_gates.get(str(gate), False)]
    baseline_failed = [str(gate) for gate in required_gates if gate in baseline_gates and not baseline_gates[str(gate)]]
    if baseline_failed:
        warnings.append("baseline failed gates: " + ", ".join(baseline_failed))

    if failed_gates:
        decision = "reject_candidate"
        reason = "candidate failed required gates"
    elif normalized_delta > min_delta:
        decision = "adopt_candidate"
        reason = "candidate improved weighted score"
    else:
        decision = "keep_baseline"
        reason = "candidate did not clear min_delta"

    return {
        "decision": decision,
        "reason": reason,
        "score_delta": normalized_delta,
        "min_delta": min_delta,
        "failed_gates": failed_gates,
        "warnings": warnings,
        "metrics": contributions,
    }


def _print_text(result: dict[str, Any]) -> None:
    print(f"decision: {result['decision']}")
    print(f"reason: {result['reason']}")
    print(f"score_delta: {result['score_delta']:.6f}")
    if result["failed_gates"]:
        print("failed_gates: " + ", ".join(result["failed_gates"]))
    if result["warnings"]:
        print("warnings: " + "; ".join(result["warnings"]))
    print("metrics:")
    for name, item in result["metrics"].items():
        print(
            f"  - {name}: baseline={item['baseline']} candidate={item['candidate']} "
            f"direction={item['direction']} contribution={item['contribution']:.6f}"
        )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path, help="Path to A/B manifest JSON")
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of text")
    args = parser.parse_args(argv)

    result = decide(_load_json(args.manifest))
    if args.json:
        json.dump(result, sys.stdout, ensure_ascii=False, indent=2)
        print()
    else:
        _print_text(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
