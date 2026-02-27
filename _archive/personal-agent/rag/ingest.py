import os
from langchain_community.document_loaders import PyPDFLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter

def ingest_documents(source_dir):
    """
    Loads PDF and Text files from a directory and splits them into chunks.
    """
    documents = []
    
    if not os.path.exists(source_dir):
        os.makedirs(source_dir)
        print(f"Created directory: {source_dir}")
        return []

    print(f"Scanning {source_dir}...")
    
    for filename in os.listdir(source_dir):
        file_path = os.path.join(source_dir, filename)
        
        try:
            if filename.endswith(".pdf"):
                print(f"Loading PDF: {filename}")
                loader = PyPDFLoader(file_path)
                documents.extend(loader.load())
                
            elif filename.endswith(".txt"):
                print(f"Loading Text: {filename}")
                loader = TextLoader(file_path, encoding='utf-8')
                documents.extend(loader.load())
                
        except Exception as e:
            print(f"Error loading {filename}: {e}")

    if not documents:
        print("No documents found.")
        return []

    # Split text into chunks
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200,
        length_function=len,
    )
    
    chunks = text_splitter.split_documents(documents)
    print(f"Split into {len(chunks)} chunks.")
    
    return chunks

if __name__ == "__main__":
    # Test
    ingest_documents("data")
