@echo off
chcp 65001 >nul
rem Adiciona o globo como submodulo do seu repositorio (uma vez), depois instala.
cd /d "%~dp0\.."
where git >nul 2>nul || ( echo Instale o Git e rode de novo. & pause & exit /b 1 )
if not exist vendor\gods-eye-view\package.json (
  git submodule add https://github.com/bilawalsidhu/gods-eye-view vendor/gods-eye-view
  git commit -m "Adiciona God's Eye View como submodulo"
)
call "%~dp0instalar_globo.bat"
echo Nao esqueca de enviar: git push
pause
