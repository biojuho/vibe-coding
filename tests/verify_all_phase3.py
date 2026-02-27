import os
import sys
import time

# Force UTF-8 for Windows
sys.stdout.reconfigure(encoding='utf-8')

def check(name, result):
    if result:
        print(f"[{name}] PASS")
    else:
        print(f"[{name}] FAIL")

print("🔎 Starting Final System Verification (QA: Jieun)...")
print("-" * 50)

# 1. Personal Agent: Scheduler
try:
    sys.path.append(os.path.join(os.getcwd(), 'projects/personal-agent'))
    from utils.scheduler import scheduler
    check("Scheduler Module Import", True)
    check("Scheduler Singleton", scheduler is not None)
except Exception as e:
    print(f"Scheduler Error: {e}")
    check("Scheduler", False)

# 2. Personal Agent: Search
try:
    from tools.search import search_web
    # Dry run search (don't spam API, just check import and function existence)
    check("Search Tool Import", callable(search_web))
except Exception as e:
    print(f"Search Error: {e}")
    check("Search Tool", False)

# 3. Word Chain: Assets
wc_path = "projects/word-chain-pygame"
assets = ["click.wav", "correct.wav", "wrong.wav"]
missing = []
for a in assets:
    if not os.path.exists(os.path.join(wc_path, "assets", a)):
        missing.append(a)
check("Word Chain Assets", len(missing) == 0)
if missing: print(f"Missing: {missing}")

# 4. Joolife Hub
try:
    import streamlit
    check("Streamlit Library", True)
    if os.path.exists("joolife_hub.py"):
        check("Hub Script Exists", True)
    else:
        check("Hub Script Exists", False)
except ImportError:
    check("Streamlit Library", False)

print("-" * 50)
print("✅ Verification Complete.")
