"""
index_faiss.py — Genera embeddings desde chunks.json y los guarda en FAISS.
Usa sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2 como modelo de embeddings.
"""

import json
from pathlib import Path

import faiss
import numpy as np
from sentence_transformers import SentenceTransformer

BASE_DIR = Path(__file__).resolve().parents[1]
CHUNK_FILE = BASE_DIR / "data" / "clean" / "chunks.json"
FAISS_DIR = BASE_DIR / "data" / "vector_store"
INDEX_FILE = FAISS_DIR / "index.faiss"
METADATA_FILE = FAISS_DIR / "metadata.json"

EMBEDDING_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
MODEL_MAX_SEQ_LENGTH = 128
BATCH_SIZE = 16


def load_chunks() -> list[dict]:
    if not CHUNK_FILE.exists():
        raise FileNotFoundError(f"No existe el archivo: {CHUNK_FILE}")

    with open(CHUNK_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, list):
        raise ValueError("chunks.json debe contener una lista de chunks.")

    return data


def batch_iterable(items: list[dict], batch_size: int):
    for i in range(0, len(items), batch_size):
        yield items[i:i + batch_size]


def validate_chunks(chunks: list[dict]):
    required_fields = [
        "id", "doc_id", "chunk_index", "total_chunks_in_section",
        "title", "section", "source", "type", "topic", "stability",
        "review_date", "chunk_length_chars", "chunk_length_tokens",
        "chunk", "embedding_text",
    ]
    for idx, item in enumerate(chunks, start=1):
        missing = [f for f in required_fields if f not in item]
        if missing:
            raise KeyError(f"Chunk #{idx} (id={item.get('id')}) faltan campos: {missing}")
        if not isinstance(item["embedding_text"], str) or not item["embedding_text"].strip():
            raise ValueError(f"Chunk #{idx} tiene embedding_text vacío o inválido.")


def main():
    chunks = load_chunks()
    if not chunks:
        print("No hay chunks para indexar.")
        return

    validate_chunks(chunks)

    FAISS_DIR.mkdir(parents=True, exist_ok=True)

    print(f"Cargando modelo de embeddings: {EMBEDDING_MODEL}")
    model = SentenceTransformer(EMBEDDING_MODEL)
    model.max_seq_length = MODEL_MAX_SEQ_LENGTH
    print(f"max_seq_length configurado en: {model.max_seq_length}")

    print(f"Generando embeddings para {len(chunks)} chunks...")
    all_embeddings = []
    all_metadata = []

    for batch in batch_iterable(chunks, BATCH_SIZE):
        texts_for_embedding = [item["embedding_text"] for item in batch]

        embeddings = model.encode(
            texts_for_embedding,
            batch_size=BATCH_SIZE,
            normalize_embeddings=True,
            convert_to_numpy=True,
            show_progress_bar=False,
        ).astype(np.float32)

        all_embeddings.append(embeddings)

        for item in batch:
            all_metadata.append({
                "id": item["id"],
                "doc_id": item["doc_id"],
                "chunk_index": item["chunk_index"],
                "total_chunks_in_section": item["total_chunks_in_section"],
                "title": item["title"],
                "section": item["section"],
                "source": item["source"],
                "type": item["type"],
                "topic": item["topic"],
                "stability": item["stability"],
                "review_date": item["review_date"],
                "chunk_length_chars": item["chunk_length_chars"],
                "chunk_length_tokens": item["chunk_length_tokens"],
                "chunk": item["chunk"],
                "embedding_text": item["embedding_text"],
            })

        print(f"Procesados {len(all_metadata)}/{len(chunks)} chunks")

    vectors = np.vstack(all_embeddings).astype(np.float32)
    dimension = vectors.shape[1]

    index = faiss.IndexFlatIP(dimension)
    index.add(vectors)

    faiss.write_index(index, str(INDEX_FILE))

    with open(METADATA_FILE, "w", encoding="utf-8") as f:
        json.dump(all_metadata, f, ensure_ascii=False, indent=2)

    print("\nIndexación completada.")
    print(f"Total de chunks indexados: {index.ntotal}")
    print(f"Dimensión de embeddings: {dimension}")
    print(f"Índice guardado en: {INDEX_FILE}")
    print(f"Metadatos guardados en: {METADATA_FILE}")


if __name__ == "__main__":
    main()