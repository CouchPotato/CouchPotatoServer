#define MyAppName "CouchPotato"
#define MyAppVer "2.0.7"

[Setup]
AppName={#MyAppName}
AppVersion=2
AppVerName={#MyAppName}
DefaultDirName={pf}\{#MyAppName}
DisableProgramGroupPage=yes
UninstallDisplayIcon=./icon.ico
SetupIconFile=./icon.ico
OutputDir=./dist
OutputBaseFilename={#MyAppName}-{#MyAppVer}.win32.installer
AppPublisher=Your Mom
AppPublisherURL=http://couchpota.to

[Files]
Source: "./dist/{#MyAppName}-{#MyAppVer}.win32/*"; Flags: recursesubdirs; DestDir: "{app}"

[Icons]
Name: "{commonprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppName}.exe"
Name: "{userstartup}\{#MyAppName}"; Filename: "{app}\{#MyAppName}.exe"; Tasks: startup

[Tasks]
Name: "startup"; Description: "Run {#MyAppName} at startup"; Flags: unchecked

[UninstallDelete]
Type: filesandordirs; Name: "{app}\appdata"
Type: filesandordirs; Name: "{app}\Microsoft.VC90.CRT"
Type: filesandordirs; Name: "{app}\updates"
Type: filesandordirs; Name: "{app}\CouchPotato*"
Type: filesandordirs; Name: "{app}\python27.dll"
Type: filesandordirs; Name: "{app}\unins000.dat"
Type: filesandordirs; Name: "{app}\unins000.exe"
