#!/bin/bash
# Restart camera server script

echo "Stopping camera server..."
pkill -f "python3 camera_server.py"

echo "Waiting for server to stop..."
sleep 2

echo "Starting camera server..."
cd /home/$(whoami)/dual_camera/dual_camera/pi
source dualcam-venv/bin/activate
python3 camera_server.py & 