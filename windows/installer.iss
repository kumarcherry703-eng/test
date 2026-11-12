#define MyAppName "Setu PC Host"
#define MyAppVersion "0.1.0"
[Setup]
AppId={{66353444-04E0-4378-95CA-BD223BFE49B7}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
DefaultDirName={localappdata}\Programs\SetuHost
DefaultGroupName=Setu
PrivilegesRequired=lowest
OutputDir=..\dist\installer
OutputBaseFilename=SetuHostSetup
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
UninstallDisplayIcon={app}\SetuHost.exe
[Files]
Source: "..\dist\SetuHost\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
[Icons]
Name: "{group}\Setu PC Host"; Filename: "{app}\SetuHost.exe"
Name: "{autodesktop}\Setu PC Host"; Filename: "{app}\SetuHost.exe"; Tasks: desktopicon
[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; Flags: unchecked
[Run]
Filename: "{app}\SetuHost.exe"; Description: "Open Setu PC Host"; Flags: nowait postinstall skipifsilent
