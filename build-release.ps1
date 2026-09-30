$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
& '.\.venv\Scripts\python.exe' 'tools/build_release.py'
if ($LASTEXITCODE -ne 0) { throw 'Release build failed.' }
