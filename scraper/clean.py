"""
clean.py — Normaliza texto y elimina secciones ruidosas del raw JSON.
"""
import json
import re
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
RAW_FILE = BASE_DIR / "data" / "raw" / "biblioteca_raw.json"
CLEAN_FILE = BASE_DIR / "data" / "clean" / "biblioteca_clean.json"

MIN_SECTION_LENGTH = 40

SKIP_HEADINGS = {
    "últimas noticias", "próximos eventos", "convenios bibliotecarios",
    "compartir", "redes sociales", "inicio", "general",
    "menú principal", "navegación", "footer",
}


def normalize(text: str) -> str:
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"(http\S+)", "", text)
    return text.strip()


def filter_section(section: dict) -> bool:
    heading = section.get("heading", "").strip().lower()
    content = section.get("content", "").strip()
    if heading in SKIP_HEADINGS:
        return False
    if len(content) < MIN_SECTION_LENGTH:
        return False
    if re.search(r"\d{1,2} - (enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|octubre|noviembre|diciembre) - \d{4}", content, re.IGNORECASE):
        return False
    return True


def main():
    CLEAN_FILE.parent.mkdir(parents=True, exist_ok=True)

    with open(RAW_FILE, "r", encoding="utf-8") as f:
        docs = json.load(f)

    clean_docs = []
    for doc in docs:
        clean_sections = []
        for section in doc.get("sections", []):
            if not filter_section(section):
                continue
            clean_sections.append({
                "heading": normalize(section["heading"]),
                "content": normalize(section["content"]),
            })

        clean_docs.append({
            "title": doc.get("title"),
            "url": doc.get("url"),
            "type": doc.get("type"),
            "topic": doc.get("topic"),
            "stability": doc.get("stability"),
            "review_date": doc.get("review_date"),
            "sections": clean_sections,
        })

    with open(CLEAN_FILE, "w", encoding="utf-8") as f:
        json.dump(clean_docs, f, ensure_ascii=False, indent=2)

    total = sum(len(d["sections"]) for d in clean_docs)
    print(f"Guardado en: {CLEAN_FILE}")
    print(f"Total secciones limpias: {total}")


if __name__ == "__main__":
    main()
