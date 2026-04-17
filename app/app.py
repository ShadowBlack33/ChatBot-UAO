"""
app.py — Backend Flask RAG CRAI UAO v2
Mejoras: historial multi-turn, respuesta estructurada, top-K dinámico,
sugerencias automáticas, endpoint de estadísticas.
"""
import json
import os
from pathlib import Path
from datetime import datetime

from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request, session
from groq import Groq
import secrets

load_dotenv()

BASE_DIR = Path(__file__).resolve().parents[1]
CHUNK_FILE = BASE_DIR / "data" / "clean" / "chunks.json"

app = Flask(__name__)
app.secret_key = secrets.token_hex(32)

groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))

STOPWORDS = {
    "qué", "que", "cuál", "cual", "cómo", "como", "dónde", "donde",
    "es", "son", "hay", "tiene", "tienen", "para", "por", "con",
    "de", "del", "la", "el", "los", "las", "un", "una", "en",
    "se", "al", "y", "o", "a", "me", "puedo", "puedes", "quiero",
    "saber", "decir", "dime", "favor", "porfavor", "hola", "buenas",
}

TOPIC_KEYWORDS = {
    "servicios": ["servicio", "servicios", "ofrece", "préstamo", "prestamo", "capacitación", "egresado", "docente", "cultural", "club", "lectura"],
    "reglamento": ["norma", "normas", "regla", "reglamento", "debo", "puede", "sancion", "derecho", "deber", "multa", "perder", "prohibido"],
    "reservas_y_horarios": ["reserv", "horario", "hora", "sala", "espacio", "disponible", "cuando", "abre", "cierra", "schedule"],
    "recursos_digitales": ["base", "datos", "digital", "revista", "articulo", "libro", "electronico", "web", "acceso", "online", "internet", "plataforma"],
    "busqueda_academica": ["buscar", "búsqueda", "busqueda", "encontrar", "catalogo", "filtro", "investigar", "paper", "tesis"],
    "informacion_general": ["crai", "biblioteca", "director", "contacto", "ubicacion", "telefono", "email", "donde", "queda", "direccion"],
}

SUGGESTED_QUESTIONS = [
    "¿Qué servicios ofrece el CRAI?",
    "¿Cuáles son mis derechos como usuario?",
    "¿Cómo reservo una sala de estudio?",
    "¿Qué recursos digitales hay disponibles?",
    "¿Cuál es el reglamento de préstamos?",
    "¿Qué espacios físicos tiene el CRAI?",
]

_chunks_cache = None


def load_chunks() -> list:
    global _chunks_cache
    if _chunks_cache is not None:
        return _chunks_cache
    if not CHUNK_FILE.exists():
        return []
    with open(CHUNK_FILE, "r", encoding="utf-8") as f:
        _chunks_cache = json.load(f)
    return _chunks_cache


def tokenize(text: str) -> set:
    return set(text.lower().split()) - STOPWORDS


def detect_topic(question: str) -> str | None:
    q = question.lower()
    for topic, keywords in TOPIC_KEYWORDS.items():
        if any(kw in q for kw in keywords):
            return topic
    return None


def search(question: str, chunks: list, top_k: int = 5) -> list:
    q_words = tokenize(question)
    if not q_words:
        return []

    topic = detect_topic(question)
    scored = []

    for chunk in chunks:
        text = chunk.get("chunk", "").lower()
        score = sum(1 for w in q_words if w in text)
        if score == 0:
            continue
        if topic and chunk.get("topic") == topic:
            score += 2
        if chunk.get("stability") == "alta":
            score += 1
        heading = chunk.get("section", "").lower()
        heading_hits = sum(1 for w in q_words if w in heading)
        score += heading_hits * 2
        scored.append((score, chunk))

    scored.sort(key=lambda x: x[0], reverse=True)

    high_conf = [s for s in scored if s[0] >= 4]
    k = min(top_k + 2, len(scored)) if len(high_conf) >= 3 else top_k
    return [item[1] for item in scored[:k]]


def build_highlights(matches: list) -> list:
    highlights = []
    seen = set()
    for m in matches:
        text = m["chunk"].strip()
        key = text[:150]
        if key in seen:
            continue
        seen.add(key)
        summary = text[:280] + ("..." if len(text) > 280 else "")
        highlights.append({
            "section": m.get("section", ""),
            "text": summary,
            "topic": m.get("topic", ""),
            "stability": m.get("stability", ""),
        })
    return highlights


def build_sources(matches: list) -> list:
    seen = set()
    sources = []
    for m in matches:
        key = m["source"]
        if key not in seen:
            seen.add(key)
            sources.append({
                "title": m["title"],
                "url": m["source"],
                "topic": m["topic"],
                "stability": m["stability"],
            })
    return sources


def build_history_messages(history: list) -> list:
    messages = []
    for turn in history[-6:]:
        messages.append({"role": "user", "content": turn["question"]})
        messages.append({"role": "assistant", "content": turn["answer"]})
    return messages


def generate_answer(question: str, highlights: list, history: list) -> str:
    if not highlights:
        return (
            "No encontré información suficiente en las fuentes del CRAI para responder esa pregunta. "
            "Te recomiendo consultar directamente en [uao.edu.co/biblioteca](https://www.uao.edu.co/biblioteca)."
        )

    contexto = "\n\n".join([
        f"[{h['section']}]: {h['text']}" for h in highlights
    ])

    
    system_prompt = """Eres un asistente virtual del CRAI (Centro de Recursos para el Aprendizaje y la Investigación) de la Universidad Autónoma de Occidente (UAO), en Cali, Colombia.

Tu función es ayudar a estudiantes, docentes y usuarios con información sobre servicios, recursos, reglamentos y espacios del CRAI.

Reglas estrictas:
1. Responde SIEMPRE en español, de forma clara, amable y directa.
2. Usa ÚNICAMENTE la información del contexto proporcionado. No inventes nada ni uses conocimiento externo.
3. Si la información no está en el contexto, responde EXACTAMENTE: "No encontré información sobre eso en las fuentes del CRAI. Intenta reformular tu pregunta o consulta directamente en uao.edu.co/biblioteca."
4. Estructura tu respuesta así:
   - Primero un párrafo breve de respuesta directa
   - Luego, si aplica, una lista con puntos clave usando bullet points (•)
   - Al final, si aplica, indica dónde consultar más información
5. Mantén coherencia con la conversación anterior si la hay.
6. Sé conciso: máximo 200 palabras.
7. NUNCA respondas con información que no esté explícitamente en el contexto dado."""

    history_messages = build_history_messages(history)

    messages = [{"role": "system", "content": system_prompt}]
    messages.extend(history_messages)
    messages.append({
        "role": "user",
        "content": f"Contexto recuperado del CRAI:\n{contexto}\n\nPregunta: {question}"
    })

    response = groq_client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=messages,
        temperature=0.2,   # ✅ MEJORA 2: bajamos de 0.3 a 0.2 para menos creatividad/alucinación
        max_tokens=600,
    )

    return response.choices[0].message.content.strip()


@app.route("/")
def home():
    if "history" not in session:
        session["history"] = []
    return render_template("index.html", suggestions=SUGGESTED_QUESTIONS)


@app.route("/ask", methods=["POST"])
def ask():
    data = request.get_json()
    question = (data or {}).get("question", "").strip()

    if not question:
        return jsonify({
            "status": "error",
            "answer": "Escribe una pregunta para continuar.",
            "highlights": [],
            "sources": []
        }), 400

    chunks = load_chunks()
    if not chunks:
        return jsonify({
            "status": "error",
            "answer": "La base de conocimiento no está disponible. Ejecuta scrape.py, clean.py y chunk.py.",
            "highlights": [],
            "sources": []
        }), 503

    matches = search(question, chunks)

    if not matches:
        return jsonify({
            "status": "not_found",
            "answer": "No encontré información sobre eso en las fuentes del CRAI. Intenta reformular tu pregunta o consulta directamente en uao.edu.co/biblioteca.",
            "highlights": [],
            "sources": [],
            "timestamp": datetime.now().strftime("%H:%M"),
        })

    highlights = build_highlights(matches)
    sources = build_sources(matches)
    history = session.get("history", [])
    answer = generate_answer(question, highlights, history)

    history.append({"question": question, "answer": answer})
    session["history"] = history[-10:]

    
    return jsonify({
        "status": "ok",
        "answer": answer,
        "highlights": highlights,
        "sources": sources,
        "timestamp": datetime.now().strftime("%H:%M"),
        "topic": detect_topic(question),
        "chunks_used": len(matches),
        "retrieval_info": f"Se usaron {len(matches)} fragmentos del CRAI como contexto.",
    })


@app.route("/reset", methods=["POST"])
def reset():
    session["history"] = []
    return jsonify({"status": "ok", "message": "Conversacion reiniciada."})


@app.route("/stats")
def stats():
    chunks = load_chunks()
    topics = {}
    for c in chunks:
        t = c.get("topic", "otro")
        topics[t] = topics.get(t, 0) + 1
    return jsonify({
        "total_chunks": len(chunks),
        "topics": topics,
        "sources": list({c["source"] for c in chunks}),
    })


if __name__ == "__main__":
    app.run(debug=True)