import time
import pandas as pd
from app.faiss_store import search

TOP_K = 5

test_questions = [
    {
        "question": "¿Qué es el CRAI?",
        "expected_keywords": ["centro", "recursos", "UAO"]
    },
    {
        "question": "¿Cuál es el horario del CRAI?",
        "expected_keywords": ["lunes", "viernes", "sábado", "horario"]
    },
    {
        "question": "¿Dónde queda el CRAI?",
        "expected_keywords": ["ubicación", "segundo piso", "CRAI"]
    },
    {
        "question": "¿Qué servicios ofrece el CRAI?",
        "expected_keywords": ["servicios", "préstamo", "recursos"]
    },
    {
        "question": "¿Cómo reservar una sala?",
        "expected_keywords": ["reservar", "sala", "capacitación"]
    },
    {
        "question": "¿Qué recursos digitales hay disponibles?",
        "expected_keywords": ["recursos", "digitales", "bases"]
    },
    {
        "question": "¿Cuál es el reglamento de préstamos?",
        "expected_keywords": ["préstamo", "reglamento", "usuario"]
    },
    {
        "question": "¿Qué espacios físicos tiene el CRAI?",
        "expected_keywords": ["sala", "espacios", "capacitación"]
    },
    {
        "question": "¿Puedo ingresar al CRAI si soy visitante externo?",
        "expected_keywords": ["visitantes", "comunidad", "usuario"]
    },
    {
        "question": "¿Qué pasa si pierdo un libro prestado?",
        "expected_keywords": ["préstamo", "reglamento", "usuario"]
    },
    {
        "question": "¿El CRAI tiene bases de datos académicas?",
        "expected_keywords": ["bases", "datos", "recursos"]
    },
    {
        "question": "¿Hay salas para capacitación?",
        "expected_keywords": ["sala", "capacitación", "segundo piso"]
    },
    {
        "question": "¿Qué derechos tengo como usuario del CRAI?",
        "expected_keywords": ["derechos", "usuario", "reglamento"]
    },
    {
        "question": "¿Qué deberes tengo como usuario?",
        "expected_keywords": ["deberes", "usuario", "reglamento"]
    },
    {
        "question": "¿Puedo consultar recursos electrónicos desde casa?",
        "expected_keywords": ["recursos", "electrónicos", "digitales"]
    },
    {
        "question": "¿Qué es el préstamo interbibliotecario?",
        "expected_keywords": ["préstamo", "interbibliotecario", "bibliotecas"]
    },
    {
        "question": "¿El CRAI ofrece servicios para docentes?",
        "expected_keywords": ["docentes", "servicios", "capacitación"]
    },
    {
        "question": "¿El CRAI apoya procesos de investigación?",
        "expected_keywords": ["investigación", "recursos", "asesoría"]
    },
    {
        "question": "¿Cuántos parqueaderos tiene el CRAI?",
        "expected_keywords": ["parqueadero"]
    },
    {
        "question": "¿Dónde queda exactamente la entrada principal del CRAI?",
        "expected_keywords": ["entrada", "ubicación", "CRAI"]
    }
]


def is_relevant(result, expected_keywords):
    text = " ".join([
        str(result.get("title", "")),
        str(result.get("text", "")),
        str(result.get("content", "")),
        str(result.get("chunk", "")),
        str(result.get("source", "")),
        str(result.get("topic", ""))
    ]).lower()

    return any(keyword.lower() in text for keyword in expected_keywords)


rows = []

total_hit = 0
total_precision = 0
total_mrr = 0
total_latency = 0

for item in test_questions:
    question = item["question"]
    expected_keywords = item["expected_keywords"]

    start = time.time()
    results = search(question, top_k=TOP_K)
    latency = time.time() - start

    relevant_positions = []

    for i, result in enumerate(results, start=1):
        if is_relevant(result, expected_keywords):
            relevant_positions.append(i)

    hit = 1 if relevant_positions else 0
    precision = len(relevant_positions) / TOP_K
    mrr = 1 / relevant_positions[0] if relevant_positions else 0

    total_hit += hit
    total_precision += precision
    total_mrr += mrr
    total_latency += latency

    rows.append({
        "pregunta": question,
        "chunks_recuperados": len(results),
        "posiciones_relevantes": relevant_positions,
        "hit@5": hit,
        "precision@5": round(precision, 2),
        "mrr": round(mrr, 2),
        "latencia_segundos": round(latency, 2),
        "fuentes": ", ".join(set(str(r.get("source", "")) for r in results))
    })


n = len(test_questions)

summary = {
    "Hit@5 promedio": round(total_hit / n, 2),
    "Precision@5 promedio": round(total_precision / n, 2),
    "MRR promedio": round(total_mrr / n, 2),
    "Latencia promedio": round(total_latency / n, 2)
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

if summary["Hit@5 promedio"] >= 0.9:
    print("• El sistema recupera información relevante en la mayoría de las consultas.")
else:
    print("• El sistema presenta dificultades recuperando información relevante.")

if summary["Precision@5 promedio"] >= 0.8:
    print("• La precisión del retrieval es alta y los chunks recuperados son mayormente útiles.")
else:
    print("• Algunos chunks recuperados contienen ruido semántico.")

if summary["MRR promedio"] >= 0.8:
    print("• El primer resultado suele ser relevante para el usuario.")
else:
    print("• La respuesta correcta no siempre aparece en las primeras posiciones.")

if summary["Latencia promedio"] <= 1:
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

print("\nArchivo generado:")
print("resultados_evaluacion.csv")