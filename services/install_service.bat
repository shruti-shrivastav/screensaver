@echo off
:: Batch script to install Screensaver as a Windows Service using NSSM (Non-Sucking Service Manager)
:: Make sure to run this script as Administrator.

set SERVICE_NAME=Screensaver
set SCRIPT_DIR=%~dp0
set PROJECT_DIR=%SCRIPT_DIR%..
set PYTHON_PATH=%PROJECT_DIR%\.venv\Scripts\python.exe
set RUN_PY=%PROJECT_DIR%\run.py

echo ===================================================
echo Installing %SERVICE_NAME% as a Windows Service
echo ===================================================

:: Check for Administrator privileges
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo ERROR: Please run this script as Administrator!
    pause
    exit /b 1
)

:: Check if NSSM is installed/available in path
where nssm >nul 2>&1
if %errorLevel% neq 0 (
    echo ERROR: NSSM (Non-Sucking Service Manager) was not found in your PATH.
    echo Please download it from https://nssm.cc/download and add it to your PATH.
    pause
    exit /b 1
)

:: Install the service
nssm install %SERVICE_NAME% "%PYTHON_PATH%" "%RUN_PY%"
if %errorLevel% neq 0 (
    echo Failed to install service. It might already be installed.
)

:: Set service properties
nssm set %SERVICE_NAME% AppDirectory "%PROJECT_DIR%"
nssm set %SERVICE_NAME% Description "AI-Powered Screensaver DSA Solver Service"
nssm set %SERVICE_NAME% Start SERVICE_AUTO_START

:: CRITICAL: Configure NSSM AppExit Action
:: Tell NSSM that if the application exits with code 0 (clean stop), it should EXIT (stop the service)
:: rather than restarting it. For all other non-zero exit codes (crashes), it will still restart.
nssm set %SERVICE_NAME% AppExit Default Restart
nssm set %SERVICE_NAME% AppExit 0 Exit

echo.
echo Service %SERVICE_NAME% installed successfully!
echo You can start it using: net start %SERVICE_NAME%
echo You can stop it using: net stop %SERVICE_NAME%
echo.
pause
