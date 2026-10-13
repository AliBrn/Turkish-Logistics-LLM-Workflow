$ErrorActionPreference = "Stop"
$projectRoot = Resolve-Path "$PSScriptRoot\.."
Set-Location $projectRoot
$env:MODEL_CLIENT_MODE = "qwen25_http"
$env:MODEL_WORKER_URL = "http://127.0.0.1:8010/extract"
$env:MODEL_FALLBACK_FAKE = "1"
& "$PSScriptRoot\.venv\Scripts\python.exe" -m uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000
