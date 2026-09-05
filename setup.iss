; ============================================================
; Inno Setup Script
; Application: Xeon - Scrcpy Controller
; Publisher: AlfandoXeon
; Repository: https://github.com/AlfandoXeon/ScrcpyControllerGUI
; ============================================================

#define MyAppName "Xeon - Scrcpy Controller"
#define MyAppShortName "ScrcpyController"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "AlfandoXeon"
#define MyAppURL "https://github.com/AlfandoXeon/ScrcpyControllerGUI"
#define MyAppExeName "ScrcpyController.exe"
#define MyDistDir "dist\ScrcpyController"
#define MyOutputBaseFilename "XeonScrcpyController_Setup_v" + MyAppVersion

[Setup]
; Unique application GUID
AppId={{8F3A2D1E-4B5C-4D6E-9F7A-1B2C3D4E5F6A}}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} v{#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}/issues
AppUpdatesURL={#MyAppURL}/releases

; Default install location: User Profile Program Files (No Administrator UAC required)
DefaultDirName={autopf}\{#MyAppShortName}
DefaultGroupName={#MyAppName}
AllowNoIcons=yes

; 64-bit Windows configuration
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible

; Permissions: Defaults to current user (lowest), allows user to choose admin if desired
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog

; Output configuration
OutputDir=installer
OutputBaseFilename={#MyOutputBaseFilename}
SetupIconFile=app\resources\icon.ico
UninstallDisplayName={#MyAppName}
UninstallDisplayIcon={app}\{#MyAppExeName}

; Embedded Windows Binary Version & Publisher Information (Windows File Properties)
VersionInfoCompany={#MyAppPublisher}
VersionInfoDescription={#MyAppName} Setup
VersionInfoVersion={#MyAppVersion}.0
VersionInfoCopyright=Copyright (C) 2026 {#MyAppPublisher}
VersionInfoProductName={#MyAppName}
VersionInfoProductVersion={#MyAppVersion}
VersionInfoOriginalFileName={#MyOutputBaseFilename}.exe

; Code Signing Integration (Inno Setup SignTool)
; When a certificate is configured in Inno Setup (Tools -> Configure Sign Tools),
; uncomment SignTool below to automatically sign the installer and uninstaller.
; SignTool=signtool
; SignedUninstaller=yes

; Modern styling and high compression
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
DisableProgramGroupPage=auto

; License agreement presentation
LicenseFile=licenses\LICENSE.txt

; Close running application instances before updating/reinstalling
CloseApplications=yes
RestartApplications=no

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[Files]
; Main distribution directory (onedir build artifacts including _internal and runtime)
Source: "{#MyDistDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\{#MyAppExeName}"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon; IconFilename: "{app}\{#MyAppExeName}"

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
; Clean up runtime-generated files in the installation directory upon uninstall
Type: filesandordirs; Name: "{app}\logs"
Type: filesandordirs; Name: "{app}\config"
Type: filesandordirs; Name: "{app}\runtime"
Type: filesandordirs; Name: "{app}\_internal"
Type: filesandordirs; Name: "{app}\app"
Type: filesandordirs; Name: "{app}\LogoAplikasi"

[Code]
// User settings and data in %APPDATA%\Xeon Scrcpy Controller are intentionally preserved
// upon uninstall to retain user presets and preferences.
