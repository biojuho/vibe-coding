from rag.ingest_custom import ingest_documents_custom as ingest_documents
from rag.vector_db import add_documents_to_db
from rag.query import query_rag
from config import LLM_PROVIDER
import os

import sys
import io

# Force UTF-8 output for Windows
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

def run_test():
    print("="*60)
    print(f"🤖 RAG System Test (Provider: {LLM_PROVIDER.upper()})")

    print("="*60)

    data_dir = "projects/personal-agent/data"
    if not os.path.exists(data_dir):
        print(f"❌ Data directory not found: {data_dir}")
        return

    print(f"\n1. 📂 Ingesting Documents from '{data_dir}'...")
    chunks = ingest_documents(data_dir)
    
    if not chunks:
        print("⚠️ No documents found or empty directory.")
        return

    print(f"   ✅ Processed {len(chunks)} chunks.")

    print(f"\n2. 💾 Adding to Vector DB...")
    try:
        add_documents_to_db(chunks)
        print("   ✅ Vector DB updated successfully.")
    except Exception as e:
        print(f"   ❌ Failed to update Vector DB: {e}")
        return

    query = "What is Vibe Coding?"
    print(f"\n3. ❓ Querying: '{query}'")
    
    try:
        response = query_rag(query)
        print("\n" + "-"*60)
        print("💡 Response:")
        print("-" * 60)
        print(response)
        print("-" * 60)
    except Exception as e:
        print(f"   ❌ Error during query: {e}")

if __name__ == "__main__":
    run_test()
