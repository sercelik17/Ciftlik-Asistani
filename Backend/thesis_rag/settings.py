from dataclasses import dataclass
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class RAGSettings:
    base_dir: Path = Path(__file__).resolve().parents[1]
    knowledge_base_dir: Path = Path(os.getenv("RAG_KNOWLEDGE_BASE", "knowledge_base"))
    index_dir: Path = Path(os.getenv("RAG_INDEX_DIR", "rag_index"))
    embed_model: str = os.getenv("RAG_EMBED_MODEL", "bge-m3")
    rag_llm: str = os.getenv("RAG_LLM", os.getenv("LOCAL_LLM", "mistral"))
    router_llm: str = os.getenv("RAG_ROUTER_LLM", os.getenv("LOCAL_LLM", "mistral"))
    ollama_base_url: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    chunk_size: int = int(os.getenv("RAG_CHUNK_SIZE", "900"))
    chunk_overlap: int = int(os.getenv("RAG_CHUNK_OVERLAP", "150"))
    vector_top_k: int = int(os.getenv("RAG_VECTOR_TOP_K", "8"))
    bm25_top_k: int = int(os.getenv("RAG_BM25_TOP_K", "8"))
    final_top_k: int = int(os.getenv("RAG_FINAL_TOP_K", "5"))
    dense_weight: float = float(os.getenv("RAG_DENSE_WEIGHT", "0.60"))
    sparse_weight: float = float(os.getenv("RAG_SPARSE_WEIGHT", "0.40"))

    def resolved_knowledge_base_dir(self) -> Path:
        path = self.knowledge_base_dir
        return path if path.is_absolute() else self.base_dir / path

    def resolved_index_dir(self) -> Path:
        path = self.index_dir
        return path if path.is_absolute() else self.base_dir / path


settings = RAGSettings()
