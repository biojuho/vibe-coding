"""Generate BGM files with Google Lyria realtime music streaming.

Usage:
    python workspace/execution/lyria_bgm_generator.py --prompt "minimal techno"
    python workspace/execution/lyria_bgm_generator.py --prompt "warm ambient piano" --duration 20 --format mp3
"""

from __future__ import annotations

import argparse
import asyncio
import re
import sys
from pathlib import Path

from dotenv import load_dotenv

WORKSPACE_ROOT = Path(__file__).resolve().parents[1]
if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT))

from path_contract import REPO_ROOT, resolve_project_dir

_SHORTS_DIR = resolve_project_dir("shorts-maker-v2", required_paths=("src",))
_SHORTS_SRC = _SHORTS_DIR / "src"
_DEFAULT_BGM_DIR = _SHORTS_DIR / "assets" / "bgm"

if str(_SHORTS_SRC) not in sys.path:
    sys.path.insert(0, str(_SHORTS_SRC))


def _slugify(text: str, *, fallback: str = "lyria-bgm") -> str:
    normalized = re.sub(r"[^\w\s-]+", "", text.casefold(), flags=re.UNICODE)
    slug = re.sub(r"[-\s]+", "-", normalized, flags=re.UNICODE).strip("-_")
    return slug[:48] or fallback


def _build_output_path(prompt: str, output_dir: Path, file_format: str) -> Path:
    stem = _slugify(prompt)
    return output_dir / f"{stem}.{file_format}"


async def _run(args: argparse.Namespace) -> Path:
    from shorts_maker_v2.providers.google_music_client import GoogleMusicClient

    client = GoogleMusicClient.from_env(request_timeout_sec=args.timeout)
    output_dir = Path(args.output_dir).resolve()
    output_path = (
        Path(args.output).resolve() if args.output else _build_output_path(args.prompt, output_dir, args.format)
    )
    return await client.generate_music_file(
        prompt=args.prompt,
        output_path=output_path,
        duration_sec=args.duration,
        bpm=args.bpm,
        temperature=args.temperature,
    )


def main() -> int:
    load_dotenv(REPO_ROOT / ".env")
    load_dotenv(_SHORTS_DIR / ".env", override=False)

    parser = argparse.ArgumentParser(description="Generate a reusable BGM file with Google Lyria.")
    parser.add_argument("--prompt", required=True, help="Music prompt, for example: minimal techno")
    parser.add_argument("--duration", type=float, default=30.0, help="Target music duration in seconds")
    parser.add_argument("--bpm", type=int, default=90, help="Target BPM")
    parser.add_argument("--temperature", type=float, default=1.0, help="Generation temperature")
    parser.add_argument("--format", choices=["wav", "mp3"], default="wav", help="Output audio format")
    parser.add_argument("--output-dir", default=str(_DEFAULT_BGM_DIR), help="Destination directory")
    parser.add_argument("--output", default="", help="Full output path. Overrides --output-dir and --format")
    parser.add_argument("--timeout", type=int, default=180, help="Overall request timeout in seconds")
    args = parser.parse_args()

    try:
        result = asyncio.run(_run(args))
    except Exception as exc:
        print(f"[FAIL] Lyria generation failed: {exc}")
        return 1

    print(f"[OK] BGM generated: {result}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
