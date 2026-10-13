$env:MODEL_CLIENT_MODE = "lmstudio"
$env:LMSTUDIO_BASE_URL = "http://127.0.0.1:1234"
$env:LMSTUDIO_MODEL_NAME = "local-model"
$env:MODEL_WORKER_TIMEOUT = "180"
$env:MODEL_FALLBACK_FAKE = "0"
$env:DATABASE_URL = "postgresql+psycopg2://postgres:12345@localhost:5432/lojistik_workflow"

Write-Host "Backend LM Studio modunda baslatiliyor..." -ForegroundColor Cyan
Write-Host "LM Studio URL: http://127.0.0.1:1234" -ForegroundColor Green

Set-Location $PSScriptRoot
.\.venv\Scripts\Activate.ps1
python -m uvicorn app.main:app --host 127.0.0.1 --port 8001 --reload
