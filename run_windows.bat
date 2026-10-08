@echo off
setlocal
cd /d "%~dp0"
where py >nul 2>nul
if errorlevel 1 (set "PYTHON_CMD=python") else (set "PYTHON_CMD=py -3")
if not exist ".venv\Scripts\python.exe" (
    %PYTHON_CMD% -m venv .venv
    if errorlevel 1 goto fail
)
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 goto fail
".venv\Scripts\python.exe" manage.py migrate
if errorlevel 1 goto fail
".venv\Scripts\python.exe" manage.py seed_demo
if errorlevel 1 goto fail
echo Open http://127.0.0.1:8000/ in your browser.
echo Demo login: demo / Demo12345!
".venv\Scripts\python.exe" manage.py runserver 127.0.0.1:8000
if errorlevel 1 goto fail
exit /b 0
:fail
echo Setup failed. Read the error above and see README.md.
pause
exit /b 1
