#!/bin/bash
# Script to uninstall and clean up the Screensaver systemd user service

SYSTEMD_USER_DIR="$HOME/.config/systemd/user"
SERVICE_NAME="screensaver.service"
SERVICE_PATH="$SYSTEMD_USER_DIR/$SERVICE_NAME"

echo "==================================================="
echo "Uninstalling Screensaver systemd User Service"
echo "==================================================="

# Check if the service file exists
if [ ! -f "$SERVICE_PATH" ]; then
    echo "Notice: Service file $SERVICE_PATH was not found. Cleaning up active processes if any..."
else
    # Stop the service if active
    echo "Stopping Screensaver service..."
    systemctl --user stop "$SERVICE_NAME" >/dev/null 2>&1

    # Disable the service
    echo "Disabling Screensaver service..."
    systemctl --user disable "$SERVICE_NAME" >/dev/null 2>&1

    # Remove the service file
    echo "Removing service file..."
    rm -f "$SERVICE_PATH"
fi

# Reload systemd configuration
echo "Reloading systemd user daemon..."
systemctl --user daemon-reload

echo ""
echo "Screensaver service has been uninstalled and cleaned up successfully!"
echo "==================================================="
