"""
Builds an in-memory Chroma vector store from the chunked documents and
exposes a simple semantic search function over it.
"""

import chromadb
from sentence_transformers import SentenceTransformer

from app.ingest import load_all_documents

_embed_model = None
_collection = None


def get_store(base_path: str = "."):
    """Lazily build the vector store once, then reuse it."""
    global _embed_model, _collection

    if _collection is not None:
        return _embed_model, _collection

    print("Loading documents and building vector store...")
    chunks = load_all_documents(base_path)

    _embed_model = SentenceTransformer("all-MiniLM-L6-v2")
    chroma_client = chromadb.Client()
    _collection = chroma_client.create_collection(name="support_docs")

    texts = [c["text"] for c in chunks]
    embeddings = _embed_model.encode(texts).tolist()
    ids = [f"chunk_{i}" for i in range(len(chunks))]
    metadatas = [{"source_type": c["source_type"], "source_file": c["source_file"]} for c in chunks]

    _collection.add(embeddings=embeddings, documents=texts, ids=ids, metadatas=metadatas)
    print(f"Vector store ready with {len(chunks)} chunks.")
    return _embed_model, _collection


def document_lookup(question: str, n_results: int = 4) -> str:
    """Semantic search over the docs, returns the top matching chunks with
    their source file so the answer can be grounded and traceable."""
    embed_model, collection = get_store()
    query_embedding = embed_model.encode([question]).tolist()
    results = collection.query(query_embeddings=query_embedding, n_results=n_results)

    docs = results["documents"][0]
    metas = results["metadatas"][0]

    parts = []
    for doc, meta in zip(docs, metas):
        parts.append(f"[source: {meta['source_file']}]\n{doc}")
    return "\n---\n".join(parts)


if __name__ == "__main__":
    print(document_lookup("what does error code ORD-500 mean"))