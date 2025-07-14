#!/usr/bin/env python3
"""
Check and restart camera server if needed
This script ensures the camera server is running the latest version with camera settings endpoints
"""

import subprocess
import requests
import time
import sys
import os

def check_server_endpoints(host="http://localhost:5000"):
    """Check if the camera settings endpoints are available"""
    try:
        # Test basic endpoint first
        response = requests.get(f"{host}/status", timeout=2)
        if response.status_code != 200:
            print("❌ Server not responding to basic endpoints")
            return False
        
        # Test camera settings endpoint
        response = requests.get(f"{host}/camera_settings", timeout=2)
        if response.status_code == 200:
            print("✅ Camera settings endpoints are available")
            return True
        else:
            print(f"❌ Camera settings endpoints not available (status: {response.status_code})")
            return False
            
    except Exception as e:
        print(f"❌ Error checking endpoints: {e}")
        return False

def restart_server():
    """Restart the camera server"""
    print("🔄 Restarting camera server...")
    
    # Kill existing server
    try:
        subprocess.run(["pkill", "-f", "python3 camera_server.py"], check=False)
        print("   Stopped existing server")
        time.sleep(2)
    except Exception as e:
        print(f"   Warning: Could not stop existing server: {e}")
    
    # Start new server
    try:
        # Get current directory
        current_dir = os.path.dirname(os.path.abspath(__file__))
        
        # Start server in background
        cmd = [
            "bash", "-c", 
            f"cd {current_dir} && source dualcam-venv/bin/activate && python3 camera_server.py"
        ]
        
        # Start in background
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        print("   Started new server")
        time.sleep(3)  # Wait for server to start
        
        return process
        
    except Exception as e:
        print(f"   Error starting server: {e}")
        return None

def main():
    host = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:5000"
    
    print("🔍 Checking camera server status...")
    print(f"   Host: {host}")
    
    # Check if endpoints are available
    if check_server_endpoints(host):
        print("✅ Server is running with camera settings support")
        return
    
    print("❌ Server needs to be restarted with updated code")
    
    # Restart server
    process = restart_server()
    if process is None:
        print("❌ Failed to restart server")
        return
    
    # Wait a bit and check again
    print("⏳ Waiting for server to start...")
    time.sleep(5)
    
    # Check endpoints again
    if check_server_endpoints(host):
        print("✅ Server restarted successfully with camera settings support")
    else:
        print("❌ Server restart failed or endpoints still not available")
        print("   Please check the server logs for errors")

if __name__ == "__main__":
    main() 