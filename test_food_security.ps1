$body = @{
    question = "Should Qatar invest `$15B in Food Valley project targeting 40% food self-sufficiency?"
    provider = "anthropic"
} | ConvertTo-Json

Write-Host "Sending request to backend..."
Write-Host "Body: $body"

try {
    $response = Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/v1/council/stream" `
        -Method Post `
        -Body $body `
        -ContentType "application/json" `
        -TimeoutSec 120
    
    Write-Host "Response received:"
    $response | ConvertTo-Json -Depth 10
} catch {
    Write-Host "Error: $_"
    Write-Host "Status Code: $($_.Exception.Response.StatusCode.value__)"
    Write-Host "Status Description: $($_.Exception.Response.StatusDescription)"
}
