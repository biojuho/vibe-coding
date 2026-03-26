"""P1 운영 효율 고도화 단위 테스트."""


# ── B-1: analytics_tracker 고도화 ───────────────────────────────────


class TestPerformanceGrade:
    """다차원 성과 등급 산정 테스트."""

    @staticmethod
    def _grade(views, likes=0, retweets=0):
        from pipeline.analytics_tracker import AnalyticsTracker
        return AnalyticsTracker._performance_grade(views, likes, retweets)

    def test_s_grade_high_views_with_engagement(self):
        """100K+ 조회 + 참여율 → S등급."""
        # 150K views = 80 base + 좋아요 7500(5%) = 15 + 리트윗 3000(2%) = 10 → 105점 = S
        assert self._grade(150_000, 7500, 3000) == "S"

    def test_s_grade_medium_views_high_engagement(self):
        """50K 조회 + 높은 참여율 → S등급 (보너스로 100점+)."""
        # 50K views = 65 base
        # 좋아요 2500 → 5% 좋아요율 → 15 보너스 (cap)
        # 리트윗 1000 → 2% 리트윗율 → 10 보너스
        # Total = 65 + 15 + 10 = 90 → A등급
        assert self._grade(50_000, 2500, 1000) == "A"

    def test_a_grade(self):
        """50K 조회 + 약간의 참여 → A등급."""
        # 50K views = 65 base + 좋아요 500(1%) = 3 + 리트윗 200(0.4%) = 2 → 70점 = A
        assert self._grade(50_000, 500, 200) == "A"

    def test_b_grade(self):
        """10K 조회 → B등급."""
        assert self._grade(10_000) == "B"

    def test_c_grade(self):
        """3K 조회 → C등급."""
        assert self._grade(3_000) == "C"

    def test_d_grade(self):
        """100 조회 → D등급."""
        assert self._grade(100) == "D"

    def test_engagement_boost(self):
        """3K 조회 + 높은 참여율 → 등급 업."""
        # 3K views = 25 base
        # 좋아요 150 → 5% 좋아요율 → 15 보너스 (cap)
        # 리트윗 60 → 2% 리트윗율 → 10 보너스
        # Total = 25 + 15 + 10 = 50 → B등급 (기존 C → B 업그레이드)
        assert self._grade(3_000, 150, 60) == "B"

    def test_zero_views(self):
        """0 조회 → D등급, 0으로 나누기 없음."""
        assert self._grade(0) == "D"


class TestKstTimeSlot:
    """KST 시간대 슬롯 테스트."""

    def test_returns_valid_slot(self):
        from pipeline.analytics_tracker import AnalyticsTracker
        slot = AnalyticsTracker._kst_time_slot()
        assert slot in {"오전", "점심", "오후", "저녁", "심야"}


# ── B-2: feedback_loop 패턴 분석 ────────────────────────────────────


class TestAnalyzeSuccessPatterns:
    """S/A등급 성공 패턴 분석 테스트."""

    def test_extracts_patterns_from_winners(self):
        from pipeline.feedback_loop import FeedbackLoop
        records = [
            {"performance_grade": "S", "topic_cluster": "연봉", "hook_type": "논쟁형", "emotion_axis": "분노", "final_rank_score": 85},
            {"performance_grade": "A", "topic_cluster": "연봉", "hook_type": "공감형", "emotion_axis": "공감", "final_rank_score": 78},
            {"performance_grade": "A", "topic_cluster": "이직", "hook_type": "논쟁형", "emotion_axis": "경악", "final_rank_score": 72},
            {"performance_grade": "D", "topic_cluster": "직장개그", "hook_type": "공감형", "emotion_axis": "웃김", "final_rank_score": 30},
        ]
        result = FeedbackLoop.analyze_success_patterns(records)
        assert result["count"] == 3  # S + A만
        assert result["top_topics"][0][0] == "연봉"  # 가장 많은 성공 토픽
        assert result["avg_rank_score"] > 0
        assert len(result["insights"]) >= 1

    def test_empty_when_no_winners(self):
        from pipeline.feedback_loop import FeedbackLoop
        records = [{"performance_grade": "D", "topic_cluster": "기타"}]
        result = FeedbackLoop.analyze_success_patterns(records)
        assert result["count"] == 0


class TestGetFailurePatterns:
    """D등급 실패 패턴 필터 테스트."""

    def test_identifies_risky_combo(self):
        from pipeline.feedback_loop import FeedbackLoop
        records = [
            {"performance_grade": "D", "topic_cluster": "정치", "hook_type": "논쟁형"},
            {"performance_grade": "D", "topic_cluster": "정치", "hook_type": "논쟁형"},
            {"performance_grade": "D", "topic_cluster": "정치", "hook_type": "논쟁형"},
            {"performance_grade": "A", "topic_cluster": "연봉", "hook_type": "공감형"},
        ]
        result = FeedbackLoop.get_failure_patterns(records, min_occurrences=3)
        assert result["count"] == 3
        assert len(result["risky_combos"]) >= 1
        assert result["risky_combos"][0][0] == "정치+논쟁형"

    def test_topic_risk_filter(self):
        from pipeline.feedback_loop import FeedbackLoop
        # 정치 토픽 4건 중 3건 D등급 (75%) → 자동 필터 생성
        records = [
            {"performance_grade": "D", "topic_cluster": "정치", "hook_type": "논쟁형"},
            {"performance_grade": "D", "topic_cluster": "정치", "hook_type": "공감형"},
            {"performance_grade": "D", "topic_cluster": "정치", "hook_type": "정보전달형"},
            {"performance_grade": "A", "topic_cluster": "정치", "hook_type": "공감형"},
        ]
        result = FeedbackLoop.get_failure_patterns(records, min_occurrences=3)
        topic_risks = [f for f in result["auto_filters"] if f["type"] == "topic_risk"]
        assert len(topic_risks) >= 1
        assert topic_risks[0]["value"] == "정치"

    def test_no_failures(self):
        from pipeline.feedback_loop import FeedbackLoop
        records = [{"performance_grade": "A", "topic_cluster": "연봉"}]
        result = FeedbackLoop.get_failure_patterns(records)
        assert result["count"] == 0
        assert result["auto_filters"] == []


# ── B-3: publish_optimizer ──────────────────────────────────────────


class TestPublishOptimizer:
    """발행 시간 최적화 테스트."""

    def test_hourly_performance_computation(self):
        from pipeline.publish_optimizer import PublishOptimizer
        records = [
            {"published_at": "2025-03-01T13:00:00+09:00", "views": 5000, "likes": 200, "retweets": 50},
            {"published_at": "2025-03-02T13:30:00+09:00", "views": 8000, "likes": 300, "retweets": 100},
            {"published_at": "2025-03-03T19:00:00+09:00", "views": 3000, "likes": 100, "retweets": 20},
        ]
        result = PublishOptimizer.get_hourly_performance(records)
        assert result["점심"]["count"] == 2
        assert result["점심"]["avg_views"] == 6500.0
        assert result["저녁"]["count"] == 1

    def test_optimal_time_with_enough_data(self):
        from pipeline.publish_optimizer import PublishOptimizer
        records = [
            {"published_at": f"2025-03-{i:02d}T13:00:00+09:00", "views": 5000 + i * 100, "likes": 100, "retweets": 30}
            for i in range(1, 11)  # 10건 점심
        ] + [
            {"published_at": f"2025-03-{i:02d}T19:00:00+09:00", "views": 2000, "likes": 20, "retweets": 5}
            for i in range(1, 11)  # 10건 저녁
        ]
        result = PublishOptimizer.get_optimal_publish_time(records, min_data_points=5)
        assert len(result) >= 2
        # 점심 슬롯이 더 높은 참여율이어야 함
        assert result[0]["slot"] == "점심"
        assert "🏆" in result[0]["reason"]

    def test_default_recommendation_when_no_data(self):
        from pipeline.publish_optimizer import PublishOptimizer
        result = PublishOptimizer.get_optimal_publish_time([], min_data_points=5)
        assert len(result) == 3  # 기본 3개 추천
        assert result[0]["confidence"] == "default"

    def test_extract_time_slot(self):
        from pipeline.publish_optimizer import _extract_time_slot
        assert _extract_time_slot({"published_at": "2025-03-01T08:30:00+09:00"}) == "오전"
        assert _extract_time_slot({"published_at": "2025-03-01T13:00:00+09:00"}) == "점심"
        assert _extract_time_slot({"published_at": "2025-03-01T16:00:00+09:00"}) == "오후"
        assert _extract_time_slot({"published_at": "2025-03-01T20:00:00+09:00"}) == "저녁"
        assert _extract_time_slot({"published_at": "2025-03-01T23:00:00+09:00"}) == "심야"
        assert _extract_time_slot({"published_at": ""}) is None
        assert _extract_time_slot({}) is None
