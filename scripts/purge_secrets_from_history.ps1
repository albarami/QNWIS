# scripts/purge_secrets_from_history.ps1
# Purpose: remove sensitive files/paths from Git history using git filter-repo.
# NOTE: Example values below are NOT real secrets — they include hyphens/underscores and are short.

param(
  [string]$RepoPath = ".",
  [string[]]$PathsToRemove = @(".env", ".env.txt", "secrets/*.json")
)

Write-Host ">>> Purging secrets from history in $RepoPath" -ForegroundColor Yellow
Write-Host ""

# Example (non-secret) tokens for demonstration only:
$EXAMPLE_OPENAI_KEY    = "sk-EXAMPLE-KEY"           # short, contains hyphen
$EXAMPLE_SEM_SCHOLAR   = "EXAMPLE_KEY_123"          # short, contains underscore + digits
$EXAMPLE_DESC          = "These are demo placeholders only."

# Safety check: ensure git-filter-repo is installed
git filter-repo --help *> $null
if ($LASTEXITCODE -ne 0) {
  Write-Error "git-filter-repo not installed. Please 'pip install git-filter-repo'."
  exit 1
}

# Remove paths from history
$pathsArgs = @()
foreach ($p in $PathsToRemove) {
  $pathsArgs += @("--path", $p)
}

# Invert-paths removes those paths entirely from history
git -C $RepoPath filter-repo --force --invert-paths @pathsArgs

Write-Host ">>> History purge complete. Force-push required." -ForegroundColor Green
Write-Host ">>> Example placeholders: $EXAMPLE_OPENAI_KEY, $EXAMPLE_SEM_SCHOLAR" -ForegroundColor DarkGray
