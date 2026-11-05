@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo Instalando os componentes do Resumo da Manha...
where python >nul 2>nul
if errorlevel 1 (
  echo Nao encontrei o Python. Instale o Python 3.12 em python.org, marcando "Add Python to PATH", e rode de novo.
  pause
  exit /b 1
)
python -m pip install --upgrade -r requirements.txt
if errorlevel 1 (
  echo A instalacao dos pacotes basicos falhou. Veja a mensagem acima.
  pause
  exit /b 1
)
python app.py --instalar
echo.
echo Pronto. Copie config.exemplo.json para config.json, preencha e use iniciar.bat.
pause
