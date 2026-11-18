@echo off
rem Arranca MEKA Core y los canales (Telegram) en esta ventana. Ciérrala para apagar MEKA.
rem Doble clic, o desde una terminal: scripts\iniciar_meka.cmd   (añade "core" para solo el núcleo)
title MEKA Core
cd /d "%~dp0.."

if not exist "venv\Scripts\python.exe" (
  echo No encuentro el entorno virtual en venv\. Sigue el inicio rapido del README.
  pause
  exit /b 1
)

rem Ollama (el cerebro local): si no esta corriendo, se abre minimizado
tasklist /FI "IMAGENAME eq ollama.exe" 2>nul | find /I "ollama.exe" >nul
if errorlevel 1 (
  where ollama >nul 2>nul && start "Ollama" /min ollama serve
)

"venv\Scripts\python.exe" run.py %*
echo.
echo MEKA se ha detenido.
pause
