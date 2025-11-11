# PowerShell helper function for quick git publish
# Usage: .\scripts\Publish-Changes.ps1 "Step 33: RG-8 PASS — continuity code + artifacts"
# Or add to your PowerShell profile for global access

param(
    [string]$Message = "chore: update"
)

function Publish-Changes {
    param([string]$m = "chore: update")
    
    Write-Host "`n=== Git Publish Helper ===" -ForegroundColor Cyan
    
    # Stage all changes
    Write-Host "`nStaging changes..." -ForegroundColor Yellow
    git add -A
    git status
    
    # Commit
    Write-Host "`nCommitting with message: $m" -ForegroundColor Yellow
    git commit -m $m
    
    # Rebase
    Write-Host "`nRebasing onto origin/main..." -ForegroundColor Yellow
    git pull --rebase origin main
    
    # Push
    Write-Host "`nPushing to origin..." -ForegroundColor Yellow
    git push -u origin HEAD
    
    # Verify
    Write-Host "`n=== Verification ===" -ForegroundColor Cyan
    $localHead = git rev-parse HEAD
    $remoteHead = git rev-parse origin/main
    
    Write-Host "Local HEAD:  " -NoNewline -ForegroundColor Yellow
    Write-Host $localHead
    Write-Host "Remote HEAD: " -NoNewline -ForegroundColor Yellow
    Write-Host $remoteHead
    
    if ($localHead -eq $remoteHead) {
        Write-Host "`n✓ SUCCESS: Local and remote are in sync!" -ForegroundColor Green
    } else {
        Write-Host "`n✗ WARNING: Local and remote differ. Run 'git push' again." -ForegroundColor Red
    }
}

# Run the function with the provided message
Publish-Changes -m $Message
