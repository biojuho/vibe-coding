import json
import os
import datetime

MEMO_FILE = "data/memos.json"

def _load_memos():
    if not os.path.exists(MEMO_FILE):
        return []
    try:
        with open(MEMO_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading memos: {e}")
        return []

def _save_memos(memos):
    os.makedirs(os.path.dirname(MEMO_FILE), exist_ok=True)
    try:
        with open(MEMO_FILE, "w", encoding="utf-8") as f:
            json.dump(memos, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Error saving memos: {e}")

def add_memo(content):
    memos = _load_memos()
    new_memo = {
        "id": len(memos) + 1,
        "content": content,
        "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    memos.append(new_memo)
    _save_memos(memos)
    return f"✅ Memo saved: '{content}'"

def list_memos():
    memos = _load_memos()
    if not memos:
        return "📭 No memos found."
    
    result = "📝 **Your Memos:**\n"
    for memo in memos:
        result += f"- [{memo['timestamp']}] {memo['content']}\n"
    return result

def clear_memos():
    _save_memos([])
    return "🗑️ All memos cleared."
