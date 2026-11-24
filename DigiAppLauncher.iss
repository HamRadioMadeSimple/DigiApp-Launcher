; DigiApp Launcher - Windows installer (Inno Setup 6)
; build_windows.bat compiles this into  output\DigiAppLauncher-<version>-Setup.exe
; Installs into  C:\Program Files\DigiApp Launcher  (asks for administrator permission, like most programs).
; Profiles live in %APPDATA%\DigiApp Launcher and are kept on update or uninstall.

#define MyAppName "DigiApp Launcher"
#ifndef MyAppVersion
  #define MyAppVersion "1.3.3"
#endif
#define MyAppExe "DigiAppLauncher.exe"
#define MyAppUserModelID "DigiApp.Launcher"

[Setup]
AppId={{6B0E7C2A-4D1F-4E7B-9C3A-DA16A0C0F3B1}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher=Ham Radio Made Simple (KW3KW)
AppPublisherURL=https://hamradiomadesimple.github.io/
AppSupportURL=https://github.com/HamRadioMadeSimple/DigiApp-Launcher/issues
AppUpdatesURL=https://github.com/HamRadioMadeSimple/DigiApp-Launcher/releases/latest
DefaultDirName={autopf}\DigiApp Launcher
DisableDirPage=yes
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
PrivilegesRequired=admin
OutputDir=output
OutputBaseFilename=DigiAppLauncher-{#MyAppVersion}-Setup
SetupIconFile=icon.ico
UninstallDisplayIcon={app}\{#MyAppExe}
UninstallDisplayName={#MyAppName}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
CloseApplications=yes
RestartApplications=no

[Tasks]
Name: "desktopicon"; Description: "Put a DigiApp Launcher icon on the desktop (click it to launch your default profile)"; GroupDescription: "Icons:"
Name: "editicon"; Description: "Put a DigiApp Launcher - Edit icon on the desktop (changes your apps without launching any)"; GroupDescription: "Icons:"

[Files]
Source: "dist\{#MyAppExe}"; DestDir: "{app}"; Flags: ignoreversion
Source: "dev\README-Windows.txt"; DestDir: "{app}"; DestName: "README.txt"; Flags: ignoreversion
Source: "docs\DigiApp-Launcher-Guide.pdf"; DestDir: "{app}"; Flags: ignoreversion skipifsourcedoesntexist

[Icons]
; Start menu and desktop icons are for all users of the PC.
; The AppUserModelID ties the shortcut to the program's taskbar button and its right-click profile list.
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExe}"; Parameters: "--run"; \
    WorkingDir: "{app}"; Comment: "Launch your default radio apps profile"; AppUserModelID: "{#MyAppUserModelID}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExe}"; Parameters: "--run"; \
    WorkingDir: "{app}"; Comment: "Launch your default radio apps profile"; AppUserModelID: "{#MyAppUserModelID}"; \
    Tasks: desktopicon
; "DigiApp Launcher - Edit": opens the editor only (no --run), so apps can be changed without launching any
Name: "{autoprograms}\{#MyAppName} - Edit"; Filename: "{app}\{#MyAppExe}"; \
    WorkingDir: "{app}"; Comment: "Edit your apps and profiles (does not open any apps)"
Name: "{autodesktop}\{#MyAppName} - Edit"; Filename: "{app}\{#MyAppExe}"; \
    WorkingDir: "{app}"; Comment: "Edit your apps and profiles (does not open any apps)"; \
    Tasks: editicon

[Run]
; runasoriginaluser: opens the program as the signed-in user (not the admin account), so profiles
; are saved in that user's own %APPDATA%\DigiApp Launcher.
Filename: "{app}\{#MyAppExe}"; Description: "Open DigiApp Launcher to set up your apps"; \
    Flags: nowait postinstall skipifsilent runasoriginaluser

[UninstallDelete]
; icons the program itself may have created with its "Desktop Icon" button
Type: files; Name: "{userdesktop}\{#MyAppName}.lnk"
Type: files; Name: "{userprograms}\{#MyAppName}.lnk"
Type: files; Name: "{userdesktop}\{#MyAppName} - Edit.lnk"
Type: files; Name: "{userprograms}\{#MyAppName} - Edit.lnk"

[Messages]
FinishedLabel=DigiApp Launcher is installed.%n%nTo pin it: right-click the DigiApp Launcher icon on the desktop or in the Start menu > Pin to taskbar. Then click it to launch your default profile, or right-click it for your other profiles and Close Open Apps. Use the DigiApp Launcher - Edit icon to change your apps without launching them.
