; Inno Setup Script
; Xeon - Scrcpy Controller
; Version: 1.0.0

#define MyAppName "Xeon - Scrcpy Controller"
#define MyAppShortName "ScrcpyController"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "AlfandoXeon"
#define MyAppURL "https://alfandoxeon.freedev.app"
#define MyAppExeName "ScrcpyController.exe"
#define MyDistDir "dist\ScrcpyController"

[Setup]
AppId={{8F3A2D1E-4B5C-4D6E-9F7A-1B2C3D4E5F6A}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={autopf}\{#MyAppShortName}
DefaultGroupName={#MyAppName}
AllowNoIcons=yes
; Do not require admin — install to Program Files but user config goes to AppData
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
OutputDir=installer
OutputBaseFilename=XeonScrcpyController_Setup_v{#MyAppVersion}
SetupIconFile=app\resources\icon.ico
Compression=lzma
SolidCompression=yes
WizardStyle=modern
DisableProgramGroupPage=auto
; Show license if present
LicenseFile=licenses\LICENSE.txt

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop shortcut"; GroupDescription: "Additional icons:"

[Files]
; Main application files
Source: "{#MyDistDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\{#MyAppExeName}"
Name: "{group}\Uninstall {#MyAppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon; IconFilename: "{app}\{#MyAppExeName}"

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Launch {#MyAppName}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
; Remove logs and config only from install dir (AppData config is preserved)
Type: filesandordirs; Name: "{app}\logs"

[Code]
// Preserve user configuration in AppData on uninstall
// (AppData folder is not touched — it belongs to the user)
