from __future__ import annotations

from pathlib import Path
from typing import Iterable

from langchain_community.document_loaders import PyPDFLoader, TextLoader
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from .settings import settings

SUPPORTED_SUFFIXES = {".pdf", ".txt", ".md"}


def _load_file(path: Path) -> list[Document]:
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        docs = PyPDFLoader(str(path)).load()
    elif suffix in {".txt", ".md"}:
        docs = TextLoader(str(path), encoding="utf-8", autodetect_encoding=True).load()
    else:
        return []

    for doc in docs:
        doc.metadata["source"] = str(path)
        doc.metadata["source_name"] = path.name
        doc.metadata["source_stem"] = path.stem
        if "page" in doc.metadata:
            # PyPDFLoader 0-tabanlı sayfa numarası verir.
            doc.metadata["page_number"] = int(doc.metadata["page"]) + 1
    return docs


def load_documents(source_dir: Path | None = None) -> list[Document]:
    source_dir = source_dir or settings.resolved_knowledge_base_dir()
    if not source_dir.exists():
        raise FileNotFoundError(f"Bilgi tabanı klasörü bulunamadı: {source_dir}")

    files = sorted(
        path for path in source_dir.rglob("*")
        if path.is_file() and path.suffix.lower() in SUPPORTED_SUFFIXES
    )
    if not files:
        raise ValueError(
            f"{source_dir} altında PDF/TXT/MD dokümanı bulunamadı. "
            "Önce güvenilir hayvancılık kaynaklarını bu klasöre ekleyin."
        )

    docs: list[Document] = []
    for path in files:
        docs.extend(_load_file(path))
    return docs


def split_documents(documents: Iterable[Document]) -> list[Document]:
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=settings.chunk_size,
        chunk_overlap=settings.chunk_overlap,
        separators=["\n\n", "\n", ". ", " ", ""],
    )
    chunks = splitter.split_documents(list(documents))
    for i, chunk in enumerate(chunks):
        chunk.metadata["chunk_id"] = f"chunk-{i:06d}"
    return chunks
