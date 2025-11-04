# scripts/secret_scan.ps1
# Purpose: Scan working tree for patterns resembling secrets with allowlist support.

Param(
  [string[]]$ExcludeGlobs = @("external_data/*", "*.png", "*.jpg", "*.jpeg", "*.parquet", "*.db", "*.sqlite", "*.sqlite3"),
  [string]$AllowlistFile = "scripts/secret_scan_allowlist.txt"
)

Write-Host ("=" * 70)
Write-Host "QNWIS SECRET SCANNER"
Write-Host ("=" * 70)
Write-Host "Exit codes: 0=CLEAN, 1=FLAGGED" -ForegroundColor Cyan

$global:HAS_ISSUES = $false

function Get-AllowlistPatterns {
  param([string]$Path)
  if (-not (Test-Path $Path)) { return @() }
  $lines = Get-Content -Path $Path
  $patterns = @()
  foreach ($line in $lines) {
    $trimmed = $line.Trim()
    if (-not $trimmed) { continue }
    if ($trimmed.StartsWith("#")) { continue }
    $patterns += [regex]::new($trimmed, [System.Text.RegularExpressions.RegexOptions]::IgnoreCase)
  }
  return $patterns
}

function Test-Allowlisted {
  param(
    [string]$Text,
    [System.Text.RegularExpressions.Regex[]]$Patterns
  )
  foreach ($regex in $Patterns) {
    if ($regex.IsMatch($Text)) { return $true }
  }
  return $false
}

function Show-FlaggedDiff {
  param([string[]]$Entries)
  foreach ($entry in $Entries) {
    if (-not $entry) { continue }
    $parts = $entry -split ":", 3
    if ($parts.Length -ge 3) {
      $file = $parts[0]
      $lineNo = $parts[1]
      $content = $parts[2].Trim()
      Write-Host ("@@ {0}:{1} @@" -f $file, $lineNo) -ForegroundColor Yellow
      Write-Host ("+ {0}" -f $content) -ForegroundColor Yellow
    } else {
      Write-Host ("+ {0}" -f $entry.Trim()) -ForegroundColor Yellow
    }
  }
}

function Get-WildcardMatchers {
  param([string[]]$Patterns)
  $options = [System.Management.Automation.WildcardOptions]::IgnoreCase
  return $Patterns | ForEach-Object { [System.Management.Automation.WildcardPattern]::new($_, $options) }
}

function Test-ExcludedPath {
  param(
    [string]$Path,
    [System.Management.Automation.WildcardPattern[]]$Matchers
  )
  foreach ($pattern in $Matchers) {
    if ($pattern.IsMatch($Path)) { return $true }
  }
  return $false
}

# Load allowlist patterns once
$allowPatterns = Get-AllowlistPatterns -Path $AllowlistFile
if ($allowPatterns.Count -gt 0) {
  Write-Host ""
  Write-Host "Loaded $($allowPatterns.Count) allowlist patterns from $AllowlistFile"
}

$excludeMatchers = Get-WildcardMatchers -Patterns $ExcludeGlobs

# 1. Check for long alphanumeric sequences (potential API keys)
Write-Host ""
$gitExe = "git"
$gitExists = Get-Command $gitExe -ErrorAction SilentlyContinue
if (-not $gitExists) {
  Write-Host "ERROR: git executable not found in PATH." -ForegroundColor Red
  exit 2
}

Write-Host "[1/3] Scanning for long alphanumeric strings (potential API keys)..."
$rawMatches = & $gitExe grep -nE "([A-Za-z0-9]{32,})" -- . 2>$null
$flagged = @()

foreach ($line in $rawMatches) {
  $split = $line -split ":", 3
  if ($split.Length -lt 2) { continue }
  $relPath = $split[0]
  if (Test-ExcludedPath -Path $relPath -Matchers $excludeMatchers) { continue }
  if (Test-Allowlisted -Text $line -Patterns $allowPatterns) { continue }
  $flagged += $line
}

if ($flagged.Count -gt 0) {
    Write-Host "WARNING: Found potential secret-like strings:" -ForegroundColor Red
    Show-FlaggedDiff -Entries $flagged
    $global:HAS_ISSUES = $true
}

# 2. Check for common secret patterns
Write-Host ""
Write-Host "[2/3] Scanning for common secret patterns (API_KEY=, token=, etc.)..."
$pattern2 = @'
(api_key|apikey|secret|token|password)\s*=\s*['"`"][^'"`"]{8,}
'@.Trim()
$rawMatches2 = & $gitExe grep -nEi $pattern2 -- . 2>$null
$flagged2 = @()

foreach ($line in $rawMatches2) {
  $split = $line -split ":", 3
  if ($split.Length -lt 2) { continue }
  $relPath = $split[0]
  if (Test-ExcludedPath -Path $relPath -Matchers $excludeMatchers) { continue }
  if (Test-Allowlisted -Text $line -Patterns $allowPatterns) { continue }
  $flagged2 += $line
}

if ($flagged2.Count -gt 0) {
    Write-Host "WARNING: Found potential hardcoded secrets:" -ForegroundColor Red
    Show-FlaggedDiff -Entries $flagged2
    $global:HAS_ISSUES = $true
}

# 3. Check for files that should not be committed
Write-Host ""
Write-Host "[3/3] Checking for sensitive files..."
$SensitiveFiles = @(".env", ".env.local", "*.pem", "*.key", "secrets/*.json")
$found = @()
foreach ($pattern in $SensitiveFiles) {
    $files = & $gitExe ls-files $pattern 2>$null
    if ($files) {
        $found += $files
    }
}
if ($found) {
    Write-Host "ERROR: Sensitive files found in repository:" -ForegroundColor Red
    foreach ($f in $found) {
        Write-Host "  $f" -ForegroundColor Yellow
    }
    $global:HAS_ISSUES = $true
}

# Final result
Write-Host ""
Write-Host ("=" * 70)
if ($global:HAS_ISSUES) {
    Write-Host "Secret scan: ISSUES FOUND" -ForegroundColor Red
    Write-Host ("=" * 70)
    exit 1
} else {
    Write-Host "Secret scan: CLEAN" -ForegroundColor Green
    Write-Host ("=" * 70)
    exit 0
}
