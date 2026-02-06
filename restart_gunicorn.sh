#!/bin/bash
# Script to restart Gunicorn for Jenkins deployment

APP_DIR="/opt/goodall/wiki_for_adaptation/src/mysite"
LOG_DIR="/opt/goodall/wiki_for_adaptation/logs"
PID_FILE="/opt/goodall/wiki_for_adaptation/gunicorn.pid"

cd "$APP_DIR"

# Stop existing Gunicorn using PID file if it exists
if [ -f "$PID_FILE" ]; then
    echo "Stopping Gunicorn using PID file..."
    OLD_PID=$(cat "$PID_FILE" 2>/dev/null)
    if [ -n "$OLD_PID" ]; then
        kill -TERM "$OLD_PID" 2>/dev/null || true
        sleep 3
        # Force kill if still running
        if ps -p "$OLD_PID" > /dev/null 2>&1; then
            echo "Process still running, forcing kill..."
            kill -9 "$OLD_PID" 2>/dev/null || true
        fi
    fi
    rm -f "$PID_FILE"
else
    echo "No PID file found, checking for running processes..."
fi

# Backup: kill any remaining gunicorn processes
pkill -f 'gunicorn.*mysite.wsgi' || true
sleep 2

# Create logs directory
mkdir -p "$LOG_DIR"

# Start Gunicorn with daemon flag
echo "Starting Gunicorn..."
/opt/miniforge/envs/goodall/bin/gunicorn mysite.wsgi:application \
    --bind 0.0.0.0:8080 \
    --workers 4 \
    --timeout 120 \
    --forwarded-allow-ips="*" \
    --access-logfile "$LOG_DIR/gunicorn-access.log" \
    --error-logfile "$LOG_DIR/gunicorn-error.log" \
    --log-level warning \
    --capture-output \
    --pid "$PID_FILE" \
    --daemon

sleep 2

# Verify it started
if [ -f "$PID_FILE" ] && ps -p $(cat "$PID_FILE") > /dev/null 2>&1; then
    echo "Gunicorn started successfully with PID $(cat $PID_FILE)"
    echo "Check configuration at: https://trackadapt.org/debug-settings/"
    exit 0
else
    echo "ERROR: Gunicorn failed to start"
    cat "$LOG_DIR/gunicorn-error.log" 2>/dev/null || echo "No error log found"
    exit 1
fi
