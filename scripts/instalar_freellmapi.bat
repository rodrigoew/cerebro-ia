@echo off
chcp 65001 >nul
rem Instala o FreeLLMAPI local (precisa do Node.js 20 a 24: nodejs.org, versão LTS).
cd /d "%~dp0\..\vendor\freellmapi" 2>nul || ( echo Rode antes scripts\preparar_git.bat. & pause & exit /b 1 )
where node >nul 2>nul || ( echo Instale o Node.js LTS em nodejs.org e rode de novo. & pause & exit /b 1 )
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\dev-bootstrap.ps1
if errorlevel 1 ( echo O bootstrap do FreeLLMAPI falhou. Veja a mensagem acima. & pause & exit /b 1 )
call npm run build
if errorlevel 1 ( echo A compilação do FreeLLMAPI falhou. & pause & exit /b 1 )
echo.
echo Instalado. Próximos passos:
echo  1. Abra o Núcleo e vá em Ajustes ^> Nuvem ^> "Usar FreeLLMAPI" (ele inicia o roteador).
echo  2. Abra o painel em http://localhost:3001, crie a conta local, cadastre as chaves dos provedores gratuitos
echo     e copie a "unified key" (freellmapi-...).
echo  3. No Núcleo, cole essa chave em Ajustes ^> Nuvem ^> Chave da API e clique em Salvar e depois em Testar conexão.
pause
