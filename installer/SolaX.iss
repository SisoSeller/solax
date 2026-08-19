#define MyAppName "SolaX"
#define MyAppVersion "1.1.3"
#define MyAppPublisher "KAPPA"
#define MyAppURL "https://sisoseller.github.io/solax/"
#define MyAppExeName "SolaX.exe"

[Setup]
AppId={{8F3C1A2B-4D5E-4670-8192-A3B4C5D6E7F8}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={localappdata}\SolaX
DefaultGroupName=SolaX
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
OutputDir=..\dist
OutputBaseFilename=SolaX-Setup
SetupIconFile=..\website\icon.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
CloseApplications=force
RestartApplications=no

[Languages]
Name: "italian"; MessagesFile: "compiler:Languages\Italian.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Crea un'icona sul desktop"; GroupDescription: "Icone:"

[Files]
Source: "..\dist\SolaX\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\SolaX"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\SolaX Auto"; Filename: "{app}\SolaX Auto.exe"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{userdesktop}\SolaX"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Avvia SolaX"; Flags: nowait postinstall skipifsilent
