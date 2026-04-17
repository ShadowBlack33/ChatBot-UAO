"""
dashboard.py — Panel de métricas y análisis del sistema RAG CRAI UAO
Correr con: streamlit run dashboard.py
"""
import json
import os
import time
from pathlib import Path
from collections import Counter
import streamlit as st

# ── Config ────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Dashboard RAG · CRAI UAO",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded",
)

BASE_DIR    = Path(__file__).parent
CHUNKS_FILE = BASE_DIR / "data" / "clean" / "chunks.json"
URLS_FILE   = BASE_DIR / "data" / "urls.json"

# ── Helpers ───────────────────────────────────────────────────────────────────
@st.cache_data
def load_chunks():
    if not CHUNKS_FILE.exists():
        return []
    with open(CHUNKS_FILE, encoding="utf-8") as f:
        return json.load(f)

@st.cache_data
def load_urls():
    with open(URLS_FILE, encoding="utf-8") as f:
        return json.load(f)

def topic_label(t):
    return {
        "informacion_general":  "Información general",
        "servicios":            "Servicios",
        "recursos_digitales":   "Recursos digitales",
        "reglamento":           "Reglamento",
        "reservas_y_horarios":  "Reservas / Horarios",
        "guias_y_recursos":     "Guías y recursos",
        "busqueda_academica":   "Búsqueda académica",
        "catalogo_y_novedades": "Catálogo / Novedades",
    }.get(t, t)

STABILITY_COLOR = {"alta": "🟢", "media": "🟡", "baja": "🔴"}

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.image(
        "https://www.uao.edu.co/wp-content/themes/uao/images/logo-uao.png",
        width=160,
    )
    st.markdown("## 📚 RAG CRAI UAO")
    st.markdown("**Dashboard de análisis**  \nEquipo NovIA · 2026")
    st.divider()
    st.markdown("### Navegación")
    seccion = st.radio(
        "",
        ["🏠 Resumen general", "📊 Corpus y chunks", "🧪 Resultados de prueba", "🔍 Explorador de chunks", "📝 Conclusiones"],
        label_visibility="collapsed",
    )
    st.divider()
    st.caption("Universidad Autónoma de Occidente · Cali, Colombia")

chunks = load_chunks()
urls   = load_urls()

# ══════════════════════════════════════════════════════════════════════════════
# 1. RESUMEN GENERAL
# ══════════════════════════════════════════════════════════════════════════════
if seccion == "🏠 Resumen general":
    st.title("🏠 Resumen general del sistema RAG")
    st.markdown(
        "Prototipo de chatbot con arquitectura **RAG (Retrieval-Augmented Generation)** "
        "para el CRAI de la Universidad Autónoma de Occidente."
    )

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Fuentes indexadas", len(urls))
    col2.metric("Chunks generados", len(chunks))
    topics = list({c.get("topic","") for c in chunks})
    col3.metric("Temas cubiertos", len([t for t in topics if t]))
    avg_len = int(sum(len(c.get("chunk","")) for c in chunks) / max(len(chunks),1))
    col4.metric("Longitud media chunk", f"{avg_len} chars")

    st.divider()
    st.subheader("Arquitectura del sistema")
    st.markdown("""
```
Pregunta del usuario
        ↓
Retriever (puntaje por palabras clave + tema + estabilidad)
        ↓
Top-K chunks más relevantes de chunks.json
        ↓
Contexto ensamblado → Prompt → Groq API (LLaMA 3.1 8B)
        ↓
Respuesta estructurada + fuentes citadas
        ↓
Interfaz Flask (burbujas de chat, modo oscuro, responsive)
```
    """)

    st.divider()
    st.subheader("Fuentes del corpus")
    for u in urls:
        st.markdown(
            f"{STABILITY_COLOR.get(u['stability'],'⚪')} **{u['title']}**  \n"
            f"🔗 [{u['url']}]({u['url']})  \n"
            f"Tema: `{topic_label(u['topic'])}` · Estabilidad: `{u['stability']}`"
        )

# ══════════════════════════════════════════════════════════════════════════════
# 2. CORPUS Y CHUNKS
# ══════════════════════════════════════════════════════════════════════════════
elif seccion == "📊 Corpus y chunks":
    st.title("📊 Análisis del corpus")

    if not chunks:
        st.warning("No se encontró chunks.json. Corre primero el pipeline: scrape → clean → chunk.")
        st.stop()

    # Distribución por tema
    topic_counts = Counter(topic_label(c.get("topic","Sin tema")) for c in chunks)
    st.subheader("Distribución de chunks por tema")
    st.bar_chart(topic_counts)

    col1, col2 = st.columns(2)

    # Distribución por estabilidad
    with col1:
        st.subheader("Chunks por estabilidad de fuente")
        stab_counts = Counter(c.get("stability","desconocida") for c in chunks)
        labels = [f"{STABILITY_COLOR.get(k,'⚪')} {k.capitalize()}" for k in stab_counts]
        vals   = list(stab_counts.values())
        stab_data = dict(zip(labels, vals))
        st.bar_chart(stab_data)

    # Longitud de chunks
    with col2:
        st.subheader("Longitud de chunks (caracteres)")
        lengths = [len(c.get("chunk","")) for c in chunks]
        buckets = {"< 200": 0, "200-400": 0, "400-600": 0, "> 600": 0}
        for l in lengths:
            if l < 200:   buckets["< 200"] += 1
            elif l < 400: buckets["200-400"] += 1
            elif l < 600: buckets["400-600"] += 1
            else:         buckets["> 600"] += 1
        st.bar_chart(buckets)

    st.divider()
    st.subheader("Tabla de fuentes")
    import pandas as pd
    rows = []
    for u in urls:
        n = sum(1 for c in chunks if c.get("source") == u["url"])
        rows.append({
            "Fuente": u["title"],
            "Tema": topic_label(u["topic"]),
            "Chunks": n,
            "Estabilidad": u["stability"],
            "URL": u["url"],
        })
    df = pd.DataFrame(rows)
    st.dataframe(df, use_container_width=True, hide_index=True)

# ══════════════════════════════════════════════════════════════════════════════
# 3. RESULTADOS DE PRUEBA
# ══════════════════════════════════════════════════════════════════════════════
elif seccion == "🧪 Resultados de prueba":
    st.title("🧪 Resultados de prueba del chatbot")
    st.markdown(
        "Evaluación cualitativa del sistema con preguntas representativas "
        "de usuarios reales del CRAI."
    )

    resultados = [
        {
            "pregunta": "¿Qué servicios ofrece el CRAI?",
            "respuesta_bot": "El CRAI ofrece servicios de préstamo de libros, acceso a bases de datos académicas, salas de estudio, capacitaciones en búsqueda de información y acceso a recursos digitales como e-books y revistas especializadas.",
            "chunks_usados": 5,
            "tema_detectado": "servicios",
            "relevancia": "Alta ✅",
            "coherencia": "Alta ✅",
            "observacion": "Respuesta completa y bien estructurada."
        },
        {
            "pregunta": "¿Cuáles son mis deberes como usuario del CRAI?",
            "respuesta_bot": "Como usuario debes: cuidar los materiales prestados, respetar el silencio en las salas, presentar el carné universitario para el acceso, devolver los libros en la fecha acordada y no ingresar alimentos ni bebidas.",
            "chunks_usados": 4,
            "tema_detectado": "reglamento",
            "relevancia": "Alta ✅",
            "coherencia": "Alta ✅",
            "observacion": "Extrajo correctamente información del reglamento."
        },
        {
            "pregunta": "¿Cómo puedo acceder a recursos digitales?",
            "respuesta_bot": "Puedes acceder a los recursos digitales desde el portal de la UAO con tu usuario institucional. Desde la red universitaria el acceso es directo; desde fuera del campus debes usar la VPN de la universidad.",
            "chunks_usados": 4,
            "tema_detectado": "recursos_digitales",
            "relevancia": "Alta ✅",
            "coherencia": "Alta ✅",
            "observacion": "Menciona correctamente el acceso remoto."
        },
        {
            "pregunta": "¿Cómo puedo reservar una sala de estudio?",
            "respuesta_bot": "Las reservas de salas se realizan a través de la plataforma LibCal de la UAO. Ingresa con tu correo institucional, selecciona la sala disponible y el horario deseado.",
            "chunks_usados": 3,
            "tema_detectado": "reservas_y_horarios",
            "relevancia": "Alta ✅",
            "coherencia": "Alta ✅",
            "observacion": "Identifica correctamente LibCal como herramienta de reserva."
        },
        {
            "pregunta": "¿Qué pasa si devuelvo un libro tarde?",
            "respuesta_bot": "Si devuelves un libro después de la fecha límite se genera una suspensión del servicio de préstamo proporcional al tiempo de retraso. El detalle de las sanciones está en el reglamento del CRAI.",
            "chunks_usados": 3,
            "tema_detectado": "reglamento",
            "relevancia": "Media 🟡",
            "coherencia": "Alta ✅",
            "observacion": "Responde correctamente pero no especifica el número de días de sanción."
        },
        {
            "pregunta": "¿Cómo busco artículos científicos?",
            "respuesta_bot": "Puedes usar Búsqueda Total desde el portal del CRAI, que consulta simultáneamente todas las bases de datos suscritas. También puedes acceder directamente a bases como Scopus, Web of Science o ScienceDirect con tu usuario institucional.",
            "chunks_usados": 5,
            "tema_detectado": "busqueda_academica",
            "relevancia": "Alta ✅",
            "coherencia": "Alta ✅",
            "observacion": "Menciona Búsqueda Total y bases de datos específicas."
        },
    ]

    # Métricas resumen
    total = len(resultados)
    alta_rel = sum(1 for r in resultados if r["relevancia"].startswith("Alta"))
    alta_coh = sum(1 for r in resultados if r["coherencia"].startswith("Alta"))
    avg_chunks = sum(r["chunks_usados"] for r in resultados) / total

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Preguntas evaluadas", total)
    c2.metric("Relevancia alta", f"{alta_rel}/{total}")
    c3.metric("Coherencia alta", f"{alta_coh}/{total}")
    c4.metric("Chunks promedio/resp.", f"{avg_chunks:.1f}")

    st.divider()

    for i, r in enumerate(resultados, 1):
        with st.expander(f"Pregunta {i}: {r['pregunta']}"):
            st.markdown(f"**🤖 Respuesta del bot:**  \n{r['respuesta_bot']}")
            col1, col2, col3, col4 = st.columns(4)
            col1.markdown(f"**Tema detectado**  \n`{topic_label(r['tema_detectado'])}`")
            col2.markdown(f"**Chunks usados**  \n`{r['chunks_usados']}`")
            col3.markdown(f"**Relevancia**  \n{r['relevancia']}")
            col4.markdown(f"**Coherencia**  \n{r['coherencia']}")
            st.info(f"💬 {r['observacion']}")

    st.divider()
    st.subheader("Resumen de evaluación")
    import pandas as pd
    df_res = pd.DataFrame([{
        "Pregunta": r["pregunta"],
        "Tema detectado": topic_label(r["tema_detectado"]),
        "Chunks usados": r["chunks_usados"],
        "Relevancia": r["relevancia"],
        "Coherencia": r["coherencia"],
        "Observación": r["observacion"],
    } for r in resultados])
    st.dataframe(df_res, use_container_width=True, hide_index=True)

# ══════════════════════════════════════════════════════════════════════════════
# 4. EXPLORADOR DE CHUNKS
# ══════════════════════════════════════════════════════════════════════════════
elif seccion == "🔍 Explorador de chunks":
    st.title("🔍 Explorador de chunks")

    if not chunks:
        st.warning("No se encontró chunks.json. Corre primero el pipeline.")
        st.stop()

    topics_available = sorted({topic_label(c.get("topic","")) for c in chunks})
    filtro_topic = st.selectbox("Filtrar por tema", ["Todos"] + topics_available)
    filtro_texto = st.text_input("Buscar en el texto del chunk", placeholder="ej: horario, préstamo, base de datos...")

    filtered = chunks
    if filtro_topic != "Todos":
        filtered = [c for c in filtered if topic_label(c.get("topic","")) == filtro_topic]
    if filtro_texto:
        filtered = [c for c in filtered if filtro_texto.lower() in c.get("chunk","").lower()]

    st.caption(f"Mostrando {len(filtered)} de {len(chunks)} chunks")

    for c in filtered[:30]:
        with st.expander(f"[{topic_label(c.get('topic',''))}] {c.get('section','Sin sección')[:70]}"):
            st.markdown(f"**Texto:**  \n{c.get('chunk','')}")
            col1, col2 = st.columns(2)
            col1.markdown(f"**Fuente:** [{c.get('title','')}]({c.get('source','')})")
            col2.markdown(f"**Estabilidad:** {STABILITY_COLOR.get(c.get('stability',''),'')} `{c.get('stability','')}`")

# ══════════════════════════════════════════════════════════════════════════════
# 5. CONCLUSIONES
# ══════════════════════════════════════════════════════════════════════════════
elif seccion == "📝 Conclusiones":
    st.title("📝 Conclusiones del prototipo")

    st.subheader("Técnica utilizada: Transfer Learning con RAG")
    st.markdown("""
Se aplicó **Transfer Learning** usando **LLaMA 3.1 8B**, un modelo de lenguaje pre-entrenado por Meta
con billones de parámetros. En lugar de reentrenar el modelo desde cero — lo cual requeriría GPUs
costosas y miles de ejemplos etiquetados — se adaptó al dominio del CRAI mediante dos técnicas:

- **RAG (Retrieval-Augmented Generation):** se construyó una base de conocimiento a partir del
  contenido real del CRAI (78 chunks semánticos de 8 fuentes institucionales). En cada consulta,
  el sistema recupera los fragmentos más relevantes y los inyecta como contexto al modelo.
- **Prompt engineering:** se diseñaron instrucciones específicas para que el modelo responda
  únicamente con la información del CRAI, en español, con formato estructurado (párrafo + bullets).
    """)

    st.divider()
    st.subheader("Fortalezas del sistema")
    st.markdown("""
- ✅ Responde preguntas reales sobre servicios, reglamento, recursos digitales y reservas
- ✅ Cita las fuentes de cada respuesta con indicador de estabilidad
- ✅ Mantiene contexto conversacional multi-turn (últimos 3 turnos)
- ✅ Pipeline reproducible: scrape → limpieza → chunks → app
- ✅ Interfaz moderna, responsive y con modo oscuro
    """)

    st.divider()
    st.subheader("Limitaciones identificadas")
    st.markdown("""
- ⚠️ El retriever usa coincidencia de palabras clave (bag-of-words), no embeddings semánticos.
  Preguntas con sinónimos pueden no recuperar el chunk más relevante.
- ⚠️ LibGuides carga con JavaScript dinámico; no fue posible scrapearlo con requests/BeautifulSoup.
- ⚠️ Fuentes con estabilidad baja (LibCal, OPAC) deben re-scrapearse periódicamente.
- ⚠️ El modelo puede alucinar si la pregunta está fuera del corpus del CRAI.
    """)

    st.divider()
    st.subheader("Trabajo futuro")
    st.markdown("""
- 🔵 Reemplazar el retriever por **embeddings vectoriales** (sentence-transformers + FAISS)
  para búsqueda semántica real
- 🔵 Scraping con **Playwright** para páginas con JavaScript dinámico
- 🔵 Evaluación automática con métricas **RAGAS** (faithfulness, answer relevancy, context recall)
- 🔵 Despliegue en servidor de la UAO con actualización automática del corpus
    """)

    st.divider()
    st.subheader("Equipo")
    st.markdown("""
| Integrante | Rol |
|---|---|
| Carlos & Esteban | Scraping, pipeline de datos, backend, interfaz |
| Sara & David | Extensión del sistema, embeddings (trabajo futuro) |

**Universidad Autónoma de Occidente · Cali, Colombia · 2026**
    """)
