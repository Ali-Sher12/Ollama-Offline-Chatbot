@echo off
echo ==========================================================
echo   Ollama Desktop Chatbot - Automated Installation (Windows)
echo ==========================================================

REM Check Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python is not installed or not in PATH.
    echo Please install Python 3.10 or newer from python.org and check "Add Python to PATH".
    pause
    exit /b 1
)

REM Create virtual environment
if not exist ".venv" (
    echo Creating virtual environment in .venv...
    python -m venv .venv
) else (
    echo Existing virtual environment detected.
)

REM Activate virtual environment
call .venv\Scripts\activate.bat

echo Installing dependencies from requirements.txt...
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

REM Check Ollama
echo Checking Ollama...
where ollama >nul 2>&1
if %errorlevel% equ 0 (
    echo [OK] Ollama is installed.
) else (
    echo [NOTE] Ollama command not found. Install from https://ollama.com if using local models.
)

echo.
echo ==========================================================
echo   Installation complete!
echo   Launch the application by running run.bat
echo ==========================================================
pause
