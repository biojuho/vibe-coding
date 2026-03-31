from __future__ import annotations

import argparse
import io
import os
import sys
import time
from typing import Callable, Optional

# Force UTF-8 output
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

# Add project roots to path
ROOT = os.path.dirname(__file__)
sys.path.append(os.path.join(ROOT, "projects", "personal-agent"))
sys.path.append(os.path.join(ROOT, "projects", "word-chain-pygame"))


def run_test(name: str, func: Callable[[], Optional[object]]) -> bool:
    print(f"\n[TEST] {name}...")
    try:
        start = time.time()
        result = func()
        duration = time.time() - start
        print(f"✅ PASS ({duration:.2f}s)")
        if result is not None:
            snippet = str(result)
            if len(snippet) > 80:
                snippet = snippet[:80] + "..."
            print(f"   -> {snippet}")
        return True
    except Exception as e:
        print(f"❌ FAIL: {e}")
        return False


def test_system_monitor():
    from tools.system_monitor import get_system_report

    return get_system_report()


def test_rag_query():
    from rag.query import query_rag

    return query_rag("What is this project?")


def test_tts():
    from utils.tts import text_to_speech

    audio_path = text_to_speech("System check complete.", output_dir="test_audio")
    if audio_path and os.path.exists(audio_path):
        return f"Audio generated: {audio_path}"
    raise RuntimeError("TTS returned no file path.")


def test_word_chain_db():
    import data as word_chain_data

    gm = word_chain_data.GameManager("projects/word-chain-pygame/word_chain.db")
    return gm.get_word_starting_with("기")


def test_side_effect_intent():
    from rag.query import query_rag

    return query_rag("계산기 실행해줘")


def main() -> int:
    parser = argparse.ArgumentParser(description="Joolife system diagnostic")
    parser.add_argument(
        "--safe",
        action="store_true",
        help="Run only non-side-effect tests (default behavior).",
    )
    parser.add_argument(
        "--with-side-effects",
        action="store_true",
        help="Run tests that can open apps/windows.",
    )
    args = parser.parse_args()

    print("=" * 50)
    print("🤖 JARVIS SYSTEM DIAGNOSTIC")
    print("=" * 50)
    print(f"Mode: {'SIDE-EFFECTS ENABLED' if args.with_side_effects else 'SAFE'}")

    tests = [
        ("System Monitor", test_system_monitor),
        ("LLM & RAG", test_rag_query),
        ("Text-to-Speech", test_tts),
        ("Word Chain DB", test_word_chain_db),
    ]

    passed = 0
    failed = 0
    for name, fn in tests:
        ok = run_test(name, fn)
        if ok:
            passed += 1
        else:
            failed += 1

    print("\n[TEST] Intent Recognition Baseline...")
    print("   - SAFE mode does not execute desktop actions.")
    if args.with_side_effects:
        print("\n⚠️ WARNING: This will open desktop applications.")
        if run_test("Intent: Open Calculator", test_side_effect_intent):
            passed += 1
        else:
            failed += 1
    else:
        print("   - Skipped side-effect tests. Use --with-side-effects to enable.")

    print("\n" + "=" * 50)
    if failed == 0:
        print("🎉 DIAGNOSTIC COMPLETE (ALL PASS)")
    else:
        print(f"⚠️ DIAGNOSTIC COMPLETE ({failed} FAILED)")
    print("=" * 50)
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
