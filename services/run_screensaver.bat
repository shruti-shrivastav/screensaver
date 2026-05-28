@echo off
:: Helper script to run Screensaver within Windows Task Scheduler
:: It automatically handles restarts on crashes (non-zero exits) and exits cleanly on exit code 0.

set SCRIPT_DIR=%~dp0
set PROJECT_DIR=%SCRIPT_DIR%..
cd /d "%PROJECT_DIR%"

:loop
:: Check for deterministic stop signal before starting
if exist "service.stop" (
    echo [%date% %time%] Stop signal detected. Cleaning up and exiting loop. >> service_out.log
    del "service.stop" >nul 2>&1
    exit /b 0
)

echo [%date% %time%] Starting Screensaver... >> service_out.log
".venv\Scripts\python.exe" run.py >> service_out.log 2>> service_err.log
set EXIT_CODE=%errorlevel%

echo [%date% %time%] Screensaver exited with code %EXIT_CODE% >> service_out.log

:: Check for deterministic stop signal after python exits
if exist "service.stop" (
    echo [%date% %time%] Stop signal detected. Cleaning up and exiting loop. >> service_out.log
    del "service.stop" >nul 2>&1
    exit /b 0
)

if %EXIT_CODE% equ 0 (
    echo [%date% %time%] Clean exit (0). Stopping. >> service_out.log
    exit /b 0
)

echo [%date% %time%] Abnormal exit (%EXIT_CODE%). Restarting in 5 seconds... >> service_out.log
echo [%date% %time%] Abnormal exit (%EXIT_CODE%). Restarting in 5 seconds... >> service_err.log
timeout /t 5 >nul
goto loop
