#define MyAppName "CouchPotato"
#define MyAppVer "0.5"

[Setup]
AppName={#MyAppName}
AppVersion={#MyAppVer}
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
Name: "{userstartup}\{#MyAppName}"; Filename: "{app}\{#MyAppName}.exe"

[Tasks]
Name: "startup"; Description: "Run {#MyAppName} at startup"; Flags: unchecked