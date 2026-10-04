from __future__ import annotations

import json
import os
import platform
import sys
from datetime import datetime, timezone
from pathlib import Path

from thesis_rag.settings import settings


from importlib import metadata


def _pkg_version(name: str) -> str | None:
    try:
        return metadata.version(name)
    except metadata.PackageNotFoundError:
        return None
    except Exception:
        return None


def collect_reproducibility() -> dict:
    index_manifest = {}
    manifest_path = settings.resolved_index_dir() / "manifest.json"
    if manifest_path.exists():
        index_manifest = json.loads(
            manifest_path.read_text(encoding="utf-8")
        )

    return {
        "captured_at_utc": datetime.now(timezone.utc).isoformat(),
        "python": sys.version,
        "platform": {
            "system": platform.system(),
            "release": platform.release(),
            "machine": platform.machine(),
            "processor": platform.processor(),
        },
        "packages": {
            "langchain": _pkg_version("langchain"),
            "langchain_core": _pkg_version("langchain-core"),
            "langchain_community": _pkg_version("langchain-community"),
            "langchain_ollama": _pkg_version("langchain-ollama"),
            "langgraph": _pkg_version("langgraph"),
            "faiss": _pkg_version("faiss-cpu") or _pkg_version("faiss"),
            "rank_bm25": _pkg_version("rank-bm25"),
            "psycopg2": _pkg_version("psycopg2-binary") or _pkg_version("psycopg2"),
        },
        "models": {
            "rag_llm": settings.rag_llm,
            "router_llm": settings.router_llm,
            "embed_model": settings.embed_model,
            "ollama_base_url": settings.ollama_base_url,
            "cloud_llm": os.getenv("CLOUD_LLM"),
            "local_llm": os.getenv("LOCAL_LLM"),
        },
        "generation": {
            "temperature": settings.llm_temperature,
            "num_predict": settings.llm_num_predict,
            "num_ctx": settings.llm_num_ctx,
            "seed": settings.llm_seed,
        },
        "retrieval": {
            "chunk_size": settings.chunk_size,
            "chunk_overlap": settings.chunk_overlap,
            "vector_top_k": settings.vector_top_k,
            "bm25_top_k": settings.bm25_top_k,
            "final_top_k": settings.final_top_k,
            "dense_weight": settings.dense_weight,
            "sparse_weight": settings.sparse_weight,
            "fusion_method": settings.fusion_method,
            "rrf_k": settings.rrf_k,
            "bm25_k1": settings.bm25_k1,
            "bm25_b": settings.bm25_b,
            "faiss_index": "IndexFlatL2",
            "faiss_metric": settings.faiss_metric,
        },
        "index_manifest": index_manifest,
        "database": {
            "engine": "PostgreSQL",
            "host": os.getenv("DB_HOST"),
            "name": os.getenv("DB_NAME"),
            "data_nature": "synthetic_prototype",
        },
        "notes": [
            "Mevcut 100 soruluk küme geliştirme/pilot setidir; final sonuçlar held-out set üzerinden raporlanmalıdır.",
            "Çiftlik verisi ticari işletme verisi değil, prototip amaçlı sentetik kayıtlardır.",
            "FAISS ve BM25 skorları farklı ölçekte olduğu için birleştirme Weighted Reciprocal Rank Fusion ile yapılır.",
        ],
    }


def write_reproducibility(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = collect_reproducibility()
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return path
