; HeyClone Windows installer (Inno Setup 6 script).
;
; Build with Inno Setup 6 (https://jrsoftware.org/isinfo.php):
;   compile this file  ->  produces  HeyClone-setup-0.1.0.exe
;
; Prerequisite: Python 3.9+ must be installed on the target machine.
; The installer bundles the source and runs install.py to create the venv.

#define MyAppName "HeyClone"
#define MyAppVersion "0.1.0"
#define MyAppPublisher "HeyClone"

[Setup]
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={localappdata}\{#MyAppName}
DefaultGroupName={#MyAppName}
OutputDir=..\..\build\windows
OutputBaseFilename=HeyClone-setup-{#MyAppVersion}
Compression=lzma2
SolidCompression=yes
ArchitecturesInstallIn64BitMode=x64compatible
PrivilegesRequired=lowest
WizardStyle=modern

[Files]
; Bundle the project source, excluding transient dirs.
Source: "..\..\*"; DestDir: "{app}\src"; \
  Excludes: "\.git,\.venv,\.install-test,__pycache__,*.pyc,*.egg-info,build,dist,*.iss"; \
  Flags: recursesubdirs createallsubdirs

[Run]
; Create the virtual environment and install (idempotent).
Filename: "{cmd}"; Parameters: "/C python ""{app}\src\install.py"" --dir ""{app}"""; \
  StatusMsg: "Installing HeyClone..."; Flags: runhidden

[UninstallDelete]
Type: filesanddirs; Name: "{app}"
