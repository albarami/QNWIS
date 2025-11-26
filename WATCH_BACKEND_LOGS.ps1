#!/usr/bin/env pwsh
# Watch Backend Logs for Legendary Debate

Write-Host "🔍 WATCHING BACKEND LOGS FOR LEGENDARY DEBATE" -ForegroundColor Cyan
Write-Host "=" -ForegroundColor Cyan
Write-Host ""
Write-Host "This will show you the debate progress in real-time." -ForegroundColor Yellow
Write-Host "Look for these key log messages:" -ForegroundColor Yellow
Write-Host ""
Write-Host "  ✅ 'Starting legendary debate with X contradictions'" -ForegroundColor Green
Write-Host "  ✅ 'Phase 1: Opening Statements starting'" -ForegroundColor Green
Write-Host "  ✅ 'Phase 2: Challenge/Defense starting'" -ForegroundColor Green
Write-Host "  ✅ 'Consensus detected after round X'" -ForegroundColor Green
Write-Host "  ✅ 'Phase 3: Edge cases - 5 scenarios generated'" -ForegroundColor Green
Write-Host "  ✅ 'Phase 4: Risk analysis starting'" -ForegroundColor Green
Write-Host "  ✅ 'Phase 5: Consensus building'" -ForegroundColor Green
Write-Host "  ✅ 'Phase 6: Final synthesis'" -ForegroundColor Green
Write-Host "  ✅ 'Debate complete: X turns, latency=Xms'" -ForegroundColor Green
Write-Host ""
Write-Host "Press Ctrl+C to stop watching" -ForegroundColor Yellow
Write-Host ""
Write-Host "=" -ForegroundColor Cyan
Write-Host ""

# Find the backend log file or watch stdout
# For now, show how to tail the backend output

Write-Host "🔍 Watching for debate-related logs..." -ForegroundColor Cyan
Write-Host ""

# Monitor uvicorn logs (adjust path if needed)
Get-Content "uvicorn.log" -Wait -Tail 50 -ErrorAction SilentlyContinue

# If no log file, show instructions
Write-Host "💡 TIP: Run the backend with output redirection:" -ForegroundColor Yellow
Write-Host "   python -m uvicorn qnwis.api.server:app --reload --port 8000 2>&1 | Tee-Object -FilePath backend.log"
Write-Host ""
Write-Host "   Then run this script again to watch backend.log"
Write-Host ""
