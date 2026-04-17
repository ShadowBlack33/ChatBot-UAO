# run.ps1 — Corre el pipeline completo y levanta las dos apps
# Uso: .\run.ps1

# run.ps1
Write-Host ""
Write-Host "========================================"
Write-Host "   RAG CRAI UAO - Iniciando sistema     "
Write-Host "========================================"
Write-Host ""

Write-Host "[1/5] Scrapeando paginas del CRAI..."
python scraper/scrape.py
if ($LASTEXITCODE -ne 0) { Write-Host "ERROR en scrape.py"; exit 1 }
Write-Host "      OK"

Write-Host "[2/5] Limpiando contenido..."
python scraper/clean.py
if ($LASTEXITCODE -ne 0) { Write-Host "ERROR en clean.py"; exit 1 }
Write-Host "      OK"

Write-Host "[3/5] Generando chunks..."
python scraper/chunk.py
if ($LASTEXITCODE -ne 0) { Write-Host "ERROR en chunk.py"; exit 1 }
Write-Host "      OK"

Write-Host ""
Write-Host "[4/5] Iniciando chatbot en http://127.0.0.1:5000 ..."
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$PWD'; .\venv\Scripts\Activate.ps1; python app/app.py"

Start-Sleep -Seconds 2

Write-Host "[5/5] Iniciando dashboard en http://localhost:8501 ..."
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$PWD'; .\venv\Scripts\Activate.ps1; streamlit run dashboard.py"

Write-Host ""
Write-Host "========================================"
Write-Host " Chatbot   -> http://127.0.0.1:5000"
Write-Host " Dashboard -> http://localhost:8501"
Write-Host "========================================"
Write-Host ""