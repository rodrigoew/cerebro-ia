@echo off
chcp 65001 >nul
rem Cria o repositório Git do Núcleo com o FreeLLMAPI como submódulo. Rode uma vez, na pasta do projeto.
cd /d "%~dp0\.."
where git >nul 2>nul || ( echo Instale o Git em git-scm.com e rode de novo. & pause & exit /b 1 )
if not exist .git (
  git init -b main
  git add -A
  git commit -m "Núcleo %date%"
)
if not exist vendor\freellmapi\package.json (
  git submodule add --depth 1 https://github.com/tashfeenahmed/freellmapi vendor/freellmapi
  git commit -m "Adiciona FreeLLMAPI como submódulo"
)
echo.
echo Repositório pronto. Para enviar ao seu GitHub (crie antes um repositório PRIVADO vazio):
echo   git remote add origin https://github.com/SEU_USUARIO/nucleo.git
echo   git push -u origin main
pause
