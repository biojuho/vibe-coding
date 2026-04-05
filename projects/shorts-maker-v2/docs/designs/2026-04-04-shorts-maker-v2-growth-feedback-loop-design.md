# Feature: Closed-Loop Growth Engine

## Summary

`shorts-maker-v2` already has strong generation primitives:

- `TrendDiscoveryStep` for input discovery
- `TopicAngleGenerator` for hook/title shaping
- `StyleTracker` for post-hoc style learning
- `SeriesEngine` for follow-up topic suggestions
- `workspace/execution/youtube_analytics_collector.py` and `workspace/execution/yt_analytics_to_notion.py` for shared YouTube metric collection

The missing layer is the product loop that turns post-publish performance into the next production decision.

This design adds a project-local growth engine that:

1. Ingests post-publish video metrics
2. Maps them back to `ab_variant` metadata already stored in manifests
3. Updates `StyleTracker` with real audience feedback
4. Produces ranked variant reports and next-action recommendations
5. Feeds `SeriesEngine` with actual topic performance instead of zeroed placeholders

## Why This Is Priority 1

- Revenue impact: this creates a premium optimization layer, not just a generator.
- Traffic impact: it moves the product from "guess good topics" to "learn what the audience actually rewards."
- Build leverage: most of the substrate already exists in the repo.
- Low integration risk: step 1 can live beside the current orchestrator without breaking the render path.

## Commercial Benchmarks

- `vidIQ` emphasizes personalized daily ideas based on channel history and similar-channel performance.
- `TubeBuddy` emphasizes post-publish A/B testing and delayed winner selection from live data blocks.
- `OpusClip` exposes a virality score that turns content quality into an actionable ranking surface.
- `YouTube` itself is shipping creator-side inspiration and trends surfaces inside Studio and Shorts.

The opportunity for `shorts-maker-v2` is to combine those ideas into one loop owned by the product:

- pre-publish opportunity scoring
- post-publish learning
- next-batch optimization

## Step 1 Scope

Step 1 is intentionally narrow:

- add project-local growth data models
- add an abstract metrics-source interface
- add a concrete growth engine that:
  - ingests `VideoPerformanceSnapshot`
  - updates `StyleTracker`
  - ranks a chosen variant field such as `caption_combo`
  - suggests a series follow-up from real performance
- add tests for the core loop

## Step 1 Non-Goals

- no automatic metadata swapping yet
- no direct YouTube OAuth flow inside `shorts-maker-v2` yet
- no dashboard UI yet
- no long-running scheduler yet
- no ML model training yet

## Integration Plan

### Phase A

- `workspace/execution/*youtube*` continues to collect shared metrics
- a thin project adapter converts those metrics into `VideoPerformanceSnapshot`
- `GrowthLoopEngine` emits recommendations

### Phase B

- add CLI entrypoint such as `shorts-maker-v2 growth-sync`
- persist ranked reports into `.tmp/` and/or `logs/`
- use the top recommendation to choose caption combos and series follow-ups for the next batch

### Phase C

- fold opportunity ranking back into `auto-topic`
- add channel-level optimization reports
- support richer metrics like `averageViewDuration`, `averageViewPercentage`, `engagedViews`, `subscribersGained`, and `impressions` when the analytics source supports them

## Libraries

Current step 1 uses:

- Python stdlib: `dataclasses`, `datetime`, `typing`, `statistics`
- existing project modules: `StyleTracker`, `SeriesEngine`

Recommended next-step integrations:

- `google-api-python-client`
- `google-auth-oauthlib`
- `google-auth-httplib2`
- `requests`
- `duckdb` (optional, for offline feature-store style analysis)

## Entry Points

- `src/shorts_maker_v2/growth/models.py`
- `src/shorts_maker_v2/growth/feedback_loop.py`
- `tests/unit/test_growth_feedback_loop.py`

## Future Tasks

- Add a metrics adapter that wraps `workspace/execution/youtube_analytics_collector.py`
- Add manifest scan helpers that join `JobManifest.ab_variant` with live video stats
- Add topic opportunity ranking that combines trend score with channel fit
- Add a scheduler that syncs metrics daily and writes a "next batch" recommendation artifact
