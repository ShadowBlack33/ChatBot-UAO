import json
import time
import pandas as pd
from app.faiss_store import search

TOP_K = 5

test_questions = [
    {
        "question": "¿Qué es el CRAI?",
        "expected_keywords": ["centro", "recursos", "uao"],
        "expected_topic": "informacion_general",
    },
    {
        "question": "¿Cuál es el horario del CRAI?",
        "expected_keywords": ["lunes", "viernes", "sábado", "horario"],
        "expected_topic": "reservas_y_horarios",
    },
    {
        "question": "¿Dónde queda el CRAI?",
        "expected_keywords": ["ubicación", "segundo piso", "crai"],
        "expected_topic": "informacion_general",
    },
    {
        "question": "¿Qué servicios ofrece el CRAI?",
        "expected_keywords": ["servicios", "préstamo", "recursos"],
        "expected_topic": "servicios",
    },
    {
        "question": "¿Cómo reservar una sala?",
        "expected_keywords": ["reservar", "sala", "capacitación"],
        "expected_topic": "reservas_y_horarios",
    },
    {
        "question": "¿Qué recursos digitales hay disponibles?",
        "expected_keywords": ["recursos", "digitales", "bases"],
        "expected_topic": "recursos_digitales",
    },
    {
        "question": "¿Cuál es el reglamento de préstamos?",
        "expected_keywords": ["préstamo", "reglamento", "usuario"],
        "expected_topic": "reglamento",
    },
    {
        "question": "¿Qué espacios físicos tiene el CRAI?",
        "expected_keywords": ["sala", "espacios", "capacitación"],
        "expected_topic": "servicios",
    },
    {
        "question": "¿Puedo ingresar al CRAI si soy visitante externo?",
        "expected_keywords": ["visitantes", "comunidad", "usuario"],
        "expected_topic": "informacion_general",
    },
    {
        "question": "¿Qué pasa si pierdo un libro prestado?",
        "expected_keywords": ["préstamo", "reglamento", "usuario"],
        "expected_topic": "reglamento",
    },
    {
        "question": "¿El CRAI tiene bases de datos académicas?",
        "expected_keywords": ["bases", "datos", "recursos"],
        "expected_topic": "recursos_digitales",
    },
    {
        "question": "¿Hay salas para capacitación?",
        "expected_keywords": ["sala", "capacitación", "segundo piso"],
        "expected_topic": "servicios",
    },
    {
        "question": "¿Qué derechos tengo como usuario del CRAI?",
        "expected_keywords": ["derechos", "usuario", "reglamento"],
        "expected_topic": "reglamento",
    },
    {
        "question": "¿Qué deberes tengo como usuario?",
        "expected_keywords": ["deberes", "usuario", "reglamento"],
        "expected_topic": "reglamento",
    },
    {
        "question": "¿Puedo consultar recursos electrónicos desde casa?",
        "expected_keywords": ["recursos", "electrónicos", "digitales"],
        "expected_topic": "recursos_digitales",
    },
    {
        "question": "¿Qué es el préstamo interbibliotecario?",
        "expected_keywords": ["préstamo", "interbibliotecario", "bibliotecas"],
        "expected_topic": "servicios",
    },
    {
        "question": "¿El CRAI ofrece servicios para docentes?",
        "expected_keywords": ["docentes", "servicios", "capacitación"],
        "expected_topic": "servicios",
    },
    {
        "question": "¿El CRAI apoya procesos de investigación?",
        "expected_keywords": ["investigación", "recursos", "asesoría"],
        "expected_topic": "busqueda_academica",
    },
    {
        "question": "¿Cuántos parqueaderos tiene el CRAI?",
        "expected_keywords": ["parqueadero"],
        "expected_topic": "informacion_general",
    },
    {
        "question": "¿Dónde queda exactamente la entrada principal del CRAI?",
        "expected_keywords": ["entrada", "ubicación", "crai"],
        "expected_topic": "informacion_general",
    },
]


def is_relevant(result, expected_keywords, expected_topic=None):
    text = " ".join([
        str(result.get("title", "")),
        str(result.get("section", "")),
        str(result.get("chunk", "")),
        str(result.get("source", "")),
        str(result.get("topic", ""))
    ]).lower()

    keyword_match = any(keyword.lower() in text for keyword in expected_keywords)
    topic_match = expected_topic is None or result.get("topic") == expected_topic
    return keyword_match or topic_match


rows = []
total_hit = 0
total_precision = 0
total_recall = 0
total_mrr = 0
total_latency = 0

for item in test_questions:
    question = item["question"]
    expected_keywords = item["expected_keywords"]
    expected_topic = item.get("expected_topic")

    start = time.time()
    results = search(question, top_k=TOP_K)
    latency = time.time() - start

    relevant_positions = []
    retrieved_topics = []

    for i, result in enumerate(results, start=1):
        retrieved_topics.append(result.get("topic", ""))
        if is_relevant(result, expected_keywords, expected_topic):
            relevant_positions.append(i)

    hit = 1 if relevant_positions else 0
    precision = len(relevant_positions) / TOP_K
    mrr = 1 / relevant_positions[0] if relevant_positions else 0

    expected_relevant_estimate = max(1, min(TOP_K, len(expected_keywords)))
    recall = min(1.0, len(relevant_positions) / expected_relevant_estimate)

    total_hit += hit
    total_precision += precision
    total_recall += recall
    total_mrr += mrr
    total_latency += latency

    rows.append({
        "pregunta": question,
        "tema_esperado": expected_topic,
        "chunks_recuperados": len(results),
        "posiciones_relevantes": relevant_positions,
        "hit@5": hit,
        "precision@5": round(precision, 2),
        "recall@5": round(recall, 2),
        "mrr": round(mrr, 2),
        "latencia_segundos": round(latency, 3),
        "topicos_recuperados": ", ".join(sorted(set(retrieved_topics))),
        "fuentes": ", ".join(sorted(set(str(r.get("source", "")) for r in results))),
    })

n = len(test_questions)

summary = {
    "hit@5_promedio": round(total_hit / n, 2),
    "precision@5_promedio": round(total_precision / n, 2),
    "recall@5_promedio": round(total_recall / n, 2),
    "mrr_promedio": round(total_mrr / n, 2),
    "latencia_promedio_segundos": round(total_latency / n, 3),
}

df = pd.DataFrame(rows)

print("\n==============================")
print("RESULTADOS POR PREGUNTA")
print("==============================\n")
print(df.to_string(index=False))

print("\n==============================")
print("RESUMEN GENERAL")
print("==============================\n")
for key, value in summary.items():
    print(f"{key}: {value}")

print("\n==============================")
print("ANÁLISIS AUTOMÁTICO")
print("==============================\n")

if summary["hit@5_promedio"] >= 0.9:
    print("• El sistema recupera información relevante en la mayoría de las consultas.")
else:
    print("• El sistema presenta dificultades recuperando información relevante.")

if summary["precision@5_promedio"] >= 0.8:
    print("• La precisión del retrieval es alta y los chunks recuperados son mayormente útiles.")
else:
    print("• Algunos chunks recuperados contienen ruido semántico.")

if summary["mrr_promedio"] >= 0.8:
    print("• El primer resultado suele ser relevante para el usuario.")
else:
    print("• La respuesta correcta no siempre aparece en las primeras posiciones.")

if summary["latencia_promedio_segundos"] <= 1:
    print("• El sistema responde en tiempo casi real.")
else:
    print("• La latencia puede afectar la experiencia del usuario.")

print("\n==============================")
print("ERRORES DETECTADOS")
print("==============================\n")

for row in rows:
    if row["precision@5"] < 1.0:
        print(f"• Pregunta con ruido semántico detectado: {row['pregunta']}")

df.to_csv("resultados_evaluacion.csv", index=False, encoding="utf-8-sig")

with open("evaluation_results.json", "w", encoding="utf-8") as f:
    json.dump({"summary": summary, "results": rows}, f, ensure_ascii=False, indent=2)

print("\nArchivos generados:")
print("resultados_evaluacion.csv")
print("evaluation_results.json")