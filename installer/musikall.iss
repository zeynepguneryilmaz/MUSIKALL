; ============ MUSIKALL Installer Script ============
; Inno Setup 6.x

[Setup]
AppId={{F4B8A6D2-7C4D-4A3B-9A7E-3C2A4E1B9D21}}
AppName=MUSIKALL
AppVersion=1.0.0
AppVerName=MUSIKALL 1.0.0
AppPublisher=Ö. Zeynep Güner Yılmaz
AppPublisherURL=https://github.com/zeynepguneryilmaz

DefaultDirName={autopf}\MUSIKALL
PrivilegesRequired=admin
ArchitecturesInstallIn64BitMode=x64

DefaultGroupName=MUSIKALL
OutputDir={#SourcePath}\output
OutputBaseFilename=MUSIKALL_Setup
Compression=lzma
SolidCompression=yes
WizardStyle=modern

; icon paths MUST be absolute-relative to script location
SetupIconFile={#SourcePath}\icon.ico
UninstallDisplayIcon={app}\MUSIKALL.exe

CloseApplications=yes
RestartApplications=no
DisableProgramGroupPage=yes

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Files]
; PyInstaller output folder - always resolve relative to THIS .iss file
Source: "{#SourcePath}\dist\MUSIKALL\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

; icon.ico (for shortcuts) - only needed if not already inside dist\MUSIKALL
Source: "{#SourcePath}\icon.ico"; DestDir: "{app}"; Flags: ignoreversion

[Tasks]
Name: "desktopicon"; Description: "Create a desktop icon"; GroupDescription: "Additional icons:"; Flags: unchecked

[Icons]
Name: "{group}\MUSIKALL"; Filename: "{app}\MUSIKALL.exe"; IconFilename: "{app}\icon.ico"
Name: "{commondesktop}\MUSIKALL"; Filename: "{app}\MUSIKALL.exe"; IconFilename: "{app}\icon.ico"; Tasks: desktopicon

[Run]
Filename: "{app}\MUSIKALL.exe"; Description: "Launch MUSIKALL"; Flags: nowait postinstall skipifsilent; WorkingDir: "{app}"
