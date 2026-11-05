@echo off
chcp 65001 >nul
rem Traz a versão mais recente do FreeLLMAPI, reinstala e registra a mudança no seu repositório.
cd /d "%~dp0\.."
git submodule update --remote --depth 1 vendor/freellmapi || ( echo Falha ao atualizar o submódulo. & pause & exit /b 1 )
call "%~dp0instalar_freellmapi.bat"
cd /d "%~dp0\.."
git add vendor/freellmapi
git commit -m "Atualiza FreeLLMAPI"
echo FreeLLMAPI atualizado. Reinicie o Núcleo para usar a nova versão.
pause
