# Quick script to check if backend has debate logs

Write-Host "`n🔍 Searching for debate-related logs..." -ForegroundColor Cyan

# Check if any debate logs exist
$logPatterns = @(
    "STARTING legendary debate",
    "legendary_debate_node",
    "Queued debate event",
    "Yielding debate event",
    "LEGENDARY DEBATE",
    "debate_legendary"
)

$found = $false
foreach ($pattern in $logPatterns) {
    $matches = Select-String -Path "d:\lmis_int\src\qnwis\orchestration\*.py" -Pattern $pattern -SimpleMatch
    if ($matches) {
        Write-Host "✅ Pattern '$pattern' exists in code" -ForegroundColor Green
        $found = $true
    }
}

if ($found) {
    Write-Host "`n⚠️  Code has debate logging, but NO logs appeared in terminal!" -ForegroundColor Yellow
    Write-Host "This means one of:" -ForegroundColor Yellow
    Write-Host "  1. Workflow still running (stuck in data fetching)" -ForegroundColor White
    Write-Host "  2. Debate node never reached" -ForegroundColor White  
    Write-Host "  3. Legendary debate node is not being called" -ForegroundColor White
}

Write-Host "`n📊 Backend Process Status:" -ForegroundColor Cyan
Get-Process python | Where-Object {$_.Path -like "*lmis_int*"} | Select-Object Id, CPU, WorkingSet, StartTime
