$body = @{
    question = "Should Qatar invest `$15B in Food Valley project targeting 40% food self-sufficiency by 2030?"
    provider = "anthropic"
} | ConvertTo-Json

Write-Host "=========================================="
Write-Host "PHASE 8.1: FOOD SECURITY TEST"
Write-Host "=========================================="
Write-Host "Query: Should Qatar invest $15B in Food Valley project?"
Write-Host "Provider: Anthropic (claude-sonnet-4-5-20250929)"
Write-Host "=========================================="
Write-Host ""

$response = Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/v1/council/stream" `
    -Method Post `
    -Body $body `
    -ContentType "application/json" `
    -TimeoutSec 180

# Save full response
$response | Out-File -FilePath "phase8_1_food_security_output.txt"

Write-Host ""
Write-Host "=========================================="
Write-Host "RESPONSE SAVED TO: phase8_1_food_security_output.txt"
Write-Host "=========================================="

# Extract key information
$response -split "`n" | Select-String "MicroEconomist|MacroEconomist|debate" | ForEach-Object {
    Write-Host $_
}
