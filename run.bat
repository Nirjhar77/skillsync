@echo off
cd /d "%~dp0"
echo ===================================
echo      Starting SkillSync Project
echo ===================================

:: Check if the virtual environment folder exists
IF NOT EXIST ".venv" (
    echo [1/3] Virtual environment not found. Creating .venv...
    python -m venv .venv
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
python app.py

pause
