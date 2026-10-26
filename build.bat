@echo off
setlocal
cd /d "%~dp0"
echo === IKA - genera el instalador para Windows ===

if not exist "backend\venv\Scripts\python.exe" (
    py -m venv backend\venv || goto :error
)
set PY=backend\venv\Scripts\python.exe
%PY% -m pip install --quiet -r requirements.txt pyinstaller==6.11.1 || goto :error

if exist "app" rmdir /s /q "app"
if exist "build" rmdir /s /q "build"

echo [1/3] Programa (carpeta app\IKA)...
%PY% -m PyInstaller --noconfirm --log-level WARN --onedir --windowed --name IKA ^
    --icon "%CD%\instalador\ika.ico" ^
    --distpath app --workpath build\ika --specpath build ^
    --add-data "%CD%\frontend;frontend" ^
    --add-data "%CD%\backend\schema.sql;." ^
    --paths backend backend\app.py || goto :error

echo [2/3] Empaquetando...
%PY% -c "import shutil; shutil.make_archive('build/IKA', 'zip', 'app/IKA')" || goto :error
copy /y NUL "app\IKA\portable.txt" >nul
%PY% -c "import shutil; shutil.make_archive('app/IKA-Portable', 'zip', 'app', 'IKA')" || goto :error
del "app\IKA\portable.txt"

echo [3/3] Instalador (app\IKA-Instalador.exe)...
%PY% -m PyInstaller --noconfirm --log-level WARN --onefile --windowed --name IKA-Instalador ^
    --icon "%CD%\instalador\ika.ico" ^
    --distpath app --workpath build\instalador --specpath build ^
    --add-data "%CD%\build\IKA.zip;." ^
    --paths backend instalador\instalar.py || goto :error

echo.
echo Listo:
echo   app\IKA-Instalador.exe   para instalar en cualquier laptop con Windows
echo   app\IKA-Portable.zip     para usar desde USB sin instalar
goto :eof

:error
echo *** Fallo el build. Revisa el mensaje de arriba. ***
exit /b 1
