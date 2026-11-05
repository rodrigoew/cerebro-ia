@echo off
chcp 65001 >nul
rem Cria o atalho "Núcleo" na área de trabalho e no menu Iniciar, com o ícone certo e sem janela de console.
cd /d "%~dp0\.."
set PASTA=%CD%
for /f "delims=" %%p in ('where pythonw 2^>nul') do ( set PYW=%%p & goto achou )
for /f "delims=" %%p in ('py -3.12 -c "import sys,os;print(os.path.join(os.path.dirname(sys.executable),'pythonw.exe'))"') do set PYW=%%p
:achou
set PYW=%PYW: =%
powershell -NoProfile -Command ^
  "$w = New-Object -ComObject WScript.Shell;" ^
  "foreach ($d in @([Environment]::GetFolderPath('Desktop'), (Join-Path $env:APPDATA 'Microsoft\Windows\Start Menu\Programs'))) {" ^
  "  $a = $w.CreateShortcut((Join-Path $d 'Núcleo.lnk'));" ^
  "  $a.TargetPath = '%PYW%'; $a.Arguments = '\"%PASTA%\app.py\"'; $a.WorkingDirectory = '%PASTA%';" ^
  "  $a.IconLocation = '%PASTA%\static\icone.ico'; $a.Description = 'Núcleo, seu segundo cérebro'; $a.Save() }"
echo Atalho "Núcleo" criado na área de trabalho e no menu Iniciar.
pause
