@echo off
:: Batch script to uninstall Screensaver Windows Service
:: Make sure to run this script as Administrator.

set SERVICE_NAME=Screensaver

echo ===================================================
echo Uninstalling %SERVICE_NAME% Windows Service
echo ===================================================

:: Check for Administrator privileges
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo ERROR: Please run this script as Administrator!
    pause
    exit /b 1
)

:: Check if NSSM is installed
where nssm >nul 2>&1
if %errorLevel% neq 0 (
    echo ERROR: NSSM was not found in your PATH. 
    echo If the service is running, trying to stop and delete it using sc...
    sc stop %SERVICE_NAME% >nul 2>&1
    sc delete %SERVICE_NAME%
    goto end
)

:: Stop the service if running
echo Stopping service %SERVICE_NAME%...
nssm stop %SERVICE_NAME% >nul 2>&1

:: Remove the service
echo Removing service %SERVICE_NAME%...
nssm remove %SERVICE_NAME% confirm
if %errorLevel% neq 0 (
    echo Failed to remove service via NSSM. Trying sc delete...
    sc delete %SERVICE_NAME%
)

:end
echo.
echo Service %SERVICE_NAME% has been uninstalled and cleaned up!
echo.
pause
