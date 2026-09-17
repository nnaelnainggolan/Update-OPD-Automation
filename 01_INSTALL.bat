@echo off
cd /d "%~dp0"
py -3 -m venv .venv
if errorlevel 1 goto failed
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 goto failed
".venv\Scripts\python.exe" -m playwright install chromium
if errorlevel 1 goto failed
echo Instalasi selesai. Buka 02_LOGIN.bat.
pause
exit /b 0
:failed
echo Instalasi gagal. Kirim pesan kesalahan yang tampil.
pause
exit /b 1
