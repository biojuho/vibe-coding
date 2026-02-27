print("Testing LangChain components...")

try:
    from langchain_core.documents import Document
    from langchain_text_splitters import RecursiveCharacterTextSplitter

    doc = Document(page_content="This is a test document. " * 100)
    print("Document created.")
    
    splitter = RecursiveCharacterTextSplitter(chunk_size=100)
    chunks = splitter.split_documents([doc])
    print(f"Split into {len(chunks)} chunks.")
    
    print("Success!")
except Exception as e:
    print(f"Error: {e}")
