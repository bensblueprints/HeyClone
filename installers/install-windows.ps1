# HeyClone Windows installer (launcher for install.py)
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$Installer = Join-Path $Root "install.py"

$python = Get-Command python -ErrorAction SilentlyContinue
if ($python) {
    & python $Installer @args
    exit $LASTEXITCODE
}

$py = Get-Command py -ErrorAction SilentlyContinue
if ($py) {
    & py -3 $Installer @args
    exit $LASTEXITCODE
}

Write-Error "Python 3.9+ is required. Install it from https://www.python.org and re-run."
exit 1
