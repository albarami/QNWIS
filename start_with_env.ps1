# Load environment variables from .env file
Get-Content .env | ForEach-Object {
    if ($_ -match '^([^=]+)=(.+)$') {
        $name = $matches[1]
        $value = $matches[2]
        [Environment]::SetEnvironmentVariable($name, $value, 'Process')
        Write-Host "Set $name"
    }
}

Write-Host "`n=== Environment Loaded ===" -ForegroundColor Green
Write-Host "QNWIS_LLM_PROVIDER: $env:QNWIS_LLM_PROVIDER"
Write-Host "QNWIS_ANTHROPIC_MODEL: $env:QNWIS_ANTHROPIC_MODEL"
Write-Host "DATABASE_URL: $($env:DATABASE_URL.Substring(0,50))..."
Write-Host "ANTHROPIC_API_KEY: $($env:ANTHROPIC_API_KEY.Substring(0,10))..." -ForegroundColor Yellow

Write-Host "`n=== Starting API Server ===" -ForegroundColor Cyan
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$PWD'; Get-Content .env | ForEach-Object { if (`$_ -match '^([^=]+)=(.+)`$') { [Environment]::SetEnvironmentVariable(`$matches[1], `$matches[2], 'Process') }}; python -m uvicorn src.qnwis.api.server:app --host 0.0.0.0 --port 8000 --reload"

Start-Sleep -Seconds 3

Write-Host "`n=== Starting React UI ===" -ForegroundColor Cyan
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$PWD/qnwis-ui'; npm run dev -- --host 0.0.0.0 --port 3000"

Write-Host "`n=== Servers Starting ===" -ForegroundColor Green
Write-Host "API: http://localhost:8000"
Write-Host "UI: http://localhost:3000"
Write-Host "`nReact console streams updates from council_llm via SSE"
