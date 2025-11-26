# Level 4 Fix Validation Script
# Automated testing helper for verifying the 6 critical fixes

param(
    [string]$BackendUrl = "http://localhost:8000",
    [string]$Question = "What are the unemployment trends in Qatar?",
    [string]$Provider = "stub"
)

Write-Host "🔍 Level 4 Fix Validation Script" -ForegroundColor Cyan
Write-Host "=================================" -ForegroundColor Cyan
Write-Host ""

# Color codes
$Green = "Green"
$Red = "Red"
$Yellow = "Yellow"
$Cyan = "Cyan"

# Test counter
$script:testsPassed = 0
$script:testsFailed = 0

function Test-Step {
    param(
        [string]$Name,
        [scriptblock]$Test,
        [string]$SuccessMessage,
        [string]$FailureMessage
    )
    
    Write-Host "Testing: $Name" -ForegroundColor $Cyan
    try {
        $result = & $Test
        if ($result) {
            Write-Host "  ✅ PASS: $SuccessMessage" -ForegroundColor $Green
            $script:testsPassed++
            return $true
        } else {
            Write-Host "  ❌ FAIL: $FailureMessage" -ForegroundColor $Red
            $script:testsFailed++
            return $false
        }
    } catch {
        Write-Host "  ❌ ERROR: $_" -ForegroundColor $Red
        $script:testsFailed++
        return $false
    }
}

Write-Host "Step 1: Pre-Test Checks" -ForegroundColor Yellow
Write-Host "------------------------" -ForegroundColor Yellow

# Check if backend is running
Test-Step -Name "Backend Health Check" -Test {
    try {
        $response = Invoke-RestMethod -Uri "$BackendUrl/health" -Method Get -TimeoutSec 5
        return $response.status -eq "healthy"
    } catch {
        return $false
    }
} -SuccessMessage "Backend is healthy" -FailureMessage "Backend is not responding or unhealthy"

# Check if backend logs show RAG pre-warming (manual check)
Write-Host ""
Write-Host "⚠️  MANUAL CHECK REQUIRED:" -ForegroundColor $Yellow
Write-Host "   Check your backend logs for:" -ForegroundColor $Yellow
Write-Host "   'INFO - Pre-warming RAG components (embedder + document store)...'" -ForegroundColor $Yellow
Write-Host "   'INFO - RAG components warm-up scheduled'" -ForegroundColor $Yellow
Write-Host ""
$ragWarmed = Read-Host "Did you see RAG pre-warming messages in backend logs? (y/n)"
if ($ragWarmed -eq "y") {
    Write-Host "  ✅ PASS: RAG pre-warming confirmed" -ForegroundColor $Green
    $script:testsPassed++
} else {
    Write-Host "  ⚠️  WARNING: RAG pre-warming not confirmed - may be slow on first request" -ForegroundColor $Yellow
}

Write-Host ""
Write-Host "Step 2: SSE Stream Test" -ForegroundColor Yellow
Write-Host "------------------------" -ForegroundColor Yellow

Write-Host "Sending test question to /council/stream endpoint..." -ForegroundColor $Cyan
Write-Host "Question: $Question" -ForegroundColor $Cyan
Write-Host "Provider: $Provider" -ForegroundColor $Cyan
Write-Host ""

# Test SSE stream (basic connectivity)
Test-Step -Name "SSE Stream Connectivity" -Test {
    try {
        $body = @{
            question = $Question
            provider = $Provider
        } | ConvertTo-Json
        
        # Use curl for SSE (Invoke-WebRequest doesn't handle SSE well)
        $curlPath = "curl"
        $response = & $curlPath -N -X POST "$BackendUrl/api/v1/council/stream" `
            -H "Content-Type: application/json" `
            -d $body `
            --max-time 10 `
            2>&1
        
        # Check if we got any SSE events
        return $response -match "data:"
    } catch {
        Write-Host "Error details: $_" -ForegroundColor $Red
        return $false
    }
} -SuccessMessage "SSE stream is responding" -FailureMessage "SSE stream failed to respond"

Write-Host ""
Write-Host "Step 3: Manual UI Testing" -ForegroundColor Yellow
Write-Host "--------------------------" -ForegroundColor Yellow
Write-Host ""
Write-Host "Please perform the following manual tests in the UI:" -ForegroundColor $Cyan
Write-Host ""
Write-Host "1. Open http://localhost:5173 in your browser" -ForegroundColor White
Write-Host "2. Open DevTools (F12) and go to Console tab" -ForegroundColor White
Write-Host "3. Submit the question: '$Question'" -ForegroundColor White
Write-Host "4. Select provider: '$Provider'" -ForegroundColor White
Write-Host ""
Write-Host "Expected Behavior Checklist:" -ForegroundColor $Cyan
Write-Host "  [ ] Classification stage completes quickly (<100ms for stub)" -ForegroundColor White
Write-Host "  [ ] Prefetch stage completes successfully" -ForegroundColor White
Write-Host "  [ ] RAG stage completes (no long delay)" -ForegroundColor White
Write-Host "  [ ] Agent selection shows EXACTLY 12 unique agents" -ForegroundColor White
Write-Host "  [ ] All 12 agents either complete or show error (no stuck 'running')" -ForegroundColor White
Write-Host "  [ ] Debate stage completes" -ForegroundColor White
Write-Host "  [ ] Critique stage completes" -ForegroundColor White
Write-Host "  [ ] Verification stage completes" -ForegroundColor White
Write-Host "  [ ] Synthesis stage completes" -ForegroundColor White
Write-Host "  [ ] Final 'done' event received" -ForegroundColor White
Write-Host "  [ ] NO browser console errors" -ForegroundColor White
Write-Host "  [ ] Screen does NOT go dark" -ForegroundColor White
Write-Host "  [ ] No duplicate agent cards" -ForegroundColor White
Write-Host ""

$uiTestsPassed = Read-Host "Did all UI tests pass? (y/n)"
if ($uiTestsPassed -eq "y") {
    Write-Host "  ✅ PASS: UI tests successful" -ForegroundColor $Green
    $script:testsPassed++
} else {
    Write-Host "  ❌ FAIL: Some UI tests failed" -ForegroundColor $Red
    $script:testsFailed++
    Write-Host ""
    Write-Host "Please check the following:" -ForegroundColor $Yellow
    Write-Host "  - Backend logs for errors" -ForegroundColor White
    Write-Host "  - Browser console for JavaScript errors" -ForegroundColor White
    Write-Host "  - Network tab for failed requests" -ForegroundColor White
}

Write-Host ""
Write-Host "Step 4: Error Handling Test" -ForegroundColor Yellow
Write-Host "----------------------------" -ForegroundColor Yellow
Write-Host ""
Write-Host "⚠️  MANUAL CHECK: Test error recovery by disconnecting network mid-workflow" -ForegroundColor $Yellow
Write-Host "Expected:" -ForegroundColor $Cyan
Write-Host "  - Error banner appears with clear message" -ForegroundColor White
Write-Host "  - UI remains responsive (no dark screen)" -ForegroundColor White
Write-Host "  - Connection status changes to 'error'" -ForegroundColor White
Write-Host "  - User can retry the query" -ForegroundColor White
Write-Host ""

$errorHandlingPassed = Read-Host "Did error handling work correctly? (y/n)"
if ($errorHandlingPassed -eq "y") {
    Write-Host "  ✅ PASS: Error handling is graceful" -ForegroundColor $Green
    $script:testsPassed++
} else {
    Write-Host "  ❌ FAIL: Error handling needs improvement" -ForegroundColor $Red
    $script:testsFailed++
}

Write-Host ""
Write-Host "=================================" -ForegroundColor Cyan
Write-Host "Test Results Summary" -ForegroundColor Cyan
Write-Host "=================================" -ForegroundColor Cyan
Write-Host "Tests Passed: $script:testsPassed" -ForegroundColor $Green
Write-Host "Tests Failed: $script:testsFailed" -ForegroundColor $Red
Write-Host ""

if ($script:testsFailed -eq 0) {
    Write-Host "🎉 ALL TESTS PASSED! Level 4 fixes are working correctly." -ForegroundColor $Green
    Write-Host ""
    Write-Host "Next Steps:" -ForegroundColor $Cyan
    Write-Host "1. Test with Anthropic provider (requires API key)" -ForegroundColor White
    Write-Host "2. Test with complex questions" -ForegroundColor White
    Write-Host "3. Test rapid-fire queries (3 or more in succession)" -ForegroundColor White
    Write-Host "4. Review LEVEL4_FIX_VERIFICATION_COMPLETE.md for full checklist" -ForegroundColor White
} else {
    Write-Host "⚠️  Some tests failed. Please review the errors above and:" -ForegroundColor $Yellow
    Write-Host "1. Check backend logs for errors" -ForegroundColor White
    Write-Host "2. Verify all 6 fixes are properly implemented" -ForegroundColor White
    Write-Host "3. Restart backend and frontend servers" -ForegroundColor White
    Write-Host "4. Clear browser cache and retry" -ForegroundColor White
    Write-Host "5. Consult LEVEL4_FIX_VERIFICATION_COMPLETE.md for troubleshooting" -ForegroundColor White
}

Write-Host ""
Write-Host "For detailed verification checklist, see:" -ForegroundColor $Cyan
Write-Host "  LEVEL4_FIX_VERIFICATION_COMPLETE.md" -ForegroundColor White
Write-Host ""
