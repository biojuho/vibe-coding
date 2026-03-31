These archived tests target the legacy V1 `ShortsFactory` template engine.

They were moved out of `tests/legacy/` on 2026-03-27 so the default pytest collection for the active V2 pipeline stays focused on `tests/`.

Files kept here:
- `test_ai_news_generator.py`
- `test_edge_client.py`
- `test_future_countdown.py`
- `test_ssml.py`
- `test_tech_vs.py`
- `unit/test_engines_v2.py`
- `unit/test_engines_v2_extended.py`
- `unit/test_interfaces.py`
- `unit/test_performance_benchmark.py`
- `unit/test_shorts_factory.py`
- `unit/test_shorts_factory_plan_overlay.py`
- `unit/test_visual_regression.py`
- `unit/test_visual_regression_quality.py`
- `integration/test_shorts_factory_e2e.py`

If we need to revisit V1 compatibility later, we can run these tests explicitly by path.
