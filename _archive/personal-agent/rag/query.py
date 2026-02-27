from __future__ import annotations

import logging
import os
from typing import Dict, Optional, Tuple

from tools.desktop_control import launch_app, open_website
from tools.launcher import launch_word_chain
from tools.memo_tool import add_memo, clear_memos, list_memos
from tools.search import search_web
from tools.system_monitor import get_system_report
from utils.llm import LLMClient

try:
    from rag.vector_db import get_vector_db
except Exception as vector_db_import_error:  # pragma: no cover - runtime fallback
    get_vector_db = None
else:
    vector_db_import_error = None


def detect_intent(user_query: str) -> Tuple[str, Dict[str, str]]:
    """Return (intent_name, metadata)."""
    keywords_game = ["게임", "끝말잇기"]
    keywords_action = ["시작", "켜줘", "할래", "실행", "해줘"]
    if any(kw in user_query for kw in keywords_game) and any(
        kw in user_query for kw in keywords_action
    ):
        return "launch_game", {}

    keywords_system = ["시스템", "컴퓨터", "CPU", "메모리", "사양"]
    keywords_status = ["상태", "진단", "체크", "확인", "어때"]
    if any(kw in user_query for kw in keywords_system) and any(
        kw in user_query for kw in keywords_status
    ):
        return "system_monitor", {}

    keywords_web = ["열어줘", "검색해줘", "가줘"]
    if any(kw in user_query for kw in keywords_web):
        if "유튜브" in user_query:
            return "open_website", {"target": "youtube.com", "label": "유튜브"}
        if "구글" in user_query:
            return "open_website", {"target": "google.com", "label": "구글"}
        if "화면" in user_query or "사이트" in user_query:
            return "website_ask", {}

    keywords_app = ["켜줘", "실행해줘"]
    if any(kw in user_query for kw in keywords_app):
        if "메모장" in user_query:
            return "launch_app", {"target": "notepad", "label": "메모장"}
        if "계산기" in user_query:
            return "launch_app", {"target": "calculator", "label": "계산기"}
        if "그림판" in user_query:
            return "launch_app", {"target": "paint", "label": "그림판"}

    keywords_memo = ["메모", "기록", "적어", "남겨"]
    if any(kw in user_query for kw in keywords_memo):
        if "읽어" in user_query or "보여줘" in user_query or "목록" in user_query:
            return "memo_list", {}
        if "삭제" in user_query or "지워" in user_query or "비워" in user_query:
            return "memo_clear", {}
        return "memo_add", {}

    if ("정리" in user_query or "청소" in user_query) and (
        "다운로드" in user_query or "폴더" in user_query
    ):
        return "organize_downloads", {}

    return "none", {}


def handle_intent(intent: str, user_query: str, metadata: Dict[str, str]) -> Optional[str]:
    if intent == "launch_game":
        logging.info("Intent Detected: Game Launch")
        print("[INFO] Game Launch Intent Detected")
        success, msg = launch_word_chain()
        if success:
            logging.info("Game launch successful")
            return "🎮 끝말잇기 게임을 실행했습니다! 새 창을 확인해주세요. (즐거운 시간 되세요!)"
        logging.error(f"Game launch failed: {msg}")
        return f"❌ 게임 실행에 실패했습니다: {msg}"

    if intent == "system_monitor":
        logging.info("Intent Detected: System Monitor")
        print("[INFO] System Monitor Intent Detected")
        report = get_system_report()
        logging.info("System report generated")
        return f"🖥️ 시스템 상태 보고:\n{report}"

    if intent == "open_website":
        logging.info("Intent Detected: Web Browse")
        ok, msg = open_website(metadata["target"])
        if ok:
            return f"📺 {metadata['label']}를 열었습니다." if metadata["label"] == "유튜브" else f"🔍 {metadata['label']}을 열었습니다."
        return f"⚠️ 사이트 열기에 실패했습니다: {msg}"

    if intent == "website_ask":
        return "🌐 어떤 사이트를 열까요? (유튜브, 구글 지원)"

    if intent == "launch_app":
        logging.info("Intent Detected: App Launch")
        ok, msg = launch_app(metadata["target"])
        if ok:
            return f"{'📝' if metadata['label'] == '메모장' else '🧮' if metadata['label'] == '계산기' else '🎨'} {metadata['label']}을 실행했습니다."
        return f"⚠️ {metadata['label']} 실행에 실패했습니다: {msg}"

    if intent == "memo_list":
        return list_memos()

    if intent == "memo_clear":
        return clear_memos()

    if intent == "memo_add":
        keywords_memo = ["메모", "기록", "적어", "남겨", "해줘", "해"]
        content = user_query
        for kw in keywords_memo:
            content = content.replace(kw, "")
        content = content.strip()
        if content:
            return add_memo(content)
        return "📝 무엇을 메모할까요? (예: '우유 사기 메모해줘')"

    if intent == "organize_downloads":
        logging.info("Intent Detected: Organize Downloads")
        try:
            from tools.file_manager import organize_directory

            downloads_path = os.path.join(os.path.expanduser("~"), "Downloads")
            result = organize_directory(downloads_path)
            return f"📂 **File Manager Report**\n\n{result}"
        except Exception as exc:  # pragma: no cover - defensive path
            logging.error(f"File Organization Failed: {exc}")
            return f"⚠️ File Organization Failed: {exc}"

    return None


def build_context(user_query: str, k: int = 3) -> Tuple[str, str]:
    results = []
    if get_vector_db is None:
        logging.warning(f"Vector DB unavailable: {vector_db_import_error}")
    else:
        try:
            db = get_vector_db()
            results = db.query(user_query, k=k)
        except Exception as exc:
            logging.warning(f"Vector DB query failed: {exc}")

    context_text = ""
    source_type = "Local Knowledge"
    if results:
        context_text = "\n\n".join(results)
        print(f"Retrieved {len(results)} chunks from Local DB.")

    should_search_web = (not results) or ("검색" in user_query) or ("찾아줘" in user_query)
    if should_search_web:
        print("[INFO] Local DB empty or Search requested. Trying Web Search...")
        web_results = search_web(user_query)
        if web_results:
            context_text += f"\n\n[Web Search Results]\n{web_results}"
            source_type = "Web Search" if not results else "Local + Web"
            print("[INFO] Found info on the Web.")
        else:
            print("[WARN] Web Search returned nothing.")

    if not context_text:
        return "", source_type
    return context_text, source_type


def construct_prompt(context: str, query: str, source_type: str) -> str:
    return f"""
You are an intelligent assistant. Answer the user's question based ONLY on the context provided below.

[Context ({source_type})]
{context}

[Question]
{query}

If the answer is not in the context, say "I don't know".
"""


def generate_answer(context_text: str, source_type: str, user_query: str) -> str:
    llm = LLMClient()
    if llm.provider == "mock":
        print("\n[WARNING] Using Mock LLM. Answer will be simulated.")
        return f"[MOCK Answer based on {source_type}]: Found relevant info. The document mentions {user_query}."

    answer = llm.generate_text(construct_prompt(context_text, user_query, source_type))
    if "I don't know" in answer and source_type == "Local Knowledge":
        print("[INFO] LLM said 'I don't know'. Trying Web Search...")
        web_results = search_web(user_query)
        if web_results:
            print("[INFO] Found info on the Web. Re-generating answer...")
            merged_context = context_text + f"\n\n[Web Search Results]\n{web_results}"
            answer = llm.generate_text(construct_prompt(merged_context, user_query, "Local + Web"))
    return answer


def query_rag(user_query: str, k: int = 3) -> str:
    """Retrieve context and return final answer."""
    logging.info(f"Query Received: {user_query}")
    print(f"User Query: {user_query}")

    intent, metadata = detect_intent(user_query)
    if intent != "none":
        intent_result = handle_intent(intent, user_query, metadata)
        if intent_result is not None:
            return intent_result

    context_text, source_type = build_context(user_query, k=k)
    if not context_text:
        return "I couldn't find any relevant information in your documents or on the web."
    return generate_answer(context_text, source_type, user_query)


if __name__ == "__main__":
    print(query_rag("끝말잇기 게임 켜줘"))
