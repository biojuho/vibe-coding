from tools.search import search_web
from rag.query import query_rag

print("--- 1. Direct Tool Test ---")
q = "2024년 노벨 문학상 수상자"
print(f"Query: {q}")
res = search_web(q)
print(f"Result: {res[:100]}..." if res else "No result")

print("\n--- 2. Integrated RAG Test (Fallback) ---")
q2 = "비트코인 현재 가격"
print(f"Query: {q2}")
ans = query_rag(q2)
print(f"Answer: {ans}")
