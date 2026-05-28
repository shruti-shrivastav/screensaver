@echo off
:: Batch script to install Screensaver as a Windows Task Scheduler task
:: Make sure to run this script as Administrator.

set SERVICE_NAME=Screensaver
set SCRIPT_DIR=%~dp0
set PROJECT_DIR=%SCRIPT_DIR%..

echo ===================================================
echo Installing %SERVICE_NAME% as a Windows Task Scheduler Task
echo ===================================================

:: Check for Administrator privileges
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo ERROR: Please run this script as Administrator!
    pause
    exit /b 1
)

:: Step 1: Clean up any old active processes, loop wrappers, and port bindings to prevent conflicts
echo Cleaning up existing active processes and port bindings...

:: Write stop signal file to terminate any existing batch loop cleanly
echo. > "%PROJECT_DIR%\service.stop"

:: Terminate python process using the deterministic PID file
if exist "%PROJECT_DIR%\service.pid" (
    for /f "usebackq" %%a in ("%PROJECT_DIR%\service.pid") do (
        taskkill /f /pid %%a >nul 2>&1
    )
    del "%PROJECT_DIR%\service.pid" >nul 2>&1
)

:: Fallback port-based netstat kill (CRLF-safe)
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

:: Clean up stop signal file if it wasn't cleaned up by the loop
if exist "%PROJECT_DIR%\service.stop" (
    del "%PROJECT_DIR%\service.stop" >nul 2>&1
)

:: Step 2: Clean up any old NSSM service to prevent conflicts
where nssm >nul 2>&1
if %errorLevel% equ 0 (
    echo Stopping and removing existing NSSM service if it exists...
    nssm stop %SERVICE_NAME% >nul 2>&1
    nssm remove %SERVICE_NAME% confirm >nul 2>&1
)

:: Also try sc stop/delete just in case
sc query %SERVICE_NAME% >nul 2>&1
if %errorLevel% equ 0 (
    echo Stopping and removing existing service via sc...
    sc stop %SERVICE_NAME% >nul 2>&1
    sc delete %SERVICE_NAME% >nul 2>&1
)

:: Step 3: Remove any existing Task Scheduler task to prevent duplicates
schtasks /query /tn "%SERVICE_NAME%" >nul 2>&1
if %errorLevel% equ 0 (
    echo Stopping and removing existing Task Scheduler task "%SERVICE_NAME%"...
    schtasks /end /tn "%SERVICE_NAME%" >nul 2>&1
    schtasks /delete /tn "%SERVICE_NAME%" /f >nul 2>&1
)

:: Step 4: Register the task in Windows Task Scheduler
:: We schedule it to run 'onlogon' so it executes in the user's active GUI session,
:: which is critical for successful screen capture operations.
echo Registering new Task Scheduler task...
schtasks /create /tn "%SERVICE_NAME%" /tr "wscript.exe \"%SCRIPT_DIR%run_screensaver.vbs\"" /sc onlogon /rl highest /f

if %errorLevel% neq 0 (
    echo.
    echo ERROR: Failed to register Task Scheduler task.
    pause
    exit /b 1
)

:: Step 5: Run the task immediately so it starts background execution right away
echo Starting task immediately...
schtasks /run /tn "%SERVICE_NAME%"
if %errorLevel% neq 0 (
    echo Warning: Failed to run task immediately.
)

echo.
echo ===================================================
echo Screensaver task successfully registered and started!
echo It will now run automatically whenever you log in.
echo ===================================================
echo.
echo Useful Commands:
echo - Start task:  schtasks /run /tn "%SERVICE_NAME%"
echo - Stop task:   schtasks /end /tn "%SERVICE_NAME%"
echo - Check state: schtasks /query /tn "%SERVICE_NAME%"
echo.
pause