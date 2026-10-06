#ifndef AppVersion
  #define AppVersion "0.20.0rc1"
#endif
[Setup]
AppId={{E143EBCB-CF84-4D13-A183-1C91B9D3B76D}
AppName=Veilbreaker
AppVersion={#AppVersion}
AppPublisher=Outpost Relay
DefaultDirName={localappdata}\Programs\Veilbreaker
DefaultGroupName=Veilbreaker
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0
OutputDir=..\dist
OutputBaseFilename=Veilbreaker-{#AppVersion}-Setup-x64
SetupIconFile=..\src\veilbreaker\assets\app.ico
UninstallDisplayIcon={app}\VeilbreakerDesktop.exe
WizardStyle=modern
Compression=lzma2
SolidCompression=yes
CloseApplications=yes
RestartApplications=no
[Tasks]
Name: "desktopicon"; Description: "Create a &desktop shortcut"; GroupDescription: "Shortcuts:"; Flags: unchecked
[Files]
Source: "..\dist\Veilbreaker\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
[Icons]
Name: "{autoprograms}\Veilbreaker"; Filename: "{app}\VeilbreakerDesktop.exe"; WorkingDir: "{app}"; AppUserModelID: "OutpostRelay.Veilbreaker"
Name: "{autodesktop}\Veilbreaker"; Filename: "{app}\VeilbreakerDesktop.exe"; WorkingDir: "{app}"; Tasks: desktopicon; AppUserModelID: "OutpostRelay.Veilbreaker"
[Run]
Filename: "{app}\VeilbreakerDesktop.exe"; Description: "Launch Veilbreaker"; Flags: nowait postinstall skipifsilent
