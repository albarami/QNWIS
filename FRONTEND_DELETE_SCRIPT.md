# 🗑️ Frontend Deletion Script

**WARNING**: This will permanently delete the current frontend.  
**Backup**: Current frontend has bugs, but save it just in case.

---

## Step 1: Backup Current Frontend (Optional)

```powershell
# Create backup
Copy-Item -Path "d:\lmis_int\qnwis-ui" -Destination "d:\lmis_int\qnwis-ui-backup-$(Get-Date -Format 'yyyyMMdd-HHmmss')" -Recurse

# Verify backup
Get-ChildItem "d:\lmis_int\qnwis-ui-backup-*"
```

---

## Step 2: Stop Frontend Server

```powershell
# Find and stop frontend process
$frontend = Get-NetTCPConnection -LocalPort 3000 -State Listen -ErrorAction SilentlyContinue
if ($frontend) {
    Stop-Process -Id $frontend.OwningProcess -Force
    Write-Host "✅ Frontend stopped" -ForegroundColor Green
} else {
    Write-Host "✅ Frontend not running" -ForegroundColor Gray
}
```

---

## Step 3: Delete Frontend Directory

```powershell
# Delete completely
Remove-Item -Path "d:\lmis_int\qnwis-ui" -Recurse -Force -ErrorAction SilentlyContinue

# Verify deletion
if (!(Test-Path "d:\lmis_int\qnwis-ui")) {
    Write-Host "✅ Frontend deleted successfully" -ForegroundColor Green
} else {
    Write-Host "❌ Frontend still exists - check permissions" -ForegroundColor Red
}
```

---

## Step 4: Clean Status

```powershell
Write-Host "`n╔════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║  Frontend Deletion Complete               ║" -ForegroundColor Cyan
Write-Host "╚════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""
Write-Host "✅ Old frontend deleted" -ForegroundColor Green
Write-Host "✅ Ready for fresh build" -ForegroundColor Green
Write-Host "✅ Backend still running" -ForegroundColor Green
Write-Host ""
Write-Host "Next: Create new frontend with Vite" -ForegroundColor Yellow
```

---

## Complete Script (All-in-One)

```powershell
# Complete deletion script
Write-Host "🗑️ Deleting old frontend..." -ForegroundColor Yellow
Write-Host ""

# Stop frontend
$frontend = Get-NetTCPConnection -LocalPort 3000 -State Listen -ErrorAction SilentlyContinue
if ($frontend) {
    Stop-Process -Id $frontend.OwningProcess -Force
    Write-Host "✅ Stopped frontend server" -ForegroundColor Green
}

# Optional backup
$backup = Read-Host "Create backup first? (y/n)"
if ($backup -eq 'y') {
    $backupName = "qnwis-ui-backup-$(Get-Date -Format 'yyyyMMdd-HHmmss')"
    Copy-Item -Path "d:\lmis_int\qnwis-ui" -Destination "d:\lmis_int\$backupName" -Recurse
    Write-Host "✅ Backup created: $backupName" -ForegroundColor Green
}

# Delete
Remove-Item -Path "d:\lmis_int\qnwis-ui" -Recurse -Force -ErrorAction SilentlyContinue
Start-Sleep -Seconds 2

# Verify
if (!(Test-Path "d:\lmis_int\qnwis-ui")) {
    Write-Host "✅ Frontend deleted successfully" -ForegroundColor Green
    Write-Host "✅ Ready for fresh build" -ForegroundColor Green
} else {
    Write-Host "❌ Deletion failed - check permissions" -ForegroundColor Red
    exit 1
}
```

---

**Save this as**: `d:\lmis_int\delete-frontend.ps1`  
**Run with**: `powershell -ExecutionPolicy Bypass -File delete-frontend.ps1`
