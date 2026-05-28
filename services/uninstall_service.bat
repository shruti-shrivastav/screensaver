@echo off
:: Batch script to uninstall Screensaver Windows Task Scheduler task
:: Make sure to run this script as Administrator.

set SERVICE_NAME=Screensaver
set SCRIPT_DIR=%~dp0
set PROJECT_DIR=%SCRIPT_DIR%..

echo ===================================================
echo Uninstalling %SERVICE_NAME% Windows Service / Task
echo ===================================================

:: Check for Administrator privileges
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo ERROR: Please run this script as Administrator!
    pause
    exit /b 1
)

:: Step 1: Write stop signal file to terminate the batch loop cleanly
echo. > "%PROJECT_DIR%\service.stop"

:: Step 2: Stop and delete the Task Scheduler task
echo Stopping Screensaver task in Task Scheduler...
schtasks /end /tn "%SERVICE_NAME%" >nul 2>&1
schtasks /delete /tn "%SERVICE_NAME%" /f >nul 2>&1

:: Step 3: Terminate python process using the deterministic PID file
if exist "%PROJECT_DIR%\service.pid" (
    echo Terminating running Screensaver background server...
    for /f "usebackq" %%a in ("%PROJECT_DIR%\service.pid") do (
        taskkill /f /pid %%a >nul 2>&1
    )
    del "%PROJECT_DIR%\service.pid" >nul 2>&1
)

:: Step 4: Fallback port-based netstat kill (CRLF-safe)
set TARGET_PORT=9090
if exist "%PROJECT_DIR%\.env" (
    for /f "usebackq tokens=1,2 delims==" %%i in ("%PROJECT_DIR%\.env") do (
        if "%%i"=="PORT" (
            set TARGET_PORT=%%j
        )
    )
)
:: Clean up carriage returns (\r) and spaces from target port
set TARGET_PORT=%TARGET_PORT: =%
for /f "delims=0123456789" %%a in ("%TARGET_PORT%") do (
    set TARGET_PORT=%TARGET_PORT:%%a=%
)

:: Run port-based taskkill as fallback
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :%TARGET_PORT%') do (
    taskkill /f /pid %%a >nul 2>&1
)

:: Step 5: Clean up any old NSSM service just in case
where nssm >nul 2>&1
if %errorLevel% equ 0 (
    echo Checking for old NSSM service to clean up...
    nssm stop %SERVICE_NAME% >nul 2>&1
    nssm remove %SERVICE_NAME% confirm >nul 2>&1
)

sc query %SERVICE_NAME% >nul 2>&1
if %errorLevel% equ 0 (
    echo Removing service from sc...
    sc stop %SERVICE_NAME% >nul 2>&1
    sc delete %SERVICE_NAME% >nul 2>&1
)

:: Clean up stop signal file if it wasn't cleaned up by the loop
if exist "%PROJECT_DIR%\service.stop" (
    del "%PROJECT_DIR%\service.stop" >nul 2>&1
)

echo.
echo ===================================================
echo Screensaver task has been uninstalled and cleaned up!
echo ===================================================
echo.
pause