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

## 🪟 Windows (Native Task Scheduler)

Windows Task Scheduler allows you to run the Python application as a standard Windows background task scheduled to run at logon (`onlogon`). This runs in your active GUI session context, which is ideal and necessary for seamless screen capture, and does not require third-party service managers like NSSM. 

To prevent any command prompt windows from popping up, the task is executed via a lightweight VBScript wrapper (`run_screensaver.vbs`), making it run completely hidden in the background.

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

* **Start task**:
  ```cmd
  schtasks /run /tn "Screensaver"
  ```
* **Stop task**:
  ```cmd
  schtasks /end /tn "Screensaver"
  ```
* **Check status**:
  ```cmd
  schtasks /query /tn "Screensaver"
  ```

---

## 💡 How the Stop/Restart Compatibility Works

The backend Stop/Restart code is built to integrate seamlessly with these service/task managers using native Python signals and exit codes:

* **UI Restart Button**: Re-executes the python process cleanly using `os.execv`. Since the process image is replaced internally, the PID remains identical. The service/task manager (systemd or Task Scheduler) does not even see a process exit, guaranteeing a smooth and instant restart.
* **UI Stop Button**: Sends a native `SIGTERM` to Uvicorn for clean ASGI lifespan cleanup (stopping tunnels, database saves), then falls back to a clean exit (`os._exit(0)`). Because the exit is clean (exit code `0`), both systemd (`RestartPreventExitStatus=0`) and our custom Windows Task Scheduler wrapper (`run_screensaver.bat`) recognize this as an intentional shutdown and exit cleanly instead of restarting.
* **Resilience (Crashes)**: If the server ever encounters a runtime exception or unhandled crash, it exits with a non-zero exit code. Both service/task managers (via systemd or the `run_screensaver.bat` crash recovery loop) will automatically relaunch it after a brief delay.
