import os

try:
    from pypdf import PdfReader
except ImportError:
    PdfReader = None

def load_pdf(file_path):
    """
    Loads text from a PDF file using pypdf.
    """
    if PdfReader is None:
        print("pypdf is not installed. Skipping PDF ingestion.")
        return ""

    try:
        reader = PdfReader(file_path)
        text = ""
        for page in reader.pages:
            text += page.extract_text() + "\n"
        return text
    except Exception as e:
        print(f"Error reading PDF {file_path}: {e}")
        return ""

def load_text(file_path):
    """
    Loads text from a .txt file.
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        print(f"Error reading text {file_path}: {e}")
        return ""

def simple_chunker(text, chunk_size=1000, overlap=200):
    """
    Splits text into chunks with overlap.
    """
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]
        chunks.append(chunk)
        start += (chunk_size - overlap)
    return chunks

def ingest_documents_custom(source_dir):
    """
    Ingests documents using custom loader and chunker.
    Returns a list of strings (chunks).
    """
    all_chunks = []
    
    if not os.path.exists(source_dir):
        print(f"Directory not found: {source_dir}")
        return []

    print(f"Scanning {source_dir}...")
    
    for filename in os.listdir(source_dir):
        file_path = os.path.join(source_dir, filename)
        
        text = ""
        if filename.endswith(".pdf"):
            print(f"Loading PDF: {filename}")
            text = load_pdf(file_path)
        elif filename.endswith(".txt"):
            print(f"Loading Text: {filename}")
            text = load_text(file_path)
            
        if text:
            chunks = simple_chunker(text)
            print(f" -> {len(chunks)} chunks")
            all_chunks.extend(chunks)
            
    return all_chunks

if __name__ == "__main__":
    # Test
    ingest_documents_custom("projects/personal-agent/data")
