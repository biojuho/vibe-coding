import os
import sys

# Force UTF-8 for Windows
sys.stdout.reconfigure(encoding="utf-8")


def check_file_content(path, distinct_string):
    try:
        if not os.path.exists(path):
            print(f"[FAIL] File not found: {path}")
            return False
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        if distinct_string in content:
            print(f"[PASS] Found '{distinct_string}' in {os.path.basename(path)}")
            return True
        else:
            print(f"[FAIL] Missing '{distinct_string}' in {os.path.basename(path)}")
            return False
    except Exception as e:
        print(f"[ERROR] {e}")
        return False


print("🔎 Starting UX/UI v2.0 Verification (QA: Jieun)...")
print("-" * 50)

# 1. Joolife Hub (Glassmorphism)
check_file_content("execution/joolife_hub.py", "backdrop-filter: blur(10px);")

# 2. Personal Agent (JooPark & Bubbles)
check_file_content("projects/personal-agent/config.py", 'USER_NAME = "Joolife President JooPark"')
check_file_content("projects/personal-agent/ui/styles.py", ".bubble-bot-happy {")

# 3. Word Chain (Mascot)
check_file_content("projects/word-chain-pygame/ui.py", "class Mascot:")
check_file_content("projects/word-chain-pygame/game.py", "self.mascot.draw(self.screen")

print("-" * 50)
print("✅ Verification Complete.")
