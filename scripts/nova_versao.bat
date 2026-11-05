@echo off
chcp 65001 >nul
rem Publica uma nova versão: atualiza VERSION, faz commit, cria a tag e (se quiser) envia ao GitHub.
cd /d "%~dp0\.."
set /p ATUAL=<VERSION
echo Versão atual: %ATUAL%
echo Lembrete: anote as mudanças no CHANGELOG.md antes de continuar.
set /p NOVA=Nova versão (ex.: 0.9.1): 
if "%NOVA%"=="" ( echo Nada feito. & pause & exit /b 0 )
> VERSION echo %NOVA%
git add -A
git commit -m "Versão %NOVA%"
git tag -a v%NOVA% -m "Versão %NOVA%"
set /p ENVIAR=Enviar ao GitHub agora? (s/n): 
if /i "%ENVIAR%"=="s" ( git push && git push --tags )
echo Versão %NOVA% criada.
pause
