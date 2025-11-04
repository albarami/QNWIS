# Git History Secret Purge Script
# CRITICAL: Run this AFTER rotating all exposed keys
# This will rewrite git history - coordinate with team before running

Write-Host "=" * 80 -ForegroundColor Red
Write-Host "CRITICAL: GIT HISTORY SECRET PURGE" -ForegroundColor Red
Write-Host "=" * 80 -ForegroundColor Red
Write-Host ""
Write-Host "This script will REWRITE git history to remove exposed secrets." -ForegroundColor Yellow
Write-Host "This is IRREVERSIBLE and requires force-push." -ForegroundColor Yellow
Write-Host ""

# Check if keys have been rotated
Write-Host "BEFORE PROCEEDING:" -ForegroundColor Cyan
Write-Host "1. Have you rotated the Semantic Scholar API key? (Y/N)" -ForegroundColor Cyan
$rotated = Read-Host

if ($rotated -ne "Y" -and $rotated -ne "y") {
    Write-Host ""
    Write-Host "❌ STOP: Rotate keys first!" -ForegroundColor Red
    Write-Host ""
    Write-Host "Go to: https://www.semanticscholar.org/product/api" -ForegroundColor Yellow
    Write-Host "1. Revoke key: SAYzpCnxTxgayxysRRQM1wwrE7NslFn9uPKT2xy4" -ForegroundColor Yellow
    Write-Host "2. Generate new key" -ForegroundColor Yellow
    Write-Host "3. Add to .env (not .env.example)" -ForegroundColor Yellow
    Write-Host "4. Test with: pytest tests/unit/test_apis_semantic_scholar.py" -ForegroundColor Yellow
    Write-Host ""
    exit 1
}

# Backup check
Write-Host ""
Write-Host "2. Have you backed up your repo? (Y/N)" -ForegroundColor Cyan
$backed = Read-Host

if ($backed -ne "Y" -and $backed -ne "y") {
    Write-Host ""
    Write-Host "❌ STOP: Create backup first!" -ForegroundColor Red
    Write-Host ""
    Write-Host "Run: git clone --mirror https://github.com/albarami/QNWIS.git ../QNWIS-backup" -ForegroundColor Yellow
    Write-Host ""
    exit 1
}

# Team coordination
Write-Host ""
Write-Host "3. Have all team members been notified? (Y/N)" -ForegroundColor Cyan
Write-Host "   (They will need to re-clone after force-push)" -ForegroundColor Gray
$notified = Read-Host

if ($notified -ne "Y" -and $notified -ne "y") {
    Write-Host ""
    Write-Host "⚠️  STOP: Notify team first!" -ForegroundColor Red
    Write-Host ""
    Write-Host "After force-push, team members must:" -ForegroundColor Yellow
    Write-Host "  1. Delete their local copy" -ForegroundColor Yellow
    Write-Host "  2. git clone fresh from GitHub" -ForegroundColor Yellow
    Write-Host ""
    exit 1
}

# Final confirmation
Write-Host ""
Write-Host "=" * 80 -ForegroundColor Red
Write-Host "FINAL CONFIRMATION" -ForegroundColor Red
Write-Host "=" * 80 -ForegroundColor Red
Write-Host ""
Write-Host "This will:" -ForegroundColor Yellow
Write-Host "  - Rewrite entire git history" -ForegroundColor Yellow
Write-Host "  - Remove the file with hardcoded secrets" -ForegroundColor Yellow
Write-Host "  - Require force-push to GitHub" -ForegroundColor Yellow
Write-Host "  - Break all existing clones" -ForegroundColor Yellow
Write-Host ""
Write-Host "Type 'PURGE' to proceed (anything else to cancel):" -ForegroundColor Cyan
$confirm = Read-Host

if ($confirm -ne "PURGE") {
    Write-Host ""
    Write-Host "Cancelled. No changes made." -ForegroundColor Green
    exit 0
}

# Install git-filter-repo if needed
Write-Host ""
Write-Host "Installing git-filter-repo..." -ForegroundColor Cyan
python -m pip install git-filter-repo 2>&1 | Out-Null

if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Failed to install git-filter-repo" -ForegroundColor Red
    exit 1
}

Write-Host "✅ git-filter-repo installed" -ForegroundColor Green

# Create backup just in case
Write-Host ""
Write-Host "Creating local backup..." -ForegroundColor Cyan
$backupDir = "d:\lmis_int_backup_$(Get-Date -Format 'yyyyMMdd_HHmmss')"
Copy-Item -Path "d:\lmis_int" -Destination $backupDir -Recurse -Force
Write-Host "✅ Backup created: $backupDir" -ForegroundColor Green

# Run git-filter-repo to remove files
Write-Host ""
Write-Host "Purging secrets from git history..." -ForegroundColor Cyan
Write-Host "(This may take a few minutes)" -ForegroundColor Gray

# We need to remove the OLD version of semantic_scholar.py that had the key
# The safest approach is to remove the entire file from history, since we've
# already replaced it with a clean version

git filter-repo --force --invert-paths --path src/data/apis/semantic_scholar.py

if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ git-filter-repo failed" -ForegroundColor Red
    Write-Host "Restore from backup: $backupDir" -ForegroundColor Yellow
    exit 1
}

Write-Host "✅ History rewritten successfully" -ForegroundColor Green

# Re-add the clean version
Write-Host ""
Write-Host "Re-adding clean version of semantic_scholar.py..." -ForegroundColor Cyan
git add src/data/apis/semantic_scholar.py
git commit -m "Add sanitized semantic_scholar.py (environment-based auth only)"

Write-Host "✅ Clean version committed" -ForegroundColor Green

# Instructions for force-push
Write-Host ""
Write-Host "=" * 80 -ForegroundColor Green
Write-Host "HISTORY PURGED - READY FOR FORCE PUSH" -ForegroundColor Green
Write-Host "=" * 80 -ForegroundColor Green
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Cyan
Write-Host ""
Write-Host "1. Force-push to GitHub:" -ForegroundColor Yellow
Write-Host "   git push --force --all origin" -ForegroundColor White
Write-Host "   git push --force --tags origin" -ForegroundColor White
Write-Host ""
Write-Host "2. Verify on GitHub that old commits with secrets are gone" -ForegroundColor Yellow
Write-Host ""
Write-Host "3. Notify team to re-clone:" -ForegroundColor Yellow
Write-Host "   rm -rf lmis_int" -ForegroundColor White
Write-Host "   git clone https://github.com/albarami/QNWIS.git lmis_int" -ForegroundColor White
Write-Host ""
Write-Host "4. Monitor for compromised keys:" -ForegroundColor Yellow
Write-Host "   Check Semantic Scholar API usage for unexpected activity" -ForegroundColor White
Write-Host ""
Write-Host "Backup location: $backupDir" -ForegroundColor Gray
Write-Host ""
