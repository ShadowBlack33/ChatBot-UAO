"""
scrape.py — Extrae contenido limpio por secciones desde las URLs del CRAI.
Cada sección (h1/h2/h3 + sus párrafos/listas) se guarda como bloque separado.
"""
import json
import re
from datetime import datetime
from pathlib import Path

import requests
from bs4 import BeautifulSoup

BASE_DIR = Path(__file__).resolve().parents[1]
URLS_FILE = BASE_DIR / "data" / "urls.json"
RAW_DIR   = BASE_DIR / "data" / "raw"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    )
}

NOISE_PATTERNS = [
    r"^(inicio|menú|saltar al contenido|compartir|facebook|twitter|instagram|whatsapp)$",
    r"^\s*$",
    r"^(©|todos los derechos|política de privacidad|términos)",
]

NAV_WORDS = {
    "inicio", "menú", "menu", "secciones", "más", "mas",
    "egresados", "préstamo interbibliotecario", "prestamo interbibliotecario",
    "circulación", "circulacion", "servicios culturales", "investigadores",
    "docentes", "ver más", "ver mas", "leer más", "leer mas",
}

SKIP_SELECTORS = [
    "script", "style", "noscript", "svg", "form", "iframe",
    "nav", "footer", "header",
    ".menu", ".navbar", ".breadcrumb", ".social", ".share",
    ".widget", ".sidebar", ".cookie", ".banner", ".ad",
    "#menu", "#footer", "#header", "#nav",
]


def is_noise(text: str) -> bool:
    t = text.strip().lower()
    if len(t) < 4:
        return True
    for pat in NOISE_PATTERNS:
        if re.search(pat, t, re.IGNORECASE):
            return True
    return False


def is_nav_content(content: str) -> bool:
    words = [w.strip() for w in re.split(r"[\n\s]{2,}|·|•|\|", content.lower()) if w.strip()]
    if not words:
        return False
    nav_hits = sum(1 for w in words if w in NAV_WORDS)
    return (nav_hits / len(words)) > 0.5


def clean_soup(soup: BeautifulSoup) -> BeautifulSoup:
    for sel in SKIP_SELECTORS:
        for tag in soup.select(sel):
            tag.decompose()
    return soup


def extract_sections(soup: BeautifulSoup) -> list[dict]:
    sections = []
    current_heading = "General"
    current_lines = []

    for tag in soup.find_all(["h1", "h2", "h3", "p", "li"]):
        text = tag.get_text(" ", strip=True)
        if not text or is_noise(text):
            continue
        if tag.name in ("h1", "h2", "h3"):
            if current_lines:
                sections.append({"heading": current_heading, "content": " ".join(current_lines)})
                current_lines = []
            current_heading = text
        else:
            if len(text) > 20:
                current_lines.append(text)

    if current_lines:
        sections.append({"heading": current_heading, "content": " ".join(current_lines)})

    sections = [s for s in sections if not is_nav_content(s["content"])]
    return sections


def deduplicate_sections(sections: list[dict]) -> list[dict]:
    seen = set()
    unique = []
    for s in sections:
        key = s["content"][:120]
        if key not in seen:
            seen.add(key)
            unique.append(s)
    return unique


def main():
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    with open(URLS_FILE, "r", encoding="utf-8") as f:
        urls = json.load(f)

    all_docs = []
    for item in urls:
        url = item["url"]
        try:
            r = requests.get(url, headers=HEADERS, timeout=25)
            r.raise_for_status()
            soup = BeautifulSoup(r.text, "html.parser")
            soup = clean_soup(soup)
            page_title = soup.title.get_text(strip=True) if soup.title else item["title"]
            sections = deduplicate_sections(extract_sections(soup))
            doc = {
                "title": item["title"],
                "page_title": page_title,
                "url": url,
                "type": item["type"],
                "topic": item["topic"],
                "stability": item["stability"],
                "review_date": datetime.now().strftime("%Y-%m-%d"),
                "sections": sections,
                "error": None,
            }
            print(f"  OK ({len(sections)} secciones) -> {item['title']}")
        except Exception as e:
            doc = {
                "title": item["title"],
                "url": url,
                "type": item["type"],
                "topic": item["topic"],
                "stability": item["stability"],
                "review_date": datetime.now().strftime("%Y-%m-%d"),
                "sections": [],
                "error": str(e),
            }
            print(f"  ERROR -> {item['title']}: {e}")
        all_docs.append(doc)

    out = RAW_DIR / "biblioteca_raw.json"
    with open(out, "w", encoding="utf-8") as f:
        json.dump(all_docs, f, ensure_ascii=False, indent=2)
    print(f"\nGuardado en: {out}")


if __name__ == "__main__":
    main()
