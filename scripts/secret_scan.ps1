# Secret Scanner for QNWIS
# Detects potential hardcoded secrets in codebase
# Run before commits to prevent secret leaks

Write-Host "=" * 70
Write-Host "QNWIS SECRET SCANNER"
Write-Host "=" * 70
Write-Host ""

$ErrorsFound = $false

# Patterns that look like secrets (32+ character alphanum strings)
Write-Host "[1/3] Scanning for long alphanumeric strings (potential API keys)..."
$secretPattern = git grep -nE "['\`"]?[A-Za-z0-9]{32,}['\`"]?" -- . `
    ':!external_data/*' `
    ':!*.png' ':!*.jpg' ':!*.jpeg' `
    ':!*.parquet' ':!*.csv' `
    ':!*.md' ':!*.txt' `
    ':!.venv/*' ':!venv/*' `
    ':!htmlcov/*' ':!.pytest_cache/*' `
    ':!*.log' 2>$null

if ($secretPattern) {
    Write-Host "❌ Potential secrets found:" -ForegroundColor Red
    $secretPattern | ForEach-Object {
        # Filter out common false positives
        if ($_ -notmatch 'example|test|dummy|placeholder|sha256|base64' -and
            $_ -notmatch '0{32,}|1{32,}' -and
            $_ -notmatch 'ABCD|abcd' -and
            $_ -notmatch '\.egg-info' -and
            $_ -notmatch 'pyproject\.toml') {
            Write-Host "  $_" -ForegroundColor Yellow
            $ErrorsFound = $true
        }
    }
}
else {
    Write-Host "✅ No long alphanumeric strings found" -ForegroundColor Green
}

Write-Host ""
Write-Host "[2/3] Scanning for hardcoded 'API_KEY' or 'TOKEN' assignments..."
$keyAssignments = git grep -nE "(API_KEY|TOKEN|SECRET|PASSWORD)\s*=\s*['\`"][^'\`"]{8,}" -- . `
    ':!external_data/*' `
    ':!.env.example' `
    ':!scripts/*' `
    ':!*.md' 2>$null

if ($keyAssignments) {
    Write-Host "❌ Hardcoded credentials found:" -ForegroundColor Red
    $keyAssignments | ForEach-Object {
        if ($_ -notmatch 'example|test|your_|change_this') {
            Write-Host "  $_" -ForegroundColor Yellow
            $ErrorsFound = $true
        }
    }
}
else {
    Write-Host "✅ No hardcoded credential assignments found" -ForegroundColor Green
}

Write-Host ""
Write-Host "[3/3] Checking .env files are ignored..."
$envFiles = git ls-files | Select-String -Pattern "^\.env$|^\.env\.local$"

if ($envFiles) {
    Write-Host "❌ .env files tracked in git:" -ForegroundColor Red
    $envFiles | ForEach-Object {
        Write-Host "  $_" -ForegroundColor Yellow
        $ErrorsFound = $true
    }
}
else {
    Write-Host "✅ No .env files tracked in git" -ForegroundColor Green
}

Write-Host ""
Write-Host "=" * 70

if ($ErrorsFound) {
    Write-Host "❌ SECRET SCAN FAILED" -ForegroundColor Red
    Write-Host "Potential secrets detected. Review and fix before committing." -ForegroundColor Red
    exit 1
}
else {
    Write-Host "✅ SECRET SCAN PASSED" -ForegroundColor Green
    Write-Host "No secrets detected. Safe to commit." -ForegroundColor Green
    exit 0
}
