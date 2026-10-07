param([string]$Compiler = '', [switch]$SkipBuild, [switch]$AllowUntested, [string]$Python = '.\.venv\Scripts\python.exe')
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
if (-not $SkipBuild) {
    & "$PSScriptRoot\build-release.ps1"
    if ($LASTEXITCODE -ne 0) { throw 'Release build failed.' }
}
if (-not $Compiler) {
    $Compiler = @("$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe", "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe") | Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1
}
if (-not $Compiler) { throw 'Inno Setup 6 is required. Supply -Compiler with the ISCC.exe path.' }
$releaseVersion = & $Python -c 'from veilbreaker import __version__; print(__version__)'
if ($LASTEXITCODE -ne 0) { throw 'Cannot read application version.' }
$manifest = Get-Content -LiteralPath 'dist/Veilbreaker/build-manifest.json' -Raw | ConvertFrom-Json
if ((-not $manifest.passed -and -not $AllowUntested) -or $manifest.version -ne $releaseVersion) { throw 'A verified build of this version is required.' }
& $Compiler "/DAppVersion=$releaseVersion" 'installer/Veilbreaker.iss'
if ($LASTEXITCODE -ne 0) { throw 'Installer compilation failed.' }
$installerPath = Join-Path $PSScriptRoot "dist/Veilbreaker-$releaseVersion-Setup-x64.exe"
$hash = (Get-FileHash -LiteralPath $installerPath -Algorithm SHA256).Hash.ToLower()
"$hash  $([IO.Path]::GetFileName($installerPath))" | Set-Content -LiteralPath "$installerPath.sha256" -Encoding ascii
Write-Output "Installer created: $installerPath"
