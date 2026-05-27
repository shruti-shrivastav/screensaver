# Screensaver AI Service Configurations

This directory contains configuration templates and automated scripts to deploy and remove the Screensaver AI solver as a resilient background service on both Linux and Windows.

These service setups are fully compatible with the manual **Stop** and **Restart** buttons in the web UI.

---

## 🐧 Linux (systemd User Service)

Running the application as a **systemd user service** allows it to start automatically when your user logs in, run in the background, and automatically restart if it crashes—all without requiring root/sudo privileges.

### 🚀 Automated Install

A one-click bash script is provided to dynamically generate the service file using your current absolute directory paths and launch the background service:

```bash
# Make sure you are in the project root directory
./services/install_service.sh
```

### 🧹 Automated Uninstall & Cleanup

To stop, disable, and completely remove the service configuration:

```bash
./services/uninstall_service.sh
```

### 📊 Service Management

* **Check status**:
  ```bash
  systemctl --user status screensaver.service
  ```
* **View live logs**:
  ```bash
  journalctl --user -u screensaver.service -f
  ```
* **Stop service manually**:
  ```bash
  systemctl --user stop screensaver.service
  ```
* **Restart service manually**:
  ```bash
  systemctl --user restart screensaver.service
  ```

---

## 🪟 Windows (NSSM Service)

NSSM (Non-Sucking Service Manager) allows you to run the Python application as a standard Windows background service that automatically restarts on crashes.

### Prerequisites

1. Download NSSM from [https://nssm.cc/download](https://nssm.cc/download).
2. Extract `nssm.exe` (use the 64-bit version) and add its directory to your Windows System **PATH** environment variable.

### 🚀 Automated Install

1. Open a Command Prompt or PowerShell window **as Administrator**.
2. Navigate to the `services` directory and run:
   ```cmd
   install_service.bat
   ```

### 🧹 Automated Uninstall & Cleanup

1. Open a Command Prompt or PowerShell window **as Administrator**.
2. Navigate to the `services` directory and run:
   ```cmd
   uninstall_service.bat
   ```

### 📊 Service Management

* **Start service**:
  ```cmd
  net start Screensaver
  ```
* **Stop service**:
  ```cmd
  net stop Screensaver
  ```

---

## 💡 How the Stop/Restart Compatibility Works

The backend Stop/Restart code is built to integrate seamlessly with these service managers using native Python signals and exit codes:

* **UI Restart Button**: Re-executes the python process cleanly using `os.execv`. Since the process image is replaced internally, the PID remains identical. The service manager (systemd or NSSM) does not even see a process exit, guaranteeing a smooth and instant restart.
* **UI Stop Button**: Sends a native `SIGTERM` to Uvicorn for clean ASGI lifespan cleanup (stopping tunnels, database saves), then falls back to a clean exit (`os._exit(0)`). Because the exit is clean (exit code `0`), both systemd (`Restart=on-failure`) and NSSM (`AppExit 0 Exit`) recognize this as an intentional shutdown and stop the service instead of restarting it.
* **Resilience (Crashes)**: If the server ever encounters a runtime exception or unhandled crash, it exits with a non-zero exit code. Both service managers will immediately relaunch it.
