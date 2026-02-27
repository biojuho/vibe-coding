from tools.search import search_web
import sys

# Force UTF-8
sys.stdout.reconfigure(encoding='utf-8')

print("Testing Search Tool...")
try:
    res = search_web("OpenAI Sora release date")
    if res:
        print("SUCCESS! Results found:")
        print(res[:200])
    else:
        print("FAILURE: No results returned.")
except Exception as e:
    print(f"ERROR: {e}")
