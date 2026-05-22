@echo off
cd /d "%~dp0"
echo ===================================
echo      Starting SkillSync Project
echo ===================================

:: ── Try to use the Python Launcher (py.exe) to bypass Microsoft Store aliases ──
set PY_CMD=py -3
where py >nul 2>nul
if %errorlevel% neq 0 (
    echo [INFO] Python Launcher 'py' not found, falling back to 'python' command.
    set PY_CMD=python
)

:: Check if the virtual environment folder exists
IF NOT EXIST ".venv" (
    echo [1/3] Virtual environment not found. Creating .venv...
    %PY_CMD% -m venv .venv
)

echo [2/3] Activating virtual environment and verifying dependencies...
call .venv\Scripts\activate.bat
pip install -r requirements.txt

echo [3/3] Setup complete!

:: Check if .env file exists
IF NOT EXIST ".env" (
    echo.
    echo WARNING: .env file not found! 
    echo Please make sure you have created a .env file with your GROQ_API_KEY.
    echo.
)

echo.
echo Starting the application...
echo Opening browser to http://127.0.0.1:5000
start http://127.0.0.1:5000
.venv\Scripts\python.exe app.py

pause
