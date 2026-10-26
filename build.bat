@echo off
setlocal
cd /d "%~dp0"
echo === IKA - genera app\IKA.exe (portable, sin instalar Python) ===

if not exist "backend\venv\Scripts\python.exe" (
    py -m venv backend\venv || goto :error
)
backend\venv\Scripts\python.exe -m pip install --quiet -r requirements.txt pyinstaller==6.11.1 || goto :error

if exist "app" rmdir /s /q "app"
backend\venv\Scripts\python.exe -m PyInstaller --noconfirm --onefile --name IKA ^
    --distpath app --workpath build --specpath build ^
    --add-data "%CD%\frontend;frontend" ^
    --add-data "%CD%\backend\schema.sql;." ^
    --paths backend backend\app.py || goto :error

echo.
echo Listo: app\IKA.exe. Usa iniciar.bat para abrir IKA.
goto :eof

:error
echo *** Fallo el build. Revisa el mensaje de arriba. ***
exit /b 1
