"""
chunk.py — Genera un chunk por sección semántica del documento.
Cada chunk lleva metadatos completos para facilitar el retrieval.
"""
import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
CLEAN_FILE = BASE_DIR / "data" / "clean" / "biblioteca_clean.json"
CHUNK_FILE = BASE_DIR / "data" / "clean" / "chunks.json"

MAX_CHUNK = 700


def split_long_content(content: str, max_len: int = MAX_CHUNK) -> list[str]:
    if len(content) <= max_len:
        return [content]
    parts = []
    while len(content) > max_len:
        cut = content[:max_len].rfind(". ")
        cut = cut if cut > 100 else max_len
        parts.append(content[:cut + 1].strip())
        content = content[cut + 1:].strip()
    if content:
        parts.append(content)
    return parts


def main():
    with open(CLEAN_FILE, "r", encoding="utf-8") as f:
        docs = json.load(f)

    chunks = []
    for doc in docs:
        for i, section in enumerate(doc.get("sections", []), start=1):
            parts = split_long_content(section["content"])
            for j, part in enumerate(parts, start=1):
                chunk_id = f"{doc['topic']}_{i:03}_{j:02}"
                chunks.append({
                    "id": chunk_id,
                    "title": doc["title"],
                    "section": section["heading"],
                    "source": doc["url"],
                    "type": doc["type"],
                    "topic": doc["topic"],
                    "stability": doc["stability"],
                    "review_date": doc["review_date"],
                    "chunk": part,
                })

    with open(CHUNK_FILE, "w", encoding="utf-8") as f:
        json.dump(chunks, f, ensure_ascii=False, indent=2)

    print(f"Guardado en: {CHUNK_FILE}")
    print(f"Total chunks: {len(chunks)}")


if __name__ == "__main__":
    main()
