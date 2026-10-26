@echo off
title IKA - MR INFRATEC
cd /d "%~dp0"

rem Si IKA ya esta abierta, solo abre el navegador.
powershell -NoProfile -Command "try { (Invoke-WebRequest -UseBasicParsing -TimeoutSec 1 http://localhost:4580/api/ajustes) | Out-Null; exit 0 } catch { exit 1 }" >nul 2>&1
if %errorlevel%==0 (
    start "" http://localhost:4580
    exit /b
)

start "" /min cmd /c "timeout /t 2 >nul & start "" http://localhost:4580"

if exist "app\IKA.exe" (
    "app\IKA.exe"
) else if exist "backend\venv\Scripts\python.exe" (
    "backend\venv\Scripts\python.exe" "backend\app.py"
) else (
    echo No se encontro app\IKA.exe ni el entorno de desarrollo.
    echo Corre build.bat una vez, o crea el entorno con:
    echo   py -m venv backend\venv
    echo   backend\venv\Scripts\pip install -r requirements.txt
    pause
)
