"""StyleTracker 유닛 테스트 — manifest 기반 + SQLite Thompson Sampling."""

from __future__ import annotations

import json
from pathlib import Path

from shorts_maker_v2.utils.style_tracker import StyleTracker

# ── manifest 기반 메서드 ─────────────────────────────────────────────────────


class TestStyleTrackerManifest:
    """manifest 파일 스캔 기반 weighted_pick / get_success_counts."""

    def _write_manifest(self, d, name, status, ab_variant):
        mf = d / f"{name}_manifest.json"
        mf.write_text(json.dumps({"status": status, "ab_variant": ab_variant}), encoding="utf-8")

    def test_no_output_dir(self, tmp_path):
        """output_dir가 없으면 빈 결과."""
        tracker = StyleTracker(tmp_path / "nonexistent", db_path=tmp_path / "db.sqlite")
        assert tracker.get_success_counts("hook_pattern") == {}

    def test_empty_output_dir(self, tmp_path):
        """manifest가 없으면 빈 결과."""
        tracker = StyleTracker(tmp_path, db_path=tmp_path / "db.sqlite")
        assert tracker.get_success_counts("hook_pattern") == {}

    def test_default_db_path_is_used_when_omitted(self, tmp_path):
        """db_path를 생략하면 기본 경로를 사용한다."""
        tracker = StyleTracker(tmp_path)
        assert tracker._db_path == Path(".tmp") / "style_performance.db"

    def test_loads_success_counts(self, tmp_path):
        """성공 manifest에서 카운트 집계."""
        self._write_manifest(tmp_path, "a", "success", {"hook_pattern": "질문형"})
        self._write_manifest(tmp_path, "b", "success", {"hook_pattern": "질문형"})
        self._write_manifest(tmp_path, "c", "success", {"hook_pattern": "충격형"})
        self._write_manifest(tmp_path, "d", "failed", {"hook_pattern": "공감형"})

        tracker = StyleTracker(tmp_path, db_path=tmp_path / "db.sqlite")
        counts = tracker.get_success_counts("hook_pattern")
        assert counts["질문형"] == 2
        assert counts["충격형"] == 1
        assert counts.get("공감형", 0) == 0  # 실패는 0 증가

    def test_skips_invalid_manifest(self, tmp_path):
        """잘못된 JSON은 무시."""
        (tmp_path / "bad_manifest.json").write_text("NOT JSON", encoding="utf-8")
        self._write_manifest(tmp_path, "ok", "success", {"x": "y"})

        tracker = StyleTracker(tmp_path, db_path=tmp_path / "db.sqlite")
        assert tracker.get_success_counts("x") == {"y": 1}

    def test_skips_missing_ab_variant(self, tmp_path):
        """ab_variant가 없는 manifest는 무시."""
        mf = tmp_path / "no_ab_manifest.json"
        mf.write_text(json.dumps({"status": "success"}), encoding="utf-8")

        tracker = StyleTracker(tmp_path, db_path=tmp_path / "db.sqlite")
        assert tracker.get_success_counts("any") == {}

    def test_weighted_pick_uniform_when_low_data(self, tmp_path):
        """데이터가 min_data 미만이면 uniform random."""
        self._write_manifest(tmp_path, "a", "success", {"k": "v1"})

        tracker = StyleTracker(tmp_path, db_path=tmp_path / "db.sqlite")
        result = tracker.weighted_pick("k", ["v1", "v2", "v3"], min_data=10)
        assert result in ["v1", "v2", "v3"]

    def test_weighted_pick_favors_winner(self, tmp_path):
        """충분한 데이터 시 성공 비율이 높은 쪽이 유리."""
        for i in range(20):
            self._write_manifest(tmp_path, f"w{i}", "success", {"style": "winner"})
        for i in range(2):
            self._write_manifest(tmp_path, f"l{i}", "success", {"style": "loser"})

        tracker = StyleTracker(tmp_path, db_path=tmp_path / "db.sqlite")
        picks = [tracker.weighted_pick("style", ["winner", "loser"]) for _ in range(100)]
        assert picks.count("winner") > picks.count("loser")

    def test_weighted_pick_empty_candidates(self, tmp_path):
        """빈 후보 리스트면 빈 문자열."""
        tracker = StyleTracker(tmp_path, db_path=tmp_path / "db.sqlite")
        assert tracker.weighted_pick("x", []) == ""

    def test_max_manifests_limit(self, tmp_path):
        """max_manifests 제한 준수."""
        for i in range(10):
            self._write_manifest(tmp_path, f"m{i}", "success", {"k": "v"})

        tracker = StyleTracker(tmp_path, max_manifests=3, db_path=tmp_path / "db.sqlite")
        counts = tracker.get_success_counts("k")
        assert counts.get("v", 0) <= 3


# ── SQLite Thompson Sampling ────────────────────────────────────────────────


class TestStyleTrackerThompson:
    """record_performance / get_weighted_combo / get_performance_stats."""

    def test_record_and_retrieve_performance(self, tmp_path):
        """성과 기록 후 stats 조회."""
        tracker = StyleTracker(tmp_path, db_path=tmp_path / "perf.db")
        tracker.record_performance("ch1", "bold_white", views=10000, likes=400)
        tracker.record_performance("ch1", "bold_white", views=5000, likes=200)
        tracker.record_performance("ch1", "minimal_black", views=8000, likes=100)

        stats = tracker.get_performance_stats("ch1")
        assert len(stats) == 2
        names = {s["combo_name"] for s in stats}
        assert names == {"bold_white", "minimal_black"}

        bw = next(s for s in stats if s["combo_name"] == "bold_white")
        assert bw["views"] == 15000
        assert bw["likes"] == 600
        assert bw["trials"] == 2

    def test_success_threshold(self, tmp_path):
        """좋아요/조회수 비율에 따른 성공 판정."""
        tracker = StyleTracker(tmp_path, db_path=tmp_path / "perf.db", success_threshold=0.05)
        # 6% → 성공
        tracker.record_performance("ch1", "good", views=1000, likes=60)
        # 2% → 실패
        tracker.record_performance("ch1", "bad", views=1000, likes=20)

        stats = tracker.get_performance_stats("ch1")
        good = next(s for s in stats if s["combo_name"] == "good")
        bad = next(s for s in stats if s["combo_name"] == "bad")
        assert good["successes"] == 1
        assert bad["successes"] == 0

    def test_zero_views_not_success(self, tmp_path):
        """조회수 0이면 성공 아님."""
        tracker = StyleTracker(tmp_path, db_path=tmp_path / "perf.db")
        tracker.record_performance("ch1", "x", views=0, likes=0)

        stats = tracker.get_performance_stats("ch1")
        assert stats[0]["successes"] == 0

    def test_get_weighted_combo_thompson(self, tmp_path):
        """Thompson Sampling으로 콤보 선택."""
        tracker = StyleTracker(tmp_path, db_path=tmp_path / "perf.db")
        # 높은 성공률 콤보
        for _ in range(20):
            tracker.record_performance("ch1", "winner", views=10000, likes=500)
        # 낮은 성공률 콤보
        for _ in range(20):
            tracker.record_performance("ch1", "loser", views=10000, likes=100)

        picks = [tracker.get_weighted_combo("ch1") for _ in range(50)]
        assert "winner" in picks  # winner가 최소 한 번은 선택됨

    def test_get_weighted_combo_fallback_to_manifest(self, tmp_path):
        """DB에 데이터 없으면 manifest fallback."""
        mf = tmp_path / "job_manifest.json"
        mf.write_text(
            json.dumps({"status": "success", "ab_variant": {"caption_combo": "retro"}}),
            encoding="utf-8",
        )

        tracker = StyleTracker(tmp_path, db_path=tmp_path / "perf.db")
        result = tracker.get_weighted_combo("nonexistent_channel")
        # retro가 유일한 후보이므로 retro 반환
        assert result == "retro"

    def test_get_weighted_combo_no_data_at_all(self, tmp_path):
        """어디에도 데이터 없으면 빈 문자열."""
        tracker = StyleTracker(tmp_path / "empty", db_path=tmp_path / "perf.db")
        assert tracker.get_weighted_combo("no_channel") == ""

    def test_get_performance_stats_empty_channel(self, tmp_path):
        """없는 채널 조회 시 빈 리스트."""
        tracker = StyleTracker(tmp_path, db_path=tmp_path / "perf.db")
        tracker._ensure_db()  # DB 초기화만 수행
        assert tracker.get_performance_stats("nonexistent") == []

    def test_db_idempotent_init(self, tmp_path):
        """_ensure_db 중복 호출 안전."""
        tracker = StyleTracker(tmp_path, db_path=tmp_path / "perf.db")
        tracker._ensure_db()
        tracker._ensure_db()
        tracker.record_performance("ch1", "x", views=100, likes=5)
        assert len(tracker.get_performance_stats("ch1")) == 1

    def test_ensure_db_returns_if_initialized_inside_lock(self, tmp_path):
        """락 대기 중 초기화가 끝나면 내부 재검사로 바로 반환한다."""
        tracker = StyleTracker(tmp_path, db_path=tmp_path / "perf.db")

        class _FlipLock:
            def __enter__(self):
                tracker._db_initialized = True
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

        tracker._db_lock = _FlipLock()
        tracker._ensure_db()

        assert tracker._db_initialized is True
        assert not tracker._db_path.exists()
