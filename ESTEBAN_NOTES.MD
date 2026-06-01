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

- La aplicación Flask inicia correctamente en entorno local.
- El índice vectorial `index.faiss` existe y carga correctamente.
- El archivo `metadata.json` existe y se procesa sin errores.
- El endpoint `/ask` recibe la pregunta del usuario y ejecuta el flujo RAG.
- La búsqueda sobre FAISS devuelve fragmentos relevantes y metadatos asociados.
- La respuesta incluye campos estructurados como `answer`, `highlights`, `sources`, `topic` y `chunks_used`.
- El endpoint `/stats` responde con información del corpus cargado.
- La ejecución local del proyecto funciona con entorno virtual y script de arranque.

## Resumen de validación

| Componente | Verificación realizada | Resultado |
|---|---|---|
| Rama de trabajo | Uso de rama propia `feature/esteban-rag` | OK |
| App Flask | Inicio local del backend | OK |
| Índice FAISS | Presencia y carga de `index.faiss` | OK |
| Metadatos | Lectura de `metadata.json` | OK |
| Endpoint `/ask` | Recepción y procesamiento de preguntas | OK |
| Recuperación RAG | Retorno de `highlights`, `sources` y `chunks_used` | OK |
| Endpoint `/stats` | Respuesta con estadísticas del corpus | OK |
| Ejecución local | Proyecto ejecutable con entorno virtual y script | OK |

## Pruebas realizadas

### 1. Estado de rama

- Rama activa: `feature/esteban-rag`
- Estado de Git: `working tree clean`

### 2. Prueba de consulta general

**Pregunta:** `¿Qué servicios ofrece el CRAI?`  
**Resultado:** el backend respondió con `status: ok`, construyó contexto con chunks recuperados y devolvió `highlights`, `sources` y `chunks_used`.

### 3. Prueba de consulta específica

**Pregunta:** `¿Cuántos puestos tiene la sala de capacitación?`  
**Resultado:** el flujo RAG respondió correctamente usando fragmentos recuperados desde el índice, con trazabilidad hacia la fuente correspondiente.

### 4. Prueba de reglamento

**Pregunta:** `¿Qué pasa si pierdo un libro prestado?`  
**Resultado:** el backend devolvió una respuesta basada en fragmentos normativos relevantes y mostró fuentes asociadas en la respuesta estructurada.

### 5. Prueba de estadísticas

**Endpoint:** `GET /stats`  
**Resultado:** respuesta correcta con estadísticas generales del corpus cargado e información agregada del sistema de recuperación.

## Tabla de pruebas

| Prueba | Entrada | Resultado principal |
|---|---|---|
| Consulta general | `¿Qué servicios ofrece el CRAI?` | Respuesta correcta con `status: ok`, `chunks_used`, `highlights` y `sources`. |
| Consulta específica | `¿Cuántos puestos tiene la sala de capacitación?` | Respuesta correcta basada en chunks relevantes del índice. |
| Consulta de reglamento | `¿Qué pasa si pierdo un libro prestado?` | Respuesta correcta con contexto normativo y trazabilidad. |
| Estadísticas del sistema | `GET /stats` | Respuesta correcta con estadísticas del corpus e índice cargado. |

## Qué quedó funcionando

- Integración Flask + FAISS.
- Lectura de metadatos del índice.
- Recuperación de contexto relevante.
- Generación de respuesta con Groq a partir de contexto recuperado.
- Endpoints `/ask` y `/stats`.
- Ejecución local del proyecto con script de arranque.

## Observaciones

- La validación inicial desde PowerShell presentó problemas de codificación UTF-8 al enviar caracteres especiales en el cuerpo JSON, un problema común cuando el request no se envía correctamente codificado en UTF-8 [web:1158][web:1164].
- La ejecución del backend debe hacerse con `python -m app.app` para evitar conflictos de imports del paquete `app` en Windows [cite:1].
- La asociación entre índice FAISS y metadatos depende de mantener consistencia entre `index.faiss` y `metadata.json`, lo cual es una práctica habitual en implementaciones que separan vectores y metadata [web:1157][web:1160].

## Pendientes

- Mejorar la lógica de detección de tema (`detect_topic`) para algunas consultas ambiguas.
- Agregar pruebas automáticas de endpoints para reducir dependencia de validación manual, algo recomendado en pruebas de aplicaciones Flask [web:1159].
- Controlar `debug=True` mediante variables de entorno para desarrollo local seguro, en lugar de dejarlo fijo en el código [web:1162][web:1165].
- Dejar este archivo como soporte para sustentación técnica y validación del backend.

## Conclusión

La validación realizada confirma que el backend del sistema RAG integra correctamente Flask, FAISS, metadatos y generación con LLM dentro de un flujo funcional de consulta. El sistema carga el índice, recupera contexto relevante, responde preguntas mediante el endpoint `/ask` y expone estadísticas mediante `/stats`, dejando una base estable para mejoras posteriores en evaluación, clasificación temática y robustez operativa.