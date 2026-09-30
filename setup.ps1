param([string]$Python = 'python')
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
if (-not (Test-Path -LiteralPath '.venv/Scripts/python.exe')) {
    & $Python -m venv .venv
    if ($LASTEXITCODE -ne 0) { throw 'Python 3.11 or later is required.' }
}
& '.\.venv\Scripts\python.exe' -m pip install -e '.[desktop,build]'
if ($LASTEXITCODE -ne 0) { throw 'Dependency installation failed.' }
