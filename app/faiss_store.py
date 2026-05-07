"""
faiss_store.py — Carga el índice FAISS y devuelve resultados con metadata.
"""

import json
from pathlib import Path
from typing import Any

import faiss
import numpy as np
from sentence_transformers import SentenceTransformer

BASE_DIR = Path(__file__).resolve().parents[1]
INDEX_FILE = BASE_DIR / "data" / "vector_store" / "index.faiss"
METADATA_FILE = BASE_DIR / "data" / "vector_store" / "metadata.json"
EMBEDDING_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"

_embedder = None
_index = None
_metadata = None


def get_embedder() -> SentenceTransformer:
    global _embedder
    if _embedder is None:
        _embedder = SentenceTransformer(EMBEDDING_MODEL)
    return _embedder


def load_store():
    global _index, _metadata

    if _index is not None and _metadata is not None:
        return _index, _metadata

    if not INDEX_FILE.exists():
        return None, []

    if not METADATA_FILE.exists():
        return None, []

    _index = faiss.read_index(str(INDEX_FILE))
    with open(METADATA_FILE, "r", encoding="utf-8") as f:
        _metadata = json.load(f)

    return _index, _metadata


def search(question: str, top_k: int = 5, topic: str | None = None) -> list[dict[str, Any]]:
    index, metadata = load_store()
    if index is None or not metadata:
        return []

    embedder = get_embedder()
    query_vector = embedder.encode(
        [question],
        normalize_embeddings=True,
        show_progress_bar=False
    )
    query_vector = np.asarray(query_vector, dtype=np.float32)

    distances, indices = index.search(query_vector, top_k)

    results = []
    for idx, score in zip(indices[0], distances[0]):
        if idx < 0 or idx >= len(metadata):
            continue

        item = metadata[idx].copy()
        item["score"] = float(score)

        if topic and item.get("topic") == topic:
            item["score"] += 0.15

        results.append(item)

    results.sort(key=lambda x: x["score"], reverse=True)
    return results


def get_stats() -> dict[str, Any]:
    _, metadata = load_store()
    topics = {}
    sources = set()

    for item in metadata:
        t = item.get("topic", "otro")
        topics[t] = topics.get(t, 0) + 1
        src = item.get("source")
        if src:
            sources.add(src)

    return {
        "total_chunks": len(metadata),
        "topics": topics,
        "sources": list(sources),
    }