[Console]::InputEncoding  = [System.Text.UTF8Encoding]::new()
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new()
$OutputEncoding = [System.Text.UTF8Encoding]::new()
chcp 65001 > $null

# run.ps1 - Ejecuta pipeline completo, evaluacion y levanta Flask + Streamlit
# Uso:
#   .\run.ps1

Write-Host ""
Write-Host "==============================================="
Write-Host "  RAG CRAI UAO - Orquestacion completa"
Write-Host "==============================================="
Write-Host ""

$projectRoot = $PSScriptRoot
$venvPython = Join-Path $projectRoot "venv\Scripts\python.exe"
$activateScript = Join-Path $projectRoot "venv\Scripts\Activate.ps1"
$envFile = Join-Path $projectRoot ".env"

if (!(Test-Path $venvPython)) {
    Write-Host "ERROR: No se encontro el entorno virtual en venv\Scripts\python.exe"
    Write-Host "Crea primero el entorno e instala dependencias."
    exit 1
}

if (!(Test-Path $envFile)) {
    Write-Host "ADVERTENCIA: No se encontro .env en la raiz del proyecto."
    Write-Host "El chatbot puede fallar si GROQ_API_KEY no esta definida."
    Write-Host ""
}

Set-Location $projectRoot

Write-Host "[1/7] Scrapeando paginas del CRAI..."
& $venvPython "scraper/scrape.py"
if ($LASTEXITCODE -ne 0) { Write-Host "ERROR en scraper/scrape.py"; exit 1 }
Write-Host "      OK"
Write-Host ""

Write-Host "[2/7] Limpiando contenido..."
& $venvPython "scraper/clean.py"
if ($LASTEXITCODE -ne 0) { Write-Host "ERROR en scraper/clean.py"; exit 1 }
Write-Host "      OK"
Write-Host ""

Write-Host "[3/7] Generando chunks..."
& $venvPython "scraper/chunk.py"
if ($LASTEXITCODE -ne 0) { Write-Host "ERROR en scraper/chunk.py"; exit 1 }
Write-Host "      OK"
Write-Host ""

Write-Host "[4/7] Generando embeddings e indice FAISS..."
& $venvPython "embeddings/index_faiss.py"
if ($LASTEXITCODE -ne 0) { Write-Host "ERROR en embeddings/index_faiss.py"; exit 1 }
Write-Host "      OK"
Write-Host ""

Write-Host "[5/7] Ejecutando evaluacion del retriever..."
& $venvPython "evaluation.py"
if ($LASTEXITCODE -ne 0) { Write-Host "ERROR en evaluation.py"; exit 1 }
Write-Host "      OK"
Write-Host ""

Write-Host "[6/7] Iniciando chatbot Flask en http://127.0.0.1:5000 ..."
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$projectRoot'; .\venv\Scripts\Activate.ps1; python -m app.app"

Start-Sleep -Seconds 3

Write-Host "[7/7] Iniciando dashboard Streamlit en http://localhost:8501 ..."
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$projectRoot'; .\venv\Scripts\Activate.ps1; python -m streamlit run dashboard.py"

Write-Host ""
Write-Host "==============================================="
Write-Host "  Servicios iniciados"
Write-Host "-----------------------------------------------"
Write-Host "  Chatbot   -> http://127.0.0.1:5000"
Write-Host "  Dashboard -> http://localhost:8501"
Write-Host "==============================================="
Write-Host ""