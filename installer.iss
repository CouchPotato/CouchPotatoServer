#define MyAppName "CouchPotato"
#define MyAppVer GetFileVersion("./dist/"+MyAppName+".exe")

[Setup]
AppName={#MyAppName}
AppVersion={#MyAppVer}
AppVerName={#MyAppName}
DefaultDirName={pf}\{#MyAppName}
DisableProgramGroupPage=yes
UninstallDisplayIcon={app}\icon.ico
OutputDir=./dist
OutputBaseFilename={#MyAppName}-{#MyAppVer}.win32.installer
AppPublisher=Your Mom
AppPublisherURL=http://couchpota.to

[Files]
Source: "./*"; DestDir: "{app}"

[Icons]
Name: "{commonprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppName}.exe"
Name: "{userstartup}\{#MyAppName}"; Filename: "{app}\{#MyAppName}.exe"

[Tasks]
Name: "startup"; Description: "Run {#MyAppName} at startup"; Flags: unchecked