import sys
import os
import io

# Force UTF-8 output
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Add project root to path
sys.path.append(os.path.join(os.path.dirname(__file__), "projects", "personal-agent"))

from tools.desktop_control import launch_app
from utils.tts import text_to_speech

if __name__ == "__main__":
    print("🛡️ Testing Desktop & TTS Robustness...")

    # Test 1: Launch non-existent app
    print("\n[TEST] Launching invalid app 'fakeapp'...")
    success, msg = launch_app("fakeapp")
    if not success:
        print(f"✅ Correctly handled invalid app: {msg}")
    else:
        print(f"❌ Unexpected success: {msg}")

    # Test 2: Launch valid app (Calculator)
    print("\n[TEST] Launching 'calculator'...")
    success, msg = launch_app("calculator")
    if success:
        print(f"✅ Successfully launched calculator: {msg}")
    else:
        print(f"❌ Failed to launch calculator: {msg}")

    # Test 3: TTS (Basic sanity check)
    print("\n[TEST] Generating TTS...")
    path = text_to_speech("시스템 안정성 테스트 중입니다.", output_dir="test_audio")
    if path and os.path.exists(path):
        print(f"✅ TTS generation successful: {path}")
    else:
        print("❌ TTS generation failed (could be network or other issue).")

    print("\n" + "="*30)
    print("Robustness Check Complete")
    print("="*30)
