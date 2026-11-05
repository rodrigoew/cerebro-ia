@echo off
chcp 65001 >nul
rem Envia o Núcleo para o seu repositório no GitHub. Rode uma vez; depois use nova_versao.bat.
cd /d "%~dp0\.."
where git >nul 2>nul || ( echo Instale o Git em git-scm.com e rode de novo. & pause & exit /b 1 )
if not exist .git call "%~dp0preparar_git.bat"
git remote get-url origin >nul 2>nul
if errorlevel 1 git remote add origin https://github.com/rodrigoew/cerebro-ia.git
git add -A
git commit -m "Nucleo" 2>nul
git branch -M main
echo.
echo Enviando para github.com/rodrigoew/cerebro-ia ...
echo (O GitHub vai pedir seu usuario e um token. Veja scripts\COMO_TOKEN.txt)
git push -u origin main
if errorlevel 1 ( echo.& echo Falhou. Confira o token e se o repositorio esta vazio. & pause & exit /b 1 )
echo.
echo Pronto! Deixe o repositorio PRIVADO: github.com/rodrigoew/cerebro-ia ^> Settings ^> Danger Zone.
pause
