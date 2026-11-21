@echo off
chcp 65001 >nul
rem Gera a versão instalável do Núcleo (Windows). Rode a partir da pasta do projeto:  empacotar\empacotar.bat
cd /d "%~dp0\.."
python -m pip install --upgrade pyinstaller -r requirements.txt faster-whisper kokoro-onnx nvidia-cublas-cu12 "nvidia-cudnn-cu12>=9,<10" cryptography
python -m PyInstaller --noconfirm --clean --windowed --name Nucleo --icon static\icone.ico ^
  --add-data "catalogo_fontes.json;." --add-data "interface.html;." --add-data "config.exemplo.json;." --add-data "VERSION;." --add-data "static;static" --add-data "conhecimento;conhecimento" ^
  --collect-all faster_whisper --collect-all ctranslate2 --collect-all kokoro_onnx --collect-all espeakng_loader ^
  --collect-all phonemizer --collect-all onnxruntime --collect-all nvidia --collect-all webview ^
  --collect-all imageio_ffmpeg --collect-all cloudinary --collect-all yt_dlp --collect-all yt_dlp_ejs --hidden-import keyring.backends.Windows app.py
if errorlevel 1 ( echo Falha no PyInstaller. & pause & exit /b 1 )
echo.
echo Pronto: dist\Nucleo\Nucleo.exe
echo Para gerar o instalador, abra empacotar\nucleo.iss no Inno Setup (jrsoftware.org) e clique em Compile.
pause
