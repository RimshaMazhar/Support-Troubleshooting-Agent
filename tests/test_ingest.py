from app.ingest import chunk_text, load_all_documents


def test_chunk_text_basic():
    text = " ".join(f"word{i}" for i in range(500))
    chunks = chunk_text(text, chunk_size=150, overlap=30)
    assert len(chunks) > 1


def test_load_all_documents_returns_tagged_chunks():
    chunks = load_all_documents(".")
    assert len(chunks) > 0
    for c in chunks[:5]:
        assert "text" in c
        assert "source_file" in c
        assert c["source_file"].endswith(".pdf")