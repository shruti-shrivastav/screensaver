#!/bin/bash
# Script to install Screensaver systemd user service dynamically based on the current path

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
SYSTEMD_USER_DIR="$HOME/.config/systemd/user"
SERVICE_NAME="screensaver.service"
SERVICE_PATH="$SYSTEMD_USER_DIR/$SERVICE_NAME"

echo "==================================================="
echo "Installing Screensaver systemd User Service"
echo "==================================================="

# Verify virtual environment exists
if [ ! -f "$PROJECT_DIR/.venv/bin/python" ]; then
    echo "ERROR: Virtual environment not found at $PROJECT_DIR/.venv/"
    echo "Please create a virtual environment first (python -m venv .venv)"
    exit 1
fi

# Ensure systemd user service directory exists
mkdir -p "$SYSTEMD_USER_DIR"

# Generate the systemd service file dynamically using absolute paths
echo "Generating $SERVICE_NAME dynamically..."
cat <<EOF > "$SERVICE_PATH"
[Unit]
Description=Screensaver AI Solver Service
After=network.target

[Service]
Type=simple
WorkingDirectory=$PROJECT_DIR
ExecStart=$PROJECT_DIR/.venv/bin/python run.py
Restart=on-failure
# Ensure that if we stop cleanly (exit code 0), systemd does not restart the service
RestartPreventExitStatus=0
SuccessExitStatus=0
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=default.target
EOF

# Set permissions
chmod 644 "$SERVICE_PATH"

# Reload systemd to recognize the new service
echo "Reloading systemd user daemon..."
systemctl --user daemon-reload

# Enable the service for startup on login
echo "Enabling service to start automatically on login..."
systemctl --user enable "$SERVICE_NAME"

# Start the service immediately
echo "Starting service immediately..."
systemctl --user start "$SERVICE_NAME"

echo ""
echo "Screensaver service has been installed and started successfully!"
echo "You can check status using: systemctl --user status $SERVICE_NAME"
echo "You can view logs using: journalctl --user -u $SERVICE_NAME -f"
echo "==================================================="
