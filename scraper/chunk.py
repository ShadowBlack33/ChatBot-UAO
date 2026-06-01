"""
chunk.py — Genera chunks por tokens reales usando el tokenizer de
sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2.
Cada chunk conserva metadatos y añade un campo embedding_text para FAISS.
"""

import json
import re
from pathlib import Path
from transformers import AutoTokenizer

BASE_DIR = Path(__file__).resolve().parents[1]
CLEAN_FILE = BASE_DIR / "data" / "clean" / "biblioteca_clean.json"
CHUNK_FILE = BASE_DIR / "data" / "clean" / "chunks.json"

MODEL_NAME = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
MAX_TOKENS = 100
OVERLAP_TOKENS = 15
MIN_CHUNK_CHARS = 80

tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)


def normalize_text(text: str) -> str:
    text = re.sub(r"\s+", " ", text or "")
    return text.strip()


def trim_to_tokens(text: str, max_tokens: int = 120) -> str:
    token_ids = tokenizer.encode(text, add_special_tokens=False)
    if len(token_ids) <= max_tokens:
        return text
    return tokenizer.decode(token_ids[:max_tokens], skip_special_tokens=True).strip()


def split_text_by_tokens(
    text: str,
    max_tokens: int = MAX_TOKENS,
    overlap: int = OVERLAP_TOKENS,
) -> list[str]:
    text = normalize_text(text)
    if not text:
        return []

    token_ids = tokenizer.encode(text, add_special_tokens=False)

    if len(token_ids) <= max_tokens:
        return [text]

    chunks = []
    start = 0
    step = max_tokens - overlap

    while start < len(token_ids):
        end = min(start + max_tokens, len(token_ids))
        chunk_token_ids = token_ids[start:end]
        chunk_text = tokenizer.decode(chunk_token_ids, skip_special_tokens=True).strip()

        if len(chunk_text) >= MIN_CHUNK_CHARS:
            chunks.append(chunk_text)

        if end >= len(token_ids):
            break

        start += step

    return chunks


def build_embedding_text(title: str, section: str, chunk: str) -> str:
    text = f"Título: {title}. Sección: {section}. Contenido: {chunk}"
    return trim_to_tokens(text, max_tokens=120)


def main():
    if not CLEAN_FILE.exists():
        raise FileNotFoundError(f"No existe el archivo: {CLEAN_FILE}")

    with open(CLEAN_FILE, "r", encoding="utf-8") as f:
        docs = json.load(f)

    all_chunks = []

    for doc_idx, doc in enumerate(docs, start=1):
        title = normalize_text(doc.get("title", "Sin título"))
        source = doc.get("url", "")
        doc_type = doc.get("type", "desconocido")
        topic = doc.get("topic", "general")
        stability = doc.get("stability", "media")
        review_date = doc.get("review_date", "")

        for sec_idx, section in enumerate(doc.get("sections", []), start=1):
            heading = normalize_text(section.get("heading", "General"))
            content = normalize_text(section.get("content", ""))

            if not content:
                continue

            parts = split_text_by_tokens(content)
            total_parts = len(parts)

            for part_idx, part in enumerate(parts, start=1):
                chunk_id = f"{topic}_{doc_idx:03}_{sec_idx:03}_{part_idx:02}"

                chunk_record = {
                    "id": chunk_id,
                    "doc_id": f"doc_{doc_idx:03}",
                    "chunk_index": part_idx,
                    "total_chunks_in_section": total_parts,
                    "title": title,
                    "section": heading,
                    "source": source,
                    "type": doc_type,
                    "topic": topic,
                    "stability": stability,
                    "review_date": review_date,
                    "chunk_length_chars": len(part),
                    "chunk_length_tokens": len(
                        tokenizer.encode(part, add_special_tokens=False)
                    ),
                    "chunk": part,
                    "embedding_text": build_embedding_text(title, heading, part),
                }

                all_chunks.append(chunk_record)

    with open(CHUNK_FILE, "w", encoding="utf-8") as f:
        json.dump(all_chunks, f, ensure_ascii=False, indent=2)

    print(f"Guardado en: {CHUNK_FILE}")
    print(f"Total chunks: {len(all_chunks)}")


if __name__ == "__main__":
    main()