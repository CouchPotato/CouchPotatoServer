#define MyAppName "CouchPotato"
#define MyAppVer "2.6.3"
#define MyAppBit "win32"
//#define MyAppBit "win-amd64"

[Setup]
AppName={#MyAppName}
AppVersion=2
AppVerName={#MyAppName}
DefaultDirName={userappdata}\{#MyAppName}\application
DisableProgramGroupPage=yes
DisableDirPage=yes
UninstallDisplayIcon=./icon.ico
SetupIconFile=./icon.ico
OutputDir=./dist
OutputBaseFilename={#MyAppName}-{#MyAppVer}.{#MyAppBit}.installer
AppPublisher=Your Mom
AppPublisherURL=http://couchpota.to
PrivilegesRequired=none
WizardSmallImageFile=installer_icon.bmp
WizardImageFile=installer_banner.bmp
UsePreviousAppDir=no

[Messages]
WelcomeLabel1=Installing [name]!
WelcomeLabel2=This wizard will install [name] to your AppData folder. It does this so it can use the build in updater without needing admin rights.

[CustomMessages]
LaunchProgram=Launch {#MyAppName} right now.

[Files]
Source: "./dist/{#MyAppName}-{#MyAppVer}.{#MyAppBit}/*"; Flags: recursesubdirs; DestDir: "{app}"

[Icons]
Name: "{commonprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppName}.exe"
Name: "{userstartup}\{#MyAppName}"; Filename: "{app}\{#MyAppName}.exe"; Tasks: startup

[Tasks]
Name: "startup"; Description: "Run {#MyAppName} at startup"; Flags: unchecked

[Run]
Filename: {app}\{#MyAppName}.exe; Description: {cm:LaunchProgram,{#MyAppName}}; Flags: nowait postinstall skipifsilent


[UninstallDelete]
Type: filesandordirs; Name: "{app}\appdata"
Type: filesandordirs; Name: "{app}\Microsoft.VC90.CRT"
Type: filesandordirs; Name: "{app}\updates"
Type: filesandordirs; Name: "{app}\CouchPotato*"
Type: filesandordirs; Name: "{app}\python27.dll"
Type: filesandordirs; Name: "{app}\unins000.dat"
Type: filesandordirs; Name: "{app}\unins000.exe"
