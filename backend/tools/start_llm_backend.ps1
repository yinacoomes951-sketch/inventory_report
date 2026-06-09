$BackendRoot = Split-Path -Parent $PSScriptRoot
$ProjectRoot = Split-Path -Parent $BackendRoot
$Python = Join-Path $BackendRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $Python)) {
    $Python = (Get-Command python -ErrorAction Stop).Source
}

$env:PYTHONPATH = Join-Path $BackendRoot "src"
$env:AI_INVENTORY_USE_MOCK_DATA = "false"
$env:AI_INVENTORY_LLM_ENABLED = "true"
Push-Location $ProjectRoot
try {
    & $Python -m uvicorn ai_inventory_backend.app:app --host 127.0.0.1 --port 8001
}
finally {
    Pop-Location
}
