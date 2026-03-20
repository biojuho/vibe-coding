from __future__ import annotations

import argparse
import shutil
import sys
from dataclasses import replace
from pathlib import Path

from dotenv import load_dotenv

from shorts_maker_v2.config import AppConfig, ConfigError, load_config, required_env_keys, validate_environment
from shorts_maker_v2.models import BatchResult
from shorts_maker_v2.pipeline.orchestrator import PipelineOrchestrator
from shorts_maker_v2.utils.channel_router import get_router
from shorts_maker_v2.utils.cost_tracker import CostTracker


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="YouTube Shorts one-click generator (MVP)")
    subparsers = parser.add_subparsers(dest="command", required=True)

    run_parser = subparsers.add_parser("run", help="Generate one shorts video")
    run_parser.add_argument(
        "--topic", type=str, required=False, default="", help="Shorts topic (요구: 새 작업 시 필수)"
    )
    run_parser.add_argument("--resume", type=str, default="", help="재개할 Job ID")
    run_parser.add_argument("--config", type=str, default="config.yaml", help="Path to YAML config")
    run_parser.add_argument("--out", type=str, default="", help="Output mp4 filename")
    run_parser.add_argument("--channel", type=str, default="", help="채널명 (DB 설정 자동 로드)")
    run_parser.add_argument("--tts-voice", type=str, default="", help="TTS 보이스 오버라이드")
    run_parser.add_argument(
        "--style-preset", type=str, default="", help="자막 스타일 오버라이드 (default/bold/neon/subtitle/cta)"
    )
    run_parser.add_argument("--font-color", type=str, default="", help="자막 폰트 색상 오버라이드 (hex)")
    run_parser.add_argument("--image-prefix", type=str, default="", help="이미지 스타일 접두어 오버라이드")
    run_parser.add_argument(
        "--renderer",
        type=str,
        default="",
        choices=["native", "auto", "shorts_factory"],
        help="렌더러 선택 오버라이드",
    )
    run_parser.add_argument("--parallel", action="store_true", help="씬별 미디어 병렬 생성")

    batch_parser = subparsers.add_parser("batch", help="Batch-generate multiple shorts videos")
    batch_group = batch_parser.add_mutually_exclusive_group(required=True)
    batch_group.add_argument("--topics-file", type=str, help="토픽 텍스트 파일 경로 (줄당 1개)")
    batch_group.add_argument("--from-db", action="store_true", help="content_db에서 pending 주제 선택")
    batch_parser.add_argument("--limit", type=int, default=5, help="최대 처리 수 (기본: 5)")
    batch_parser.add_argument("--channel", type=str, default="", help="채널 필터 (--from-db 전용)")
    batch_parser.add_argument("--config", type=str, default="config.yaml", help="Path to YAML config")
    batch_parser.add_argument(
        "--renderer",
        type=str,
        default="",
        choices=["native", "auto", "shorts_factory"],
        help="렌더러 선택 오버라이드",
    )
    batch_parser.add_argument("--parallel", action="store_true", help="씬별 미디어 병렬 생성")
    batch_parser.add_argument("--no-continue-on-error", action="store_true", help="실패 시 중단")

    doctor_parser = subparsers.add_parser("doctor", help="Validate environment and configuration")
    doctor_parser.add_argument("--config", type=str, default="config.yaml", help="Path to YAML config")

    costs_parser = subparsers.add_parser("costs", help="Show cost summary (daily/monthly/total)")
    costs_parser.add_argument("--config", type=str, default="config.yaml", help="Path to YAML config")

    dashboard_parser = subparsers.add_parser("dashboard", help="Generate HTML statistics dashboard")
    dashboard_parser.add_argument("--config", type=str, default="config.yaml", help="Path to YAML config")
    dashboard_parser.add_argument("--out", type=str, default="dashboard.html", help="Path to output HTML file")
    return parser


def _load_channel_settings(channel: str) -> dict:
    """content_db에서 채널 설정 로드. DB 없으면 빈 dict 반환."""
    try:
        import sys as _sys
        from pathlib import Path as _Path

        _root = _Path(__file__).resolve().parent.parent.parent.parent.parent
        if str(_root) not in _sys.path:
            _sys.path.insert(0, str(_root))
        from execution.content_db import get_channel_settings, init_db  # type: ignore[import]

        init_db()
        return get_channel_settings(channel) or {}
    except Exception:
        return {}


def _import_content_db():
    """content_db 모듈 동적 로드. 실패 시 None 반환."""
    try:
        import sys as _sys
        from pathlib import Path as _Path

        _root = _Path(__file__).resolve().parent.parent.parent.parent.parent
        if str(_root) not in _sys.path:
            _sys.path.insert(0, str(_root))
        from execution import content_db  # type: ignore[import]

        content_db.init_db()
        return content_db
    except Exception:
        return None


def _apply_channel_overrides(config: AppConfig, args: argparse.Namespace) -> AppConfig:
    """채널 프로파일 + DB 설정 + CLI 플래그로 AppConfig 오버라이드. 우선순위: CLI > profile > DB > 기본값."""
    channel = getattr(args, "channel", "")
    db_settings: dict = _load_channel_settings(channel) if channel else {}

    # 1. channel_profiles.yaml 기반 프로파일 적용 (채널 키가 프로파일에 있으면)
    try:
        if channel:
            router = get_router()
            config = router.apply(config, channel)
            profile_context = router.get_channel_context(channel)
            if profile_context:
                # 채널 컨텍스트를 config에 임시 저장 (persona_pipeline에서 꺼내 사용)
                object.__setattr__(config, "_channel_context", profile_context)
            # 채널 키를 config에 저장 (orchestrator에서 프로필 자동 로딩용)
            object.__setattr__(config, "_channel_key", channel)
    except Exception:
        pass  # 프로파일 미존재 시 무시 (기존 동작 유지)

    # 2. CLI 플래그 오버라이드 (CLI가 항상 최우선)
    tts_voice = getattr(args, "tts_voice", "") or db_settings.get("voice", "")
    style_preset = getattr(args, "style_preset", "") or db_settings.get("style_preset", "")
    font_color = getattr(args, "font_color", "") or db_settings.get("font_color", "")
    image_prefix = getattr(args, "image_prefix", "") or db_settings.get("image_style_prefix", "")
    renderer = getattr(args, "renderer", "") or config.rendering.engine

    providers = config.providers
    captions = config.captions
    intro_outro = config.intro_outro

    if tts_voice:
        providers = replace(providers, tts_voice=tts_voice)
    if image_prefix:
        providers = replace(providers, image_style_prefix=image_prefix)
    if font_color:
        captions = replace(captions, text_color=font_color)

    # 3. 브랜드 에셋 자동 생성 + intro_outro 경로 설정
    if channel:
        config_base = Path(args.config).resolve().parent
        brand_dir = config_base / "assets" / "channels" / channel
        intro_p = brand_dir / "intro.png"
        brand_dir / "outro.png"
        if not intro_p.exists():
            try:
                from execution.brand_asset_generator import generate_channel_brand  # type: ignore[import]

                generate_channel_brand(channel, output_dir=brand_dir)
                print(f"[OK] 브랜드 에셋 생성: {brand_dir}")
            except Exception as exc:
                print(f"[WARN] 브랜드 에셋 생성 실패 (무시): {exc}")
        # 인트로/아웃트로 자동 삽입 비활성화 — 첫 화면 제거
        # if intro_p.exists():
        #     intro_outro = replace(intro_outro, intro_path=str(intro_p), outro_path=str(outro_p))

    new_config = replace(
        config,
        providers=providers,
        captions=captions,
        intro_outro=intro_outro,
        rendering=replace(config.rendering, engine=renderer),
    )

    # style_preset은 RenderStep.__init__에서 적용되므로 captions에 반영
    if style_preset:
        new_config = replace(new_config, captions=replace(new_config.captions, style_preset=style_preset))

    return new_config


# ── 배치 모드 ────────────────────────────────────────────────────────────────


def _pick_from_db(channel: str, limit: int) -> list[dict]:
    """content_db에서 채널별 pending 주제 선택."""
    db = _import_content_db()
    if db is None:
        print("[WARN] content_db 로드 실패 — --from-db 사용 불가")
        return []
    channels = [channel] if channel else db.get_channels()
    selected: list[dict] = []
    for ch in channels:
        items = db.get_all(channel=ch)
        pending = [i for i in items if i["status"] == "pending"]
        pending.reverse()  # 오래된 순
        selected.extend(pending[:limit])
    return selected[:limit]


def _make_batch_namespace(base_args: argparse.Namespace, channel: str) -> argparse.Namespace:
    """배치 실행용 최소 Namespace 생성 (_apply_channel_overrides 호환)."""
    return argparse.Namespace(
        config=getattr(base_args, "config", "config.yaml"),
        channel=channel,
        tts_voice="",
        style_preset="",
        font_color="",
        image_prefix="",
        renderer=getattr(base_args, "renderer", ""),
    )


def _print_batch_summary(results: list[BatchResult]) -> None:
    success = sum(1 for r in results if r.status == "success")
    skipped = sum(1 for r in results if r.status == "topic_unsuitable")
    failed = len(results) - success - skipped
    total_cost = sum(r.cost_usd for r in results)
    total_dur = sum(r.duration_sec for r in results)
    print(f"\n{'=' * 50}")
    print(f"배치 완료: 성공 {success} / 주제스킵 {skipped} / 실패 {failed} / 총 {len(results)}건")
    print(f"총 비용: ${total_cost:.3f} | 총 길이: {total_dur:.1f}s")
    print(f"{'=' * 50}")


def _run_batch(args: argparse.Namespace, config_path: Path) -> int:
    """배치 모드: 여러 주제를 순차 처리."""
    continue_on_error = not getattr(args, "no_continue_on_error", False)
    parallel = getattr(args, "parallel", False)

    # 1. 주제 로드: (topic, channel, db_item_id | None)
    topics: list[tuple[str, str, int | None]] = []

    if getattr(args, "topics_file", None):
        file_path = Path(args.topics_file).resolve()
        if not file_path.exists():
            print(f"[FAIL] topics file not found: {file_path}")
            return 1
        lines = file_path.read_text(encoding="utf-8").strip().splitlines()
        for line in lines[: args.limit]:
            stripped = line.strip()
            if stripped and not stripped.startswith("#"):
                topics.append((stripped, args.channel, None))

    elif getattr(args, "from_db", False):
        pending = _pick_from_db(channel=args.channel, limit=args.limit)
        topics = [(item["topic"], item.get("channel", ""), item["id"]) for item in pending]

    if not topics:
        print("[INFO] 처리할 주제가 없습니다.")
        return 0

    # 2. Config 로드
    try:
        config = load_config(config_path)
    except ConfigError as exc:
        print(f"[FAIL] config: {exc}")
        return 1

    missing_keys = validate_environment(config)
    if missing_keys:
        print(f"[FAIL] missing required env keys: {', '.join(missing_keys)}")
        return 1

    db = _import_content_db()

    # 3. 순차 실행
    print(f"[BATCH] {len(topics)}건 처리 시작 (parallel={'on' if parallel else 'off'})")
    results: list[BatchResult] = []

    for i, (topic, channel, db_id) in enumerate(topics, 1):
        print(f"\n--- [{i}/{len(topics)}] {f'[{channel}] ' if channel else ''}{topic} ---")

        if db_id is not None and db is not None:
            db.update_job(db_id, status="running")

        try:
            ns = _make_batch_namespace(args, channel)
            job_config = _apply_channel_overrides(config, ns)
            orchestrator = PipelineOrchestrator(
                config=job_config,
                base_dir=config_path.parent,
                renderer_mode=job_config.rendering.engine,
            )
            manifest = orchestrator.run(topic=topic, channel=channel, parallel=parallel)

            result = BatchResult(
                topic=topic,
                channel=channel,
                status=manifest.status,
                job_id=manifest.job_id,
                cost_usd=manifest.estimated_cost_usd,
                duration_sec=manifest.total_duration_sec,
            )
            if manifest.status != "success":
                result = BatchResult(
                    topic=topic,
                    channel=channel,
                    status=manifest.status,
                    job_id=manifest.job_id,
                    cost_usd=manifest.estimated_cost_usd,
                    duration_sec=manifest.total_duration_sec,
                    error="; ".join(f["message"] for f in manifest.failed_steps),
                )

            if db_id is not None and db is not None:
                db.update_job(
                    db_id,
                    status=manifest.status,
                    job_id=manifest.job_id,
                    title=manifest.title,
                    video_path=manifest.output_path,
                    thumbnail_path=manifest.thumbnail_path,
                    cost_usd=manifest.estimated_cost_usd,
                    duration_sec=manifest.total_duration_sec,
                )
        except Exception as exc:
            result = BatchResult(
                topic=topic,
                channel=channel,
                status="failed",
                job_id="",
                cost_usd=0,
                duration_sec=0,
                error=str(exc),
            )
            if db_id is not None and db is not None:
                db.update_job(db_id, status="failed", notes=str(exc)[:500])

            if not continue_on_error:
                results.append(result)
                print(f"  -> 실패 (중단): {result.error[:100]}")
                break

        results.append(result)
        if result.status == "success":
            print(f"  -> 성공 | 비용: ${result.cost_usd:.3f} | 길이: {result.duration_sec:.1f}s")
        elif result.status == "topic_unsuitable":
            print(f"  -> 주제 부적합 (스킵) | {result.error[:100]}")
        else:
            print(f"  -> 실패 | {result.error[:100]}")

    _print_batch_summary(results)
    return 0 if all(r.status in ("success", "topic_unsuitable") for r in results) else 1


def _doctor(config_path: Path) -> int:
    try:
        config = load_config(config_path)
    except ConfigError as exc:
        print(f"[FAIL] config: {exc}")
        return 1

    print(f"[OK] config loaded: {config_path}")
    errors: list[str] = []
    warnings: list[str] = []

    missing_keys = validate_environment(config)
    if missing_keys:
        errors.append(f"Missing environment keys: {', '.join(missing_keys)}")
    else:
        print(f"[OK] env keys: {', '.join(required_env_keys(config))}")

    ffmpeg_bin = shutil.which("ffmpeg")
    if ffmpeg_bin:
        print(f"[OK] ffmpeg found: {ffmpeg_bin}")
    else:
        warnings.append("ffmpeg not found in PATH. MoviePy rendering may fail.")

    base_dir = config_path.resolve().parent
    for relative in [config.paths.output_dir, config.paths.logs_dir, config.paths.runs_dir]:
        target = (base_dir / relative).resolve()
        try:
            target.mkdir(parents=True, exist_ok=True)
            print(f"[OK] writable dir: {target}")
        except Exception as exc:
            errors.append(f"Cannot create directory {target}: {exc}")

    for warning in warnings:
        print(f"[WARN] {warning}")
    for error in errors:
        print(f"[FAIL] {error}")
    if errors:
        return 1
    print("[OK] doctor passed")
    return 0


def _ensure_utf8_stdio() -> None:
    """Windows cp949 콘솔 인코딩 문제 방지 — 모든 진입점에서 호출."""
    import io

    for stream_name in ("stdout", "stderr"):
        stream = getattr(sys, stream_name, None)
        if stream and hasattr(stream, "encoding") and stream.encoding:
            if stream.encoding.lower() not in ("utf-8", "utf_8"):
                wrapped = io.TextIOWrapper(stream.buffer, encoding="utf-8", errors="replace")
                setattr(sys, stream_name, wrapped)


def run_cli(argv: list[str] | None = None) -> int:
    _ensure_utf8_stdio()
    load_dotenv()
    parser = _build_parser()
    args = parser.parse_args(argv)
    config_path = Path(args.config).resolve()

    if args.command == "doctor":
        return _doctor(config_path)

    if args.command == "batch":
        return _run_batch(args, config_path)

    if args.command == "dashboard":
        try:
            config = load_config(config_path)
        except ConfigError:
            logs_dir = config_path.parent / "logs"
        else:
            logs_dir = (config_path.parent / config.paths.logs_dir).resolve()

        from shorts_maker_v2.utils.dashboard import generate_dashboard

        out_html = config_path.parent / args.out
        generate_dashboard(logs_dir=logs_dir, output_file=out_html)
        print(f"[OK] Dashboard generated at {out_html}")
        return 0

    if args.command == "costs":
        try:
            config = load_config(config_path)
        except ConfigError:
            # config 없어도 기본 logs 경로로 시도
            logs_dir = config_path.parent / "logs"
        else:
            logs_dir = (config_path.parent / config.paths.logs_dir).resolve()
        tracker = CostTracker(logs_dir=logs_dir)
        tracker.print_summary()
        return 0

    if args.command == "run":
        if not args.topic and not args.resume:
            print("[FAIL] --topic is required unless --resume is specified")
            return 1

        try:
            config = load_config(config_path)
        except ConfigError as exc:
            print(f"[FAIL] config: {exc}")
            return 1

        missing_keys = validate_environment(config)
        if missing_keys:
            print(f"[FAIL] missing required env keys: {', '.join(missing_keys)}")
            return 1

        config = _apply_channel_overrides(config, args)
        parallel = getattr(args, "parallel", False)
        orchestrator = PipelineOrchestrator(
            config=config,
            base_dir=config_path.parent,
            renderer_mode=config.rendering.engine,
        )
        manifest = orchestrator.run(
            topic=args.topic,
            output_filename=args.out or None,
            channel=getattr(args, "channel", ""),
            parallel=parallel,
            resume_job_id=getattr(args, "resume", ""),
        )

        if manifest.status == "success":
            print(f"[OK] generated video: {manifest.output_path}")
            print(f"[OK] estimated cost: ${manifest.estimated_cost_usd:.3f}")
            return 0

        print("[FAIL] generation failed")
        for failed in manifest.failed_steps:
            step = failed.get("step", "unknown")
            code = failed.get("code") or failed.get("error_type", "unknown")
            message = failed.get("message", "")
            print(f" - {step}: {code} - {message}")
        return 1

    print("[FAIL] unknown command")
    return 1


if __name__ == "__main__":
    raise SystemExit(run_cli(sys.argv[1:]))
