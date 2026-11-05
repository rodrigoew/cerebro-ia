; Instalador do Núcleo (Inno Setup 6). Gere antes a pasta dist\Nucleo com empacotar.bat.
#define Versao "1.0.0"
[Setup]
AppId={{6E1C5B1E-3A1D-4F7B-9B27-NUCLEO000001}
AppName=Núcleo
AppVersion={#Versao}
AppPublisher=Seu nome
DefaultDirName={autopf}\Nucleo
DefaultGroupName=Núcleo
OutputDir=..\dist
OutputBaseFilename=Nucleo-{#Versao}-instalador
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
LicenseFile=..\documentos\LICENCA_DE_USO.md
PrivilegesRequired=lowest
[Languages]
Name: "pt"; MessagesFile: "compiler:Languages\BrazilianPortuguese.isl"
[Files]
Source: "..\dist\Nucleo\*"; DestDir: "{app}"; Flags: recursesubdirs ignoreversion
Source: "..\documentos\*"; DestDir: "{app}\documentos"; Flags: ignoreversion
[Icons]
Name: "{group}\Núcleo"; Filename: "{app}\Nucleo.exe"
Name: "{autodesktop}\Núcleo"; Filename: "{app}\Nucleo.exe"; Tasks: atalho
[Tasks]
Name: "atalho"; Description: "Criar atalho na área de trabalho"
[Run]
Filename: "{app}\Nucleo.exe"; Description: "Abrir o Núcleo agora"; Flags: nowait postinstall skipifsilent
