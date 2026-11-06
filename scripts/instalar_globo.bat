@echo off
chcp 65001 >nul
rem Instala o globo 3D ao vivo (God's Eye View). Precisa do Node.js 24 (nodejs.org, versão LTS).
cd /d "%~dp0\..\vendor\gods-eye-view" 2>nul || ( echo Rode antes: git submodule update --init vendor/gods-eye-view & pause & exit /b 1 )
where node >nul 2>nul || ( echo Instale o Node.js LTS em nodejs.org e rode de novo. & pause & exit /b 1 )
echo Baixando dependencias do globo (alguns minutos)...
call npm ci || call npm install
if errorlevel 1 ( echo Falha ao baixar as dependencias. & pause & exit /b 1 )
echo.
echo Instalado. No Nucleo, va em Ajustes ^> Globo ao vivo e ligue.
echo Dica: para o 3D fotorrealista, pegue um token gratuito da Cesium ion e cole no painel POWER UP do globo.
pause
