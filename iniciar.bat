@echo off
rem Modo desarrollo: abre IKA con el Python del proyecto, sin consola.
rem Para las laptops usa app\IKA-Instalador.exe (lo genera build.bat).
cd /d "%~dp0"
if exist "backend\venv\Scripts\pythonw.exe" (
    start "" "backend\venv\Scripts\pythonw.exe" "backend\app.py"
) else (
    echo Falta el entorno de desarrollo. Crealo con:
    echo   py -m venv backend\venv
    echo   backend\venv\Scripts\pip install -r requirements.txt
    pause
)
