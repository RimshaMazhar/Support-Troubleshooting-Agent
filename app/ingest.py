"""
Loads all PDF documents (product docs, runbooks, incident summaries) from the
data/ folder, splits them into overlapping word-chunks, and returns them
tagged with a source label so retrieval results can say where they came from.
"""

import glob
import os

from pypdf import PdfReader

DOC_FOLDERS = {
    "docs": "data/docs",
}


def extract_text_from_pdf(pdf_path: str) -> str:
    reader = PdfReader(pdf_path)
    text = ""
    for page in reader.pages:
        text += page.extract_text() + "\n"
    return text


def chunk_text(text: str, chunk_size: int = 150, overlap: int = 30):
    words = text.split()
    chunks = []
    start = 0
    while start < len(words):
        end = start + chunk_size
        chunks.append(" ".join(words[start:end]))
        start += chunk_size - overlap
    return chunks


def load_all_documents(base_path: str = "."):
    """Returns a list of dicts: {text, source_type, source_file}"""
    all_chunks = []
    for source_type, folder in DOC_FOLDERS.items():
        full_folder = os.path.join(base_path, folder)
        pdf_files = sorted(glob.glob(os.path.join(full_folder, "*.pdf")))
        for pdf_path in pdf_files:
            filename = os.path.basename(pdf_path)
            text = extract_text_from_pdf(pdf_path)
            chunks = chunk_text(text)
            for chunk in chunks:
                all_chunks.append({
                    "text": chunk,
                    "source_type": source_type,
                    "source_file": filename,
                })
    return all_chunks


if __name__ == "__main__":
    chunks = load_all_documents()
    print(f"Total chunks loaded: {len(chunks)}")
    by_type = {}
    for c in chunks:
        by_type[c["source_type"]] = by_type.get(c["source_type"], 0) + 1
    for k, v in by_type.items():
        print(f"  {k}: {v} chunks")
    print("\nSample chunk:")
    print(chunks[0])