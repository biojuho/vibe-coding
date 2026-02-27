import warnings
import sys

# Suppress Pydantic V1 compatibility warning
warnings.filterwarnings("ignore", category=UserWarning, module="langchain_core")

try:
    from langchain_core.documents import Document
    from langchain_text_splitters import RecursiveCharacterTextSplitter

    print("Testing LangChain components with warning suppression...")

    doc = Document(page_content="This is a test document. " * 100)
    print("Document created.")
    
    splitter = RecursiveCharacterTextSplitter(chunk_size=100)
    chunks = splitter.split_documents([doc])
    print(f"Split into {len(chunks)} chunks.")
    
    print("Success!")
except ImportError as e:
    print(f"Import Error: {e}")
except Exception as e:
    print(f"Error: {e}")
