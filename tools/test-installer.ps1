param([string]$Installer = '', [switch]$IsolatedIdentity)
$ErrorActionPreference = 'Stop'
$projectRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
if (-not $Installer) { $Installer = Join-Path $projectRoot 'dist/Veilbreaker-0.20.0rc1-Setup-x64.exe' }
$artifactRoot = Join-Path $projectRoot 'test-artifacts'
$testRoot = Join-Path $artifactRoot ('installer-' + [Guid]::NewGuid().ToString('N').Substring(0,8))
$installRoot = [IO.Path]::GetFullPath((Join-Path $testRoot 'installer-check'))
if (-not $installRoot.StartsWith($testRoot + '\', [StringComparison]::OrdinalIgnoreCase)) { throw 'Invalid test install path.' }
$testAppName = 'Veilbreaker'
$testAppId = 'E143EBCB-CF84-4D13-A183-1C91B9D3B76D'
if ($IsolatedIdentity) {
    # Same release payload and installer directives, with a separate test identity.
    $testAppName = 'Veilbreaker Validation'
    $testAppId = '07E4818D-E997-4190-8CFE-7622096E521D'
    $compiler = @("$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe", "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe") | Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1
    if (-not $compiler) { throw 'Inno Setup is needed for an isolated identity test.' }
    $validationSource = Join-Path $projectRoot 'installer/.validation.iss'
    $source = Get-Content -LiteralPath (Join-Path $projectRoot 'installer/Veilbreaker.iss') -Raw
    $source = $source.Replace('E143EBCB-CF84-4D13-A183-1C91B9D3B76D', $testAppId).Replace('AppName=Veilbreaker', "AppName=$testAppName").Replace('OutputBaseFilename=Veilbreaker-', 'OutputBaseFilename=VeilbreakerValidation-').Replace('Name: "{autoprograms}\Veilbreaker"', 'Name: "{autoprograms}\Veilbreaker Validation"').Replace('Name: "{autodesktop}\Veilbreaker"', 'Name: "{autodesktop}\Veilbreaker Validation"')
    try {
        $source | Set-Content -LiteralPath $validationSource -Encoding utf8
        & $compiler /Q $validationSource
        if ($LASTEXITCODE -ne 0) { throw 'Validation installer compilation failed.' }
    } finally {
        if (Test-Path -LiteralPath $validationSource) { Remove-Item -LiteralPath $validationSource }
    }
    $Installer = Join-Path $projectRoot 'dist/VeilbreakerValidation-0.20.0rc1-Setup-x64.exe'
}
$registryKey = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\{$testAppId}_is1"
$menuLink = Join-Path ([Environment]::GetFolderPath('Programs')) "$testAppName.lnk"
$desktopLink = Join-Path ([Environment]::GetFolderPath('Desktop')) "$testAppName.lnk"
foreach ($existing in @($registryKey, $menuLink, $desktopLink, $installRoot)) {
    if (Test-Path -LiteralPath $existing) { throw "Refusing to overwrite an existing installation or shortcut: $existing" }
}
New-Item -ItemType Directory -Path $testRoot -Force | Out-Null
$dataRoot = Join-Path $testRoot 'installer-user-data'
New-Item -ItemType Directory -Path $dataRoot -Force | Out-Null
$sentinel = Join-Path $dataRoot 'preserve-me.txt'
'Veilbreaker test data' | Set-Content -LiteralPath $sentinel
$priorDataDir = $env:VEILBREAKER_DATA_DIR
$env:VEILBREAKER_DATA_DIR = $dataRoot
$checks = [Collections.Generic.List[string]]::new()
try {
    $process = Start-Process -FilePath $Installer -ArgumentList @('/VERYSILENT', '/SUPPRESSMSGBOXES', '/NORESTART', '/CURRENTUSER', "/DIR=`"$installRoot`"", '/TASKS=desktopicon', "/LOG=`"$testRoot\installer-test.log`"") -WindowStyle Hidden -PassThru -Wait
    if ($process.ExitCode -ne 0) { throw "Setup failed: $($process.ExitCode)" }
    $exe = Join-Path $installRoot 'VeilbreakerDesktop.exe'
    $cli = Join-Path $installRoot 'veilbreaker.exe'
    $registration = Get-ItemProperty -LiteralPath $registryKey
    if ([IO.Path]::GetFullPath($registration.InstallLocation).TrimEnd('\') -ne $installRoot) { throw 'Unexpected installation registration.' }
    $checks.Add('Per-user install and uninstall registration')
    $shell = New-Object -ComObject WScript.Shell
    foreach ($link in @($menuLink, $desktopLink)) {
        if (-not (Test-Path -LiteralPath $link) -or $shell.CreateShortcut($link).TargetPath -ne $exe) { throw "Missing or incorrect shortcut: $link" }
    }
    $checks.Add('Start menu and optional desktop shortcuts')
    $process = Start-Process -FilePath $cli -ArgumentList 'selftest' -WindowStyle Hidden -PassThru -Wait -RedirectStandardOutput (Join-Path $testRoot 'installed-cli.txt')
    if ($process.ExitCode -ne 0) { throw 'Installed CLI self-test failed.' }
    $process = Start-Process -FilePath $cli -ArgumentList 'init' -WindowStyle Hidden -PassThru -Wait -RedirectStandardOutput (Join-Path $testRoot 'installed-init.txt')
    if ($process.ExitCode -ne 0) { throw 'Installed CLI init failed.' }
    $process = Start-Process -FilePath $exe -ArgumentList @('--smoke-test', "`"$testRoot\installed-gui`"") -WindowStyle Hidden -PassThru -Wait
    if ($process.ExitCode -ne 0 -or -not (Get-Content -LiteralPath (Join-Path $testRoot 'installed-gui/gui-smoke.json') -Raw | ConvertFrom-Json).passed) { throw 'Installed GUI smoke failed.' }
    $checks.Add('Installed CLI and six GUI pages')
    $configHash = (Get-FileHash -LiteralPath (Join-Path $dataRoot 'config.json')).Hash
    $process = Start-Process -FilePath $Installer -ArgumentList @('/VERYSILENT', '/SUPPRESSMSGBOXES', '/NORESTART', '/CURRENTUSER', "/DIR=`"$installRoot`"", '/TASKS=desktopicon') -WindowStyle Hidden -PassThru -Wait
    if ($process.ExitCode -ne 0) { throw 'Reinstall failed.' }
    if ((Get-FileHash -LiteralPath (Join-Path $dataRoot 'config.json')).Hash -ne $configHash) { throw 'Reinstall modified user config.' }
    $checks.Add('Reinstall preserves user configuration')
} finally {
    $env:VEILBREAKER_DATA_DIR = $priorDataDir
    $uninstaller = Join-Path $installRoot 'unins000.exe'
    if (Test-Path -LiteralPath $uninstaller) {
        $process = Start-Process -FilePath $uninstaller -ArgumentList @('/VERYSILENT', '/SUPPRESSMSGBOXES', '/NORESTART', "/LOG=`"$testRoot\uninstaller-test.log`"") -WindowStyle Hidden -PassThru -Wait
        if ($process.ExitCode -ne 0) { throw 'Uninstall failed.' }
    }
}
foreach ($removed in @($registryKey, $menuLink, $desktopLink, (Join-Path $installRoot 'VeilbreakerDesktop.exe'), (Join-Path $installRoot 'veilbreaker.exe'))) {
    if (Test-Path -LiteralPath $removed) { throw "Uninstall left an application component: $removed" }
}
if (-not (Test-Path -LiteralPath $sentinel) -or (Get-FileHash -LiteralPath (Join-Path $dataRoot 'config.json')).Hash -ne $configHash) { throw 'Uninstall altered user data.' }
$checks.Add('Uninstall removes application components and preserves user data')
@{passed=$true; checks=@($checks); installer=[IO.Path]::GetFileName($Installer); isolated_identity=[bool]$IsolatedIdentity; logs=$testRoot} | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $artifactRoot 'installer-report.json') -Encoding utf8
Write-Output 'Installer lifecycle checks passed.'
