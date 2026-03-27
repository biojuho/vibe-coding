"""
test_performance_benchmark.py — 엔진 성능 벤치마크
===================================================
각 엔진의 렌더링 속도를 측정하여 성능 기준선을 설정하고,
성능 저하(regression)를 자동 감지합니다.

사용법:
    pytest tests/unit/test_performance_benchmark.py -v --tb=short
    pytest tests/unit/test_performance_benchmark.py -k "benchmark" -v

벤치마크 결과는 .tmp/benchmarks/latest.json 에 저장됩니다.
"""

import json
import sys
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

# ── 설정 ──────────────────────────────────────────────────────────────

_BENCHMARK_DIR = Path(__file__).resolve().parents[2] / ".tmp" / "benchmarks"
_CHANNEL_CONFIG = {
    "palette": {
        "bg": "#0A0E1A",
        "primary": "#00D4FF",
        "accent": "#00FF88",
        "secondary": "#7C3AED",
    },
    "font_title": "Pretendard-ExtraBold",
    "font_body": "Pretendard-Regular",
    "hook_style": "popup",
    "keyword_highlights": {"numbers": "#FFD700"},
}

# 성능 기준 (초) — 이 시간을 초과하면 경고
_PERF_THRESHOLDS = {
    "text_render_subtitle": 2.0,
    "text_render_glow": 3.0,
    "text_render_badge": 1.0,
    "text_render_gradient": 5.0,
    "text_render_progress_bar": 1.0,
    "bg_create_gradient": 1.0,
    "bg_create_particle": 1.0,
    "bg_create_grid": 1.0,
    "bg_create_noise": 2.0,
    "bg_create_scanline": 1.0,
    "bg_create_mesh_gradient": 5.0,
    "layout_split_screen": 2.0,
    "layout_card": 2.0,
    "color_grading_frame": 1.0,
}


@dataclass
class BenchmarkResult:
    """벤치마크 결과."""

    name: str
    duration_ms: float
    threshold_ms: float
    passed: bool
    iterations: int = 1
    metadata: dict = field(default_factory=dict)


class BenchmarkCollector:
    """벤치마크 결과 수집기."""

    def __init__(self):
        self.results: list[BenchmarkResult] = []

    def add(self, result: BenchmarkResult):
        self.results.append(result)

    def save(self):
        """결과를 JSON으로 저장."""
        _BENCHMARK_DIR.mkdir(parents=True, exist_ok=True)
        data = {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "results": [asdict(r) for r in self.results],
            "summary": {
                "total": len(self.results),
                "passed": sum(1 for r in self.results if r.passed),
                "failed": sum(1 for r in self.results if not r.passed),
            },
        }
        path = _BENCHMARK_DIR / "latest.json"
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        return path

    def print_summary(self):
        """벤치마크 요약 출력."""
        lines = []
        lines.append("\n" + "=" * 70)
        lines.append("Performance Benchmark Results")
        lines.append("=" * 70)
        for r in self.results:
            status = "PASS" if r.passed else "FAIL"
            lines.append(f"  [{status}] {r.name:<35} {r.duration_ms:>8.1f}ms / {r.threshold_ms:>8.1f}ms")
        lines.append("-" * 70)
        total = len(self.results)
        passed = sum(1 for r in self.results if r.passed)
        lines.append(f"  Total {total} | PASS {passed} | FAIL {total - passed}")
        lines.append("=" * 70)
        try:
            print("\n".join(lines))
        except UnicodeEncodeError:
            print("\n".join(lines).encode("ascii", errors="replace").decode("ascii"))


_collector = BenchmarkCollector()


def _benchmark(name: str, fn, iterations: int = 3, **metadata) -> BenchmarkResult:
    """함수를 반복 실행하여 평균 소요 시간 측정."""
    times = []
    for _ in range(iterations):
        start = time.perf_counter()
        fn()
        elapsed = time.perf_counter() - start
        times.append(elapsed)

    avg_ms = (sum(times) / len(times)) * 1000
    threshold = _PERF_THRESHOLDS.get(name, 5.0) * 1000
    result = BenchmarkResult(
        name=name,
        duration_ms=round(avg_ms, 2),
        threshold_ms=threshold,
        passed=avg_ms <= threshold,
        iterations=iterations,
        metadata=metadata,
    )
    _collector.add(result)
    return result


# ── TextEngine 벤치마크 ──────────────────────────────────────────────


class TestTextEngineBenchmark:
    """TextEngine 렌더링 성능 벤치마크."""

    @pytest.fixture
    def engine(self):
        from ShortsFactory.engines.text_engine import TextEngine

        return TextEngine(_CHANNEL_CONFIG)

    def test_benchmark_render_subtitle(self, engine, tmp_path):
        """자막 렌더링 속도."""

        def run():
            engine.render_subtitle(
                "성능 테스트 자막입니다 - 3배 향상",
                role="body",
                output_path=tmp_path / f"sub_{time.time_ns()}.png",
            )

        result = _benchmark("text_render_subtitle", run)
        assert result.passed, f"성능 저하: {result.duration_ms:.1f}ms > {result.threshold_ms:.1f}ms"

    def test_benchmark_render_glow(self, engine, tmp_path):
        """글로우 자막 렌더링 속도."""

        def run():
            engine.render_subtitle_with_glow(
                "네온 글로우 테스트",
                output_path=tmp_path / f"glow_{time.time_ns()}.png",
            )

        result = _benchmark("text_render_glow", run)
        assert result.passed, f"성능 저하: {result.duration_ms:.1f}ms > {result.threshold_ms:.1f}ms"

    def test_benchmark_render_badge(self, engine, tmp_path):
        """배지 렌더링 속도."""

        def run():
            engine.render_badge(
                7,
                output_path=tmp_path / f"badge_{time.time_ns()}.png",
            )

        result = _benchmark("text_render_badge", run)
        assert result.passed, f"성능 저하: {result.duration_ms:.1f}ms > {result.threshold_ms:.1f}ms"

    def test_benchmark_render_gradient_text(self, engine, tmp_path):
        """그라데이션 텍스트 속도."""

        def run():
            engine.render_gradient_text(
                "그라데이션 테스트",
                output_path=tmp_path / f"grad_{time.time_ns()}.png",
            )

        result = _benchmark("text_render_gradient", run)
        assert result.passed, f"성능 저하: {result.duration_ms:.1f}ms > {result.threshold_ms:.1f}ms"

    def test_benchmark_render_progress_bar(self, engine, tmp_path):
        """프로그레스 바 속도."""

        def run():
            engine.render_progress_bar(
                0.7,
                output_path=tmp_path / f"prog_{time.time_ns()}.png",
            )

        result = _benchmark("text_render_progress_bar", run)
        assert result.passed, f"성능 저하: {result.duration_ms:.1f}ms > {result.threshold_ms:.1f}ms"


# ── BackgroundEngine 벤치마크 ────────────────────────────────────────


class TestBackgroundEngineBenchmark:
    """BackgroundEngine 렌더링 성능 벤치마크."""

    @pytest.fixture
    def engine(self):
        from ShortsFactory.engines.background_engine import BackgroundEngine

        return BackgroundEngine(_CHANNEL_CONFIG)

    def test_benchmark_create_gradient(self, engine, tmp_path):
        """그라데이션 배경 생성 속도."""

        def run():
            engine.create_gradient(
                540,
                960,
                output_path=tmp_path / f"bg_{time.time_ns()}.png",
            )

        result = _benchmark("bg_create_gradient", run)
        assert result.passed

    def test_benchmark_create_particle(self, engine, tmp_path):
        """파티클 오버레이 생성 속도."""

        def run():
            engine.create_particle_overlay(
                540,
                960,
                output_path=tmp_path / f"px_{time.time_ns()}.png",
            )

        result = _benchmark("bg_create_particle", run)
        assert result.passed

    def test_benchmark_create_grid(self, engine, tmp_path):
        """그리드 오버레이 생성 속도."""

        def run():
            engine.create_grid_overlay(
                540,
                960,
                output_path=tmp_path / f"grid_{time.time_ns()}.png",
            )

        result = _benchmark("bg_create_grid", run)
        assert result.passed

    def test_benchmark_create_noise(self, engine, tmp_path):
        """노이즈 텍스처 생성 속도."""

        def run():
            engine.create_noise_texture(
                540,
                960,
                output_path=tmp_path / f"noise_{time.time_ns()}.png",
            )

        result = _benchmark("bg_create_noise", run)
        assert result.passed

    def test_benchmark_create_scanline(self, engine, tmp_path):
        """스캔라인 오버레이 생성 속도."""

        def run():
            engine.create_scanline_overlay(
                540,
                960,
                output_path=tmp_path / f"scan_{time.time_ns()}.png",
            )

        result = _benchmark("bg_create_scanline", run)
        assert result.passed

    def test_benchmark_create_mesh_gradient(self, engine, tmp_path):
        """메쉬 그라데이션 생성 속도 (가장 무거운 연산)."""

        def run():
            engine.create_mesh_gradient(
                270,
                480,  # 작은 크기로 테스트
                num_points=3,
                blur_radius=30,
                output_path=tmp_path / f"mesh_{time.time_ns()}.png",
            )

        result = _benchmark("bg_create_mesh_gradient", run)
        assert result.passed


# ── LayoutEngine 벤치마크 ────────────────────────────────────────────


class TestLayoutEngineBenchmark:
    """LayoutEngine 렌더링 성능 벤치마크."""

    @pytest.fixture
    def engine(self):
        from ShortsFactory.engines.layout_engine import LayoutEngine

        return LayoutEngine(_CHANNEL_CONFIG)

    def test_benchmark_split_screen(self, engine, tmp_path):
        """분할 화면 생성 속도."""

        def run():
            engine.split_screen(
                "좋은 예시",
                "나쁜 예시",
                output_path=tmp_path / f"split_{time.time_ns()}.png",
            )

        result = _benchmark("layout_split_screen", run)
        assert result.passed

    def test_benchmark_card_layout(self, engine, tmp_path):
        """카드 레이아웃 생성 속도."""
        items = [{"title": f"항목 {i}", "body": f"설명 {i}"} for i in range(5)]

        def run():
            engine.card_layout(
                items,
                output_path=tmp_path / f"card_{time.time_ns()}.png",
            )

        result = _benchmark("layout_card", run)
        assert result.passed


# ── ColorEngine 벤치마크 ─────────────────────────────────────────────


class TestColorEngineBenchmark:
    """ColorEngine 프레임 처리 성능 벤치마크."""

    def test_benchmark_grading_frame(self, tmp_path):
        """단일 프레임 컬러 그레이딩 속도."""
        from ShortsFactory.engines.color_engine import ColorEngine

        engine = ColorEngine("neon_tech")

        # 가짜 클립 (get_frame만 제공)
        frame = np.random.randint(0, 255, (960, 540, 3), dtype=np.uint8)

        class FakeClip:
            size = (540, 960)

            def transform(self, fn):
                # fn을 한 번 실행하여 성능 측정
                fn(lambda t: frame, 0.0)
                return self

        def run():
            engine.apply_grading(FakeClip())

        result = _benchmark("color_grading_frame", run, iterations=5)
        assert result.passed


# ── 벤치마크 결과 저장 ──────────────────────────────────────────────


@pytest.fixture(scope="session", autouse=True)
def save_benchmark_results():
    """모든 테스트 완료 후 벤치마크 결과 저장."""
    yield
    if _collector.results:
        path = _collector.save()
        _collector.print_summary()
        print(f"\n  결과 저장: {path}")
