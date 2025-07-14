#!/bin/bash
# Restart camera server with URL path fixes

echo "🔄 Restarting camera server with URL path fixes..."

# Stop existing server
echo "   Stopping existing server..."
pkill -f "python3 camera_server.py"
sleep 2

# Start new server
echo "   Starting updated server..."
cd /home/$(whoami)/dual_camera/dual_camera/pi
source dualcam-venv/bin/activate
python3 camera_server.py 