"""Tests for local inference benchmark helpers."""

from __future__ import annotations

import json
from types import SimpleNamespace

from execution import benchmark_local


def test_match_expected_keywords_case_insensitive():
    matched, accuracy = benchmark_local._match_expected_keywords(
        "DEF factorial returns a Value",
        ["def", "return", "missing"],
    )

    assert matched == ["def", "return"]
    assert accuracy == 2 / 3


def test_summarize_ollama_results_calculates_totals():
    stats = benchmark_local._summarize_ollama_results(
        [
            {
                "status": "success",
                "complexity": "SIMPLE",
                "elapsed_sec": 2.0,
                "tokens_per_sec": 10.0,
                "keyword_accuracy": 0.5,
                "input_tokens": 20,
                "output_tokens": 30,
            },
            {
                "status": "error",
                "complexity": "SIMPLE",
                "elapsed_sec": 1.0,
            },
        ],
        total_prompts=2,
    )

    assert stats["successful"] == 1
    assert stats["failed"] == 1
    assert stats["avg_elapsed_sec"] == 2.0
    assert stats["avg_tokens_per_sec"] == 10.0
    assert stats["avg_keyword_accuracy"] == 0.5
    assert stats["avg_elapsed_simple"] == 2.0
    assert stats["estimated_cloud_cost"]["ollama_local"] == 0.0


def test_run_single_benchmark_success(monkeypatch):
    times = iter([10.0, 12.0])
    monkeypatch.setattr(benchmark_local.time, "perf_counter", lambda: next(times))

    class FakeClient:
        default_model = "default-model"

        def __init__(self) -> None:
            self.calls = []

        def generate(self, **kwargs):
            self.calls.append(kwargs)
            return "def factorial returns value", 10, 20

    client = FakeClient()
    result = benchmark_local.run_single_benchmark(
        client,
        {
            "id": "T1",
            "complexity": "SIMPLE",
            "system": "system",
            "prompt": "prompt",
            "expected_keywords": ["def", "factorial", "return"],
        },
        model="chosen-model",
    )

    assert result["status"] == "success"
    assert result["elapsed_sec"] == 2.0
    assert result["tokens_per_sec"] == 10.0
    assert result["keyword_accuracy"] == 1.0
    assert result["matched_keywords"] == ["def", "factorial", "return"]
    assert client.calls[0]["model"] == "chosen-model"


def test_run_single_benchmark_error(monkeypatch):
    times = iter([3.0, 4.25])
    monkeypatch.setattr(benchmark_local.time, "perf_counter", lambda: next(times))

    class FakeClient:
        default_model = "default-model"

        def generate(self, **_kwargs):
            raise RuntimeError("boom")

    result = benchmark_local.run_single_benchmark(
        FakeClient(),
        {
            "id": "T2",
            "complexity": "SIMPLE",
            "system": "system",
            "prompt": "prompt",
            "expected_keywords": ["def"],
        },
    )

    assert result["status"] == "error"
    assert result["error"] == "boom"
    assert result["elapsed_sec"] == 1.25


def test_run_benchmark_uses_fakes_and_writes_output(tmp_path, monkeypatch, capsys):
    prompts = [
        {
            "id": "S1",
            "complexity": "SIMPLE",
            "system": "system",
            "prompt": "prompt one",
            "expected_keywords": ["def", "return"],
        },
        {
            "id": "S2",
            "complexity": "SIMPLE",
            "system": "system",
            "prompt": "prompt two",
            "expected_keywords": ["def"],
        },
    ]
    instances = []

    class FakeOllamaClient:
        default_model = "fake-default"

        def __init__(self) -> None:
            self.closed = False
            instances.append(self)

        def is_available(self):
            return True

        def list_models(self):
            return ["fake-default"]

        def generate(self, **_kwargs):
            return "def return", 3, 7

        def close(self):
            self.closed = True

    class FakeSmartRouter:
        def classify(self, _prompt):
            return SimpleNamespace(
                complexity=SimpleNamespace(value="simple"),
                score=0.12345,
            )

    monkeypatch.setattr(benchmark_local, "BENCHMARK_PROMPTS", prompts)
    monkeypatch.setattr(benchmark_local, "WORKSPACE_ROOT", tmp_path)
    monkeypatch.setattr(benchmark_local, "OllamaClient", FakeOllamaClient)
    monkeypatch.setattr(benchmark_local, "SmartRouter", FakeSmartRouter)
    monkeypatch.setattr(benchmark_local.time, "strftime", lambda _fmt: "2026-05-12T00:00:00")

    output = benchmark_local.run_benchmark(model="fake-default")
    capsys.readouterr()

    output_path = tmp_path / ".tmp" / "benchmark_results.json"
    saved = json.loads(output_path.read_text(encoding="utf-8"))
    assert output["stats"]["successful"] == 2
    assert output["router_accuracy"][0]["match"] is True
    assert saved["model"] == "fake-default"
    assert instances[0].closed is True


def test_run_benchmark_closes_unavailable_client(monkeypatch):
    instances = []

    class UnavailableClient:
        default_model = "fake-default"

        def __init__(self) -> None:
            self.closed = False
            instances.append(self)

        def is_available(self):
            return False

        def close(self):
            self.closed = True

    monkeypatch.setattr(benchmark_local, "OllamaClient", UnavailableClient)

    result = benchmark_local.run_benchmark()

    assert result == {"error": "Ollama server not available"}
    assert instances[0].closed is True
