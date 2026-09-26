from __future__ import annotations

import json
from pathlib import Path

from langchain_community.vectorstores import FAISS
from langchain_ollama import OllamaEmbeddings

from .documents import load_documents, split_documents
from .settings import settings


def _serialize_chunks(chunks, path: Path) -> None:
    payload = [
        {"page_content": d.page_content, "metadata": d.metadata}
        for d in chunks
    ]
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def build_index(source_dir: Path | None = None, index_dir: Path | None = None) -> dict:
    source_dir = source_dir or settings.resolved_knowledge_base_dir()
    index_dir = index_dir or settings.resolved_index_dir()
    index_dir.mkdir(parents=True, exist_ok=True)

    documents = load_documents(source_dir)
    chunks = split_documents(documents)

    embeddings = OllamaEmbeddings(
        model=settings.embed_model,
        base_url=settings.ollama_base_url,
    )
    vector_store = FAISS.from_documents(chunks, embeddings)
    vector_store.save_local(str(index_dir / "faiss"))
    _serialize_chunks(chunks, index_dir / "chunks.json")

    manifest = {
        "document_count": len(documents),
        "chunk_count": len(chunks),
        "embedding_model": settings.embed_model,
        "chunk_size": settings.chunk_size,
        "chunk_overlap": settings.chunk_overlap,
        "source_dir": str(source_dir),
    }
    (index_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return manifest
