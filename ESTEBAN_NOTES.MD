# ESTEBAN_NOTES

## Validación backend RAG - CRAI UAO

**Fecha:** 2026-05-30  
**Rama de trabajo:** `feature/esteban-rag`

## Objetivo

Validar la integración entre la aplicación Flask y el sistema de búsqueda vectorial con FAISS, comprobando que el flujo de consulta funcione de punta a punta.

## Archivos revisados

- `app/app.py`
- `app/faiss_store.py`
- `data/vector_store/index.faiss`
- `data/vector_store/metadata.json`
- `run.ps1`

## Qué se verificó

- La aplicación Flask inicia correctamente en `http://127.0.0.1:5000`.
- El índice vectorial `index.faiss` existe y carga correctamente.
- El archivo `metadata.json` existe y se lee sin problemas.
- El endpoint `/ask` recibe la pregunta del usuario y procesa la consulta.
- La búsqueda en el índice devuelve fragmentos relevantes (`highlights`) y fuentes (`sources`).
- El endpoint `/stats` responde con información del índice cargado.

## Resumen de validación

| Emoji | Componente | Verificación realizada | Resultado |
|---|---|---|---|
| 🌿 | Rama de trabajo | Uso de rama propia `feature/esteban-rag` | ✅ OK |
| 🚀 | App Flask | Inicio local en `http://127.0.0.1:5000` | ✅ OK |
| 🧠 | Índice FAISS | Presencia y carga de `index.faiss` | ✅ OK |
| 🗂️ | Metadatos | Lectura de `metadata.json` | ✅ OK |
| 💬 | Endpoint `/ask` | Recepción y procesamiento de preguntas | ✅ OK |
| 🔎 | Recuperación RAG | Retorno de `highlights`, `sources` y `chunks_used` | ✅ OK |
| 📊 | Endpoint `/stats` | Respuesta con estadísticas del índice | ✅ OK |
| ⚙️ | Ejecución local | Proyecto ejecutable con entorno virtual y script | ✅ OK |

## Pruebas realizadas

### 1. Estado de rama
- Rama activa: `feature/esteban-rag`
- Estado de Git: `working tree clean`

### 2. Prueba de consulta general
**Pregunta:** `Que servicios ofrece el CRAI?`  
**Resultado:** respuesta correcta con `status: ok`, `chunks_used: 5`, highlights y sources.

### 3. Prueba de consulta específica
**Pregunta:** `Cuantos puestos tiene la sala de capacitacion?`  
**Resultado:** respuesta correcta indicando capacidad para 25 personas, con fuentes relevantes.

### 4. Prueba de reglamento
**Pregunta:** `Que pasa si pierdo un libro prestado?`  
**Resultado:** respuesta correcta con condiciones de responsabilidad, devolución y posibles cargos.

### 5. Prueba de estadísticas
**Endpoint:** `GET /stats`  
**Resultado:** respuesta correcta con `total_chunks: 47` y distribución por temas.

## Tabla de pruebas

| Emoji | Prueba | Entrada | Resultado principal |
|---|---|---|---|
| 💬 | Consulta general | `Que servicios ofrece el CRAI?` | Respuesta correcta con `status: ok`, `chunks_used: 5`, highlights y sources |
| 🏫 | Consulta específica | `Cuantos puestos tiene la sala de capacitacion?` | Respuesta correcta indicando capacidad para 25 personas |
| 📚 | Consulta de reglamento | `Que pasa si pierdo un libro prestado?` | Respuesta correcta con reglas de responsabilidad, devolución y posibles cargos |
| 📈 | Estadísticas del índice | `GET /stats` | Respuesta correcta con `total_chunks: 47` y distribución por temas |

## Qué quedó funcionando

- Integración Flask + FAISS
- Lectura de metadatos
- Recuperación de contexto relevante
- Generación de respuesta con Groq
- Endpoints `/ask` y `/stats`
- Ejecución local del proyecto

## Observaciones

- La prueba inicial por PowerShell falló por codificación UTF-8 al enviar caracteres especiales en JSON.
- Se resolvió enviando el body en UTF-8.
- La recuperación funciona bien, aunque en algunos casos el `topic` detectado no coincide exactamente con el tema real de la respuesta.

## Pendientes

- Se puede mejorar la lógica de detección de tema (`detect_topic`) para clasificar mejor algunas consultas.
- Se recomienda dejar este archivo como soporte para la sustentación técnica.