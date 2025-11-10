param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$ReadinessArgs
)

$ErrorActionPreference = "Stop"
$scriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$root = Get-Item (Join-Path $scriptRoot "..\..")

$env:PYTHONPATH = "$($root.FullName)\src" + ($(if ($env:PYTHONPATH) { ";" + $env:PYTHONPATH } else { "" }))
$env:TZ = "UTC"
$env:LC_ALL = "C"
if (-not $env:PYTHONHASHSEED) {
    $env:PYTHONHASHSEED = "0"
}

python "$($root.FullName)\src\qnwis\scripts\qa\readiness_gate.py" @ReadinessArgs
