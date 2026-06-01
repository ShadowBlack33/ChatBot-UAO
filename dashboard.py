"""
dashboard.py - Panel de metricas del sistema RAG CRAI UAO
Ejecutar con:
    streamlit run dashboard.py
"""

import json
from collections import Counter
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st

st.set_page_config(
    page_title="Dashboard RAG | CRAI UAO",
    page_icon="📘",
    layout="wide",
    initial_sidebar_state="expanded",
)

BASE_DIR = Path(__file__).resolve().parent
CHUNKS_FILE = BASE_DIR / "data" / "clean" / "chunks.json"
URLS_FILE = BASE_DIR / "data" / "urls.json"
EVAL_FILE = BASE_DIR / "evaluation_results.json"

TOPIC_LABELS = {
    "informacion_general": "Informacion general",
    "servicios": "Servicios",
    "recursos_digitales": "Recursos digitales",
    "reglamento": "Reglamento",
    "reservas_y_horarios": "Reservas y horarios",
    "guias_y_recursos": "Guias y recursos",
    "busqueda_academica": "Busqueda academica",
    "catalogo_y_novedades": "Catalogo y novedades",
}

STABILITY_LABELS = {
    "alta": "Alta",
    "media": "Media",
    "baja": "Baja",
}

TOPIC_KEYWORDS = {
    "servicios": ["servicio", "servicios", "ofrece", "prestamo", "capacitacion", "egresado", "docente", "cultural", "club", "lectura"],
    "reglamento": ["norma", "normas", "regla", "reglamento", "debo", "puede", "sancion", "derecho", "deber", "multa", "perder", "prohibido"],
    "reservas_y_horarios": ["reserv", "horario", "hora", "sala", "espacio", "disponible", "cuando", "abre", "cierra", "schedule"],
    "recursos_digitales": ["base", "datos", "digital", "revista", "articulo", "libro", "electronico", "web", "acceso", "online", "internet", "plataforma"],
    "busqueda_academica": ["buscar", "busqueda", "encontrar", "catalogo", "filtro", "investigar", "paper", "tesis"],
    "informacion_general": ["crai", "biblioteca", "director", "contacto", "ubicacion", "telefono", "email", "donde", "queda", "direccion"],
}

EXAMPLE_QUERIES = [
    "Que servicios ofrece el CRAI?",
    "Como reservo una sala de estudio?",
    "Que recursos digitales estan disponibles?",
    "Cual es el reglamento de prestamos?",
    "Como buscar articulos cientificos?",
    "Donde queda el CRAI?",
]


@st.cache_data
def load_chunks():
    if not CHUNKS_FILE.exists():
        return []
    with open(CHUNKS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


@st.cache_data
def load_urls():
    if not URLS_FILE.exists():
        return []
    with open(URLS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


@st.cache_data
def load_evaluation():
    if not EVAL_FILE.exists():
        return {"summary": {}, "results": []}
    with open(EVAL_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def topic_label(value: str) -> str:
    return TOPIC_LABELS.get(value, value or "Sin tema")


def stability_label(value: str) -> str:
    return STABILITY_LABELS.get(value, value or "Desconocida")


def detect_topic(question: str) -> str | None:
    q = question.lower()
    for topic, keywords in TOPIC_KEYWORDS.items():
        if any(kw in q for kw in keywords):
            return topic
    return None


def source_chunk_count(chunks: list[dict], url: str) -> int:
    return sum(1 for c in chunks if c.get("source") == url)


def compute_metrics(chunks: list[dict], urls: list[dict]) -> dict:
    lengths_chars = [len(c.get("chunk", "")) for c in chunks]
    lengths_tokens = [
        c.get("chunk_length_tokens", 0)
        for c in chunks
        if isinstance(c.get("chunk_length_tokens", 0), int)
    ]
    unique_topics = sorted({c.get("topic", "") for c in chunks if c.get("topic")})
    unique_sources = sorted({c.get("source", "") for c in chunks if c.get("source")})

    return {
        "sources_indexed": len(urls),
        "chunks_total": len(chunks),
        "topics_total": len(unique_topics),
        "sources_with_chunks": len(unique_sources),
        "avg_chars": round(sum(lengths_chars) / len(lengths_chars), 1) if lengths_chars else 0,
        "avg_tokens": round(sum(lengths_tokens) / len(lengths_tokens), 1) if lengths_tokens else 0,
        "min_chars": min(lengths_chars) if lengths_chars else 0,
        "max_chars": max(lengths_chars) if lengths_chars else 0,
    }


def build_sources_table(urls: list[dict], chunks: list[dict]) -> pd.DataFrame:
    rows = []
    for item in urls:
        rows.append({
            "Fuente": item.get("title", ""),
            "Tema": topic_label(item.get("topic", "")),
            "Estabilidad": stability_label(item.get("stability", "")),
            "Chunks asociados": source_chunk_count(chunks, item.get("url", "")),
            "URL": item.get("url", ""),
        })
    return pd.DataFrame(rows)


def build_chunks_table(chunks: list[dict]) -> pd.DataFrame:
    rows = []
    for c in chunks:
        rows.append({
            "ID": c.get("id", ""),
            "Tema": topic_label(c.get("topic", "")),
            "Seccion": c.get("section", ""),
            "Titulo": c.get("title", ""),
            "Estabilidad": stability_label(c.get("stability", "")),
            "Chars": len(c.get("chunk", "")),
            "Tokens": c.get("chunk_length_tokens", ""),
            "Fuente": c.get("source", ""),
        })
    return pd.DataFrame(rows)


def build_topic_distribution(chunks: list[dict]) -> pd.DataFrame:
    counts = Counter(topic_label(c.get("topic", "Sin tema")) for c in chunks)
    df = pd.DataFrame([{"Tema": k, "Chunks": v} for k, v in counts.items()])
    return df.sort_values("Chunks", ascending=False) if not df.empty else df


def build_stability_distribution(chunks: list[dict]) -> pd.DataFrame:
    counts = Counter(stability_label(c.get("stability", "desconocida")) for c in chunks)
    order = ["Alta", "Media", "Baja", "Desconocida"]
    rows = [{"Estabilidad": k, "Chunks": counts.get(k, 0)} for k in order if counts.get(k, 0) > 0]
    return pd.DataFrame(rows)


def build_chunk_length_distribution(chunks: list[dict]) -> pd.DataFrame:
    buckets = {
        "< 120": 0,
        "120-200": 0,
        "201-300": 0,
        "301-450": 0,
        "> 450": 0,
    }
    for c in chunks:
        n = len(c.get("chunk", ""))
        if n < 120:
            buckets["< 120"] += 1
        elif n <= 200:
            buckets["120-200"] += 1
        elif n <= 300:
            buckets["201-300"] += 1
        elif n <= 450:
            buckets["301-450"] += 1
        else:
            buckets["> 450"] += 1
    return pd.DataFrame([{"Rango": k, "Chunks": v} for k, v in buckets.items()])


def build_query_examples_df(chunks: list[dict]) -> pd.DataFrame:
    rows = []
    for q in EXAMPLE_QUERIES:
        topic = detect_topic(q)
        matching_chunks = sum(1 for c in chunks if c.get("topic") == topic) if topic else 0
        rows.append({
            "Consulta ejemplo": q,
            "Tema detectado": topic_label(topic) if topic else "Sin coincidencia",
            "Chunks disponibles": matching_chunks,
        })
    return pd.DataFrame(rows)


def build_eval_results_df(eval_payload: dict) -> pd.DataFrame:
    results = eval_payload.get("results", [])
    if not results:
        return pd.DataFrame()

    df = pd.DataFrame(results)
    rename_map = {
        "pregunta": "Pregunta",
        "tema_esperado": "Tema esperado",
        "chunks_recuperados": "Chunks recuperados",
        "posiciones_relevantes": "Posiciones relevantes",
        "hit@5": "Hit@5",
        "precision@5": "Precision@5",
        "recall@5": "Recall@5",
        "mrr": "MRR",
        "latencia_segundos": "Latencia (s)",
        "topicos_recuperados": "Topicos recuperados",
        "fuentes": "Fuentes",
    }
    df = df.rename(columns=rename_map)

    if "Tema esperado" in df.columns:
        df["Tema esperado"] = df["Tema esperado"].apply(topic_label)

    return df


def build_eval_summary_df(eval_payload: dict) -> pd.DataFrame:
    summary = eval_payload.get("summary", {})
    if not summary:
        return pd.DataFrame()

    label_map = {
        "hit@5_promedio": "Hit@5 promedio",
        "precision@5_promedio": "Precision@5 promedio",
        "recall@5_promedio": "Recall@5 promedio",
        "mrr_promedio": "MRR promedio",
        "latencia_promedio_segundos": "Latencia promedio (s)",
    }

    rows = []
    for k, v in summary.items():
        rows.append({
            "Metrica": label_map.get(k, k),
            "Valor": v,
        })

    return pd.DataFrame(rows)


def build_eval_by_topic_df(eval_payload: dict) -> pd.DataFrame:
    df = build_eval_results_df(eval_payload)
    if df.empty or "Tema esperado" not in df.columns:
        return pd.DataFrame()

    numeric_cols = [c for c in ["Hit@5", "Precision@5", "Recall@5", "MRR", "Latencia (s)"] if c in df.columns]
    grouped = df.groupby("Tema esperado")[numeric_cols].mean().reset_index()
    return grouped.sort_values("MRR", ascending=False) if "MRR" in grouped.columns else grouped


def make_horizontal_metric_chart(df: pd.DataFrame, label_col: str, value_col: str, color: str = "#60a5fa"):
    chart = (
        alt.Chart(df)
        .mark_bar(cornerRadiusEnd=8, size=26, color=color)
        .encode(
            x=alt.X(f"{value_col}:Q", title="", scale=alt.Scale(domain=[0, 1])),
            y=alt.Y(f"{label_col}:N", sort="-x", title=""),
            tooltip=[label_col, alt.Tooltip(f"{value_col}:Q", format=".2f")],
        )
        .properties(height=max(220, len(df) * 42))
    )

    text = chart.mark_text(
        align="left",
        baseline="middle",
        dx=6,
        color="white"
    ).encode(
        text=alt.Text(f"{value_col}:Q", format=".2f")
    )

    return (chart + text).configure_view(strokeWidth=0)


def inject_css():
    st.markdown("""
    <style>
        .block-container {
            padding-top: 1.15rem;
            padding-bottom: 2rem;
            max-width: 1380px;
        }
        .metric-card {
            border: 1px solid rgba(148,163,184,0.16);
            border-radius: 18px;
            padding: 1rem 1.1rem;
            background: linear-gradient(180deg, rgba(15,23,42,0.55), rgba(15,23,42,0.35));
            box-shadow: 0 10px 30px rgba(0,0,0,0.15);
        }
        .small-title {
            font-size: 0.78rem;
            text-transform: uppercase;
            letter-spacing: 0.06em;
            color: #94a3b8;
            margin-bottom: 0.35rem;
        }
        .big-number {
            font-size: 1.9rem;
            font-weight: 700;
            line-height: 1.15;
            color: #f8fafc;
        }
        .hero-box {
            border: 1px solid rgba(96,165,250,0.18);
            border-radius: 18px;
            padding: 1.1rem 1.2rem;
            background: radial-gradient(circle at top left, rgba(96,165,250,0.16), rgba(15,23,42,0.18) 45%);
            margin-bottom: 1rem;
        }
        .hero-title {
            font-size: 1.45rem;
            font-weight: 700;
            color: #f8fafc;
            margin-bottom: 0.25rem;
        }
        .hero-sub {
            color: #cbd5e1;
            font-size: 0.98rem;
        }
        .caption-box {
            border: 1px solid rgba(148,163,184,0.14);
            border-radius: 14px;
            padding: 0.95rem 1rem;
            color: #cbd5e1;
            background: rgba(15,23,42,0.26);
            margin: 0.5rem 0 1rem 0;
        }
        div[data-testid="stDataFrame"] {
            border: 1px solid rgba(148,163,184,0.12);
            border-radius: 14px;
            overflow: hidden;
        }
        h1, h2, h3 {
            letter-spacing: -0.02em;
        }
    </style>
    """, unsafe_allow_html=True)


inject_css()
chunks = load_chunks()
urls = load_urls()
eval_payload = load_evaluation()
metrics = compute_metrics(chunks, urls)

with st.sidebar:
    st.markdown("## 📘 Dashboard RAG")
    st.markdown("CRAI | Universidad Autonoma de Occidente")
    st.divider()
    section = st.radio(
        "Secciones",
        [
            "Inicio",
            "Evaluacion",
            "Corpus",
            "Fuentes",
            "Explorador",
        ],
        label_visibility="collapsed",
    )
    st.divider()
    st.caption("Datos cargados desde urls.json, chunks.json y evaluation_results.json")


if section == "Inicio":
    st.markdown("""
    <div class="hero-box">
        <div class="hero-title">✨ Panel del sistema RAG CRAI UAO</div>
        <div class="hero-sub">Vista general del corpus, retrieval y cobertura tematica del proyecto.</div>
    </div>
    """, unsafe_allow_html=True)

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(f"<div class='metric-card'><div class='small-title'>📚 Fuentes</div><div class='big-number'>{metrics['sources_indexed']}</div></div>", unsafe_allow_html=True)
    with c2:
        st.markdown(f"<div class='metric-card'><div class='small-title'>🧩 Chunks</div><div class='big-number'>{metrics['chunks_total']}</div></div>", unsafe_allow_html=True)
    with c3:
        st.markdown(f"<div class='metric-card'><div class='small-title'>🏷️ Temas</div><div class='big-number'>{metrics['topics_total']}</div></div>", unsafe_allow_html=True)
    with c4:
        st.markdown(f"<div class='metric-card'><div class='small-title'>🔗 Fuentes utiles</div><div class='big-number'>{metrics['sources_with_chunks']}</div></div>", unsafe_allow_html=True)

    st.markdown("")
    c5, c6, c7 = st.columns(3)
    with c5:
        st.markdown(f"<div class='metric-card'><div class='small-title'>✍️ Promedio por chunk</div><div class='big-number'>{metrics['avg_chars']} chars</div></div>", unsafe_allow_html=True)
    with c6:
        st.markdown(f"<div class='metric-card'><div class='small-title'>🔢 Promedio tokens</div><div class='big-number'>{metrics['avg_tokens']}</div></div>", unsafe_allow_html=True)
    with c7:
        st.markdown(f"<div class='metric-card'><div class='small-title'>📏 Rango chars</div><div class='big-number'>{metrics['min_chars']} - {metrics['max_chars']}</div></div>", unsafe_allow_html=True)

    st.divider()
    st.subheader("🛠️ Arquitectura actual")
    st.code(
        """Pregunta del usuario
↓
Deteccion ligera de tema
↓
Embedding de la consulta
↓
Busqueda semantica en FAISS (top-k)
↓
Reordenamiento con refuerzo por topico
↓
Contexto ensamblado
↓
Groq / LLaMA 3.1
↓
Respuesta final + fragmentos fuente""",
        language="text",
    )

    st.markdown(
        "<div class='caption-box'>"
        "Este panel resume el estado del corpus, la evaluacion del retrieval y la trazabilidad de las fuentes del proyecto."
        "</div>",
        unsafe_allow_html=True,
    )

    st.subheader("📌 Cobertura tematica")
    topic_df = build_topic_distribution(chunks)
    if not topic_df.empty:
        st.dataframe(topic_df, use_container_width=True, hide_index=True)
    else:
        st.info("No se encontraron chunks para mostrar.")

    st.subheader("💡 Consultas de referencia")
    st.dataframe(build_query_examples_df(chunks), use_container_width=True, hide_index=True)


elif section == "Evaluacion":
    st.markdown("""
    <div class="hero-box">
        <div class="hero-title">📊 Evaluacion del sistema</div>
        <div class="hero-sub">Metricas generales del retrieval y detalle por tema y pregunta.</div>
    </div>
    """, unsafe_allow_html=True)

    eval_df = build_eval_results_df(eval_payload)
    by_topic_df = build_eval_by_topic_df(eval_payload)

    if eval_df.empty:
        st.warning(
            "No se encontro evaluation_results.json o no contiene resultados. Ejecuta primero el script de evaluacion."
        )
        st.stop()

    summary = eval_payload.get("summary", {})
    k1, k2, k3, k4, k5 = st.columns(5)

    with k1:
        st.markdown(
            f"<div class='metric-card'><div class='small-title'>✅ Hit@5</div><div class='big-number'>{summary.get('hit@5_promedio', '—')}</div></div>",
            unsafe_allow_html=True,
        )
    with k2:
        st.markdown(
            f"<div class='metric-card'><div class='small-title'>🎯 Precision@5</div><div class='big-number'>{summary.get('precision@5_promedio', '—')}</div></div>",
            unsafe_allow_html=True,
        )
    with k3:
        st.markdown(
            f"<div class='metric-card'><div class='small-title'>📎 Recall@5</div><div class='big-number'>{summary.get('recall@5_promedio', '—')}</div></div>",
            unsafe_allow_html=True,
        )
    with k4:
        st.markdown(
            f"<div class='metric-card'><div class='small-title'>🚀 MRR</div><div class='big-number'>{summary.get('mrr_promedio', '—')}</div></div>",
            unsafe_allow_html=True,
        )
    with k5:
        st.markdown(
            f"<div class='metric-card'><div class='small-title'>⏱️ Latencia</div><div class='big-number'>{summary.get('latencia_promedio_segundos', '—')} s</div></div>",
            unsafe_allow_html=True,
        )

    st.divider()
    st.subheader("Resumen visual")

    viz_left, viz_right = st.columns([1.15, 1])

    with viz_left:
        summary_chart = pd.DataFrame(
            {
                "Metrica": ["Hit@5", "MRR", "Precision@5", "Recall@5"],
                "Valor": [
                    summary.get("hit@5_promedio", 0),
                    summary.get("mrr_promedio", 0),
                    summary.get("precision@5_promedio", 0),
                    summary.get("recall@5_promedio", 0),
                ],
            }
        )

        st.markdown("#### Vista general")
        st.dataframe(
            summary_chart.sort_values("Valor", ascending=False),
            use_container_width=True,
            hide_index=True,
        )
        st.altair_chart(
            make_horizontal_metric_chart(summary_chart, "Metrica", "Valor"),
            use_container_width=True,
        )

    with viz_right:
        st.markdown("#### Rendimiento por tema")
        if not by_topic_df.empty:
            topic_table = by_topic_df.copy().round(2)
            st.dataframe(topic_table, use_container_width=True, hide_index=True)
        else:
            st.info("No hay datos agrupados por tema.")

    st.divider()
    st.subheader("🔎 Detalle por pregunta")

    filter_topic_eval = None
    if "Tema esperado" in eval_df.columns:
        available_eval_topics = sorted(eval_df["Tema esperado"].dropna().unique().tolist())
        filter_topic_eval = st.selectbox("Filtrar por tema esperado", ["Todos"] + available_eval_topics)

    filtered_eval_df = eval_df.copy()
    if filter_topic_eval and filter_topic_eval != "Todos":
        filtered_eval_df = filtered_eval_df[filtered_eval_df["Tema esperado"] == filter_topic_eval]

    st.dataframe(filtered_eval_df, use_container_width=True, hide_index=True)

    st.markdown(
        "<div class='caption-box'>"
        "Hit@5 indica si aparecio al menos un resultado relevante. Precision@5 y Recall@5 muestran la calidad del top-k. MRR refleja que tan arriba aparece el primer resultado util."
        "</div>",
        unsafe_allow_html=True,
    )


elif section == "Corpus":
    st.markdown("""
    <div class="hero-box">
        <div class="hero-title">📚 Corpus y chunks</div>
        <div class="hero-sub">Distribucion, estructura y exploracion del contenido indexado.</div>
    </div>
    """, unsafe_allow_html=True)

    if not chunks:
        st.warning("No se encontro chunks.json. Ejecuta primero scrape.py, clean.py, chunk.py e index_faiss.py.")
        st.stop()

    left, right = st.columns(2)

    with left:
        st.subheader("Distribucion por tema")
        topic_df = build_topic_distribution(chunks)
        st.dataframe(topic_df, use_container_width=True, hide_index=True)

    with right:
        st.subheader("Distribucion por estabilidad")
        stability_df = build_stability_distribution(chunks)
        st.dataframe(stability_df, use_container_width=True, hide_index=True)

    st.subheader("Longitud de chunks")
    length_df = build_chunk_length_distribution(chunks)
    st.dataframe(length_df, use_container_width=True, hide_index=True)

    st.divider()
    st.subheader("Vista tabular del corpus")
    df_chunks = build_chunks_table(chunks)

    topic_filter = st.multiselect(
        "Filtrar por tema",
        options=sorted(df_chunks["Tema"].dropna().unique().tolist()),
    )
    stability_filter = st.multiselect(
        "Filtrar por estabilidad",
        options=sorted(df_chunks["Estabilidad"].dropna().unique().tolist()),
    )

    filtered_df = df_chunks.copy()
    if topic_filter:
        filtered_df = filtered_df[filtered_df["Tema"].isin(topic_filter)]
    if stability_filter:
        filtered_df = filtered_df[filtered_df["Estabilidad"].isin(stability_filter)]

    st.dataframe(filtered_df, use_container_width=True, hide_index=True)


elif section == "Fuentes":
    st.markdown("""
    <div class="hero-box">
        <div class="hero-title">🔗 Fuentes del corpus</div>
        <div class="hero-sub">Relacion entre paginas declaradas y chunks generados por el pipeline.</div>
    </div>
    """, unsafe_allow_html=True)

    if not urls:
        st.warning("No se encontro urls.json.")
        st.stop()

    df_sources = build_sources_table(urls, chunks)
    st.dataframe(df_sources, use_container_width=True, hide_index=True)

    st.divider()
    st.subheader("Detalle por fuente")
    for item in urls:
        count = source_chunk_count(chunks, item.get("url", ""))
        with st.expander(item.get("title", "Fuente sin titulo")):
            st.markdown(f"**Tema:** {topic_label(item.get('topic', ''))}")
            st.markdown(f"**Estabilidad:** {stability_label(item.get('stability', ''))}")
            st.markdown(f"**Chunks asociados:** {count}")
            st.markdown(f"**URL:** [{item.get('url', '')}]({item.get('url', '')})")

            matching_sections = [
                c for c in chunks if c.get("source") == item.get("url", "")
            ][:5]

            if matching_sections:
                st.markdown("**Secciones de ejemplo:**")
                for c in matching_sections:
                    st.markdown(f"- {c.get('section', 'Sin seccion')}")
            else:
                st.caption("Esta fuente no produjo chunks en la version actual del corpus.")


elif section == "Explorador":
    st.markdown("""
    <div class="hero-box">
        <div class="hero-title">🧭 Explorador de chunks</div>
        <div class="hero-sub">Busqueda rapida dentro del contenido indexado por tema y texto.</div>
    </div>
    """, unsafe_allow_html=True)

    if not chunks:
        st.warning("No se encontro chunks.json.")
        st.stop()

    topics_available = sorted({topic_label(c.get("topic", "")) for c in chunks if c.get("topic")})
    selected_topic = st.selectbox("Tema", ["Todos"] + topics_available)
    search_text = st.text_input(
        "Buscar texto dentro del chunk",
        placeholder="horario, prestamo, sala, bases de datos..."
    )

    filtered = chunks
    if selected_topic != "Todos":
        filtered = [c for c in filtered if topic_label(c.get("topic", "")) == selected_topic]
    if search_text.strip():
        term = search_text.lower().strip()
        filtered = [
            c for c in filtered
            if term in c.get("chunk", "").lower() or term in c.get("section", "").lower()
        ]

    st.caption(f"Resultados: {len(filtered)} de {len(chunks)} chunks")

    for c in filtered[:40]:
        title = c.get("title", "Sin titulo")
        section_name = c.get("section", "Sin seccion")
        with st.expander(f"{title} | {section_name[:80]}"):
            st.markdown(f"**Tema:** {topic_label(c.get('topic', ''))}")
            st.markdown(f"**Estabilidad:** {stability_label(c.get('stability', ''))}")
            st.markdown(f"**Tokens:** {c.get('chunk_length_tokens', '')}")
            st.markdown(f"**Fuente:** [{c.get('source', '')}]({c.get('source', '')})")
            st.markdown("**Texto del chunk:**")
            st.write(c.get("chunk", ""))