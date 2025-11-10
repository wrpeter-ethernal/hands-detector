@echo off
REM ============================================================
REM PYTHON CONFIGURATION
REM ============================================================
REM If Python is not in your PATH, modify the following line
REM with the full path to your Python executable:
REM Example: if exist "C:\Python311\python.exe" (
REM ============================================================

echo ============================================================
echo Starting Hand Detection - Finger Counter...
echo ============================================================
echo.

REM Check if Python 3.11 is available
set PYTHON_CMD=

REM CONFIGURE YOUR PYTHON PATH HERE:
REM Replace "F:\Python-311\python.exe" with your Python installation path
if exist "F:\Python-311\python.exe" (
    "F:\Python-311\python.exe" --version >nul 2>&1
    if %errorlevel% equ 0 (
        set PYTHON_CMD=F:\Python-311\python.exe
        goto :python_found
    )
)

python3.11 --version >nul 2>&1
if %errorlevel% equ 0 (
    set PYTHON_CMD=python3.11
    goto :python_found
)

py -3.11 --version >nul 2>&1
if %errorlevel% equ 0 (
    set PYTHON_CMD=py -3.11
    goto :python_found
)

python --version >nul 2>&1
if %errorlevel% equ 0 (
    for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYTHON_VERSION=%%i
    echo %PYTHON_VERSION% | findstr /R "^3\.11\." >nul
    if %errorlevel% equ 0 (
        set PYTHON_CMD=python
        goto :python_found
    )
)

py --version >nul 2>&1
if %errorlevel% equ 0 (
    for /f "tokens=2" %%i in ('py --version 2^>^&1') do set PYTHON_VERSION=%%i
    echo %PYTHON_VERSION% | findstr /R "^3\.11\." >nul
    if %errorlevel% equ 0 (
        set PYTHON_CMD=py
        goto :python_found
    )
)

echo ERROR: Python 3.11 not found!
echo Please install Python 3.11 or update this script to use your Python version.
echo.
echo Tried commands: F:\Python-311\python.exe, python3.11, py -3.11, python, py
echo.
pause
exit /b 1

:python_found
echo Python 3.11 detected: 
%PYTHON_CMD% --version
echo.

REM Check if required files exist
if not exist "main.py" (
    echo ERROR: main.py not found in current directory!
    echo Make sure you are running this from the project folder.
    echo.
    pause
    exit /b 1
)

echo Starting application...
echo Press Ctrl+C to stop or 'q' in the application window to quit.
echo.

%PYTHON_CMD% main.py

echo.
echo Application closed.
pause

