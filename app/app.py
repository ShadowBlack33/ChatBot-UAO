"""
app.py — Backend Flask RAG CRAI UAO v2
Usa FAISS para retrieval semántico.
"""
import os
from datetime import datetime

import secrets
from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request, session
from groq import Groq

from app.faiss_store import get_stats, search

load_dotenv()

app = Flask(__name__)
app.secret_key = secrets.token_hex(32)

groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))

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


def detect_topic(question: str) -> str | None:
    q = question.lower()
    for topic, keywords in TOPIC_KEYWORDS.items():
        if any(kw in q for kw in keywords):
            return topic
    return None


def build_highlights(matches: list) -> list:
    highlights = []
    seen = set()
    for m in matches:
        text = m.get("chunk", "").strip()
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
        key = m.get("source")
        if key not in seen:
            seen.add(key)
            sources.append({
                "title": m.get("title", ""),
                "url": m.get("source", ""),
                "topic": m.get("topic", ""),
                "stability": m.get("stability", ""),
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

    contexto = "\n\n".join([f"[{h['section']}]: {h['text']}" for h in highlights])

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

    messages = [{"role": "system", "content": system_prompt}]
    messages.extend(build_history_messages(history))
    messages.append({
        "role": "user",
        "content": f"Contexto recuperado del CRAI:\n{contexto}\n\nPregunta: {question}"
    })

    response = groq_client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=messages,
        temperature=0.2,
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

    topic = detect_topic(question)
    matches = search(question, top_k=5, topic=topic)

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
        "topic": topic,
        "chunks_used": len(matches),
        "retrieval_info": f"Se usaron {len(matches)} fragmentos del CRAI como contexto.",
    })


@app.route("/reset", methods=["POST"])
def reset():
    session["history"] = []
    return jsonify({"status": "ok", "message": "Conversacion reiniciada."})


@app.route("/stats")
def stats():
    data = get_stats()
    return jsonify(data)


if __name__ == "__main__":
    app.run(debug=True)