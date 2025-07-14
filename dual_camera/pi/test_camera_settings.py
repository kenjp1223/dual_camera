#!/usr/bin/env python3
"""
Test script for camera settings endpoints
Run this on the Pi to test if the camera settings endpoints are working
"""

import requests
import json
import sys

def test_endpoints(host="http://localhost:5000"):
    """Test all camera settings endpoints"""
    
    print(f"Testing camera settings endpoints on {host}")
    print("=" * 50)
    
    # Test 1: List cameras
    print("\n1. Testing /cameras endpoint...")
    try:
        response = requests.get(f"{host}/cameras", timeout=5)
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            cameras = response.json().get('cameras', [])
            print(f"Found {len(cameras)} cameras:")
            for cam in cameras:
                print(f"  - {cam['device']} (working: {cam.get('working', False)})")
        else:
            print(f"Error: {response.text}")
    except Exception as e:
        print(f"Error: {e}")
    
    # Test 2: Get camera properties for first camera
    print("\n2. Testing /camera_properties endpoint...")
    try:
        response = requests.get(f"{host}/cameras", timeout=5)
        if response.status_code == 200:
            cameras = response.json().get('cameras', [])
            if cameras:
                device = cameras[0]['device']
                print(f"Testing properties for {device}...")
                
                # URL encode the device path
                import urllib.parse
                encoded_device = urllib.parse.quote(device, safe='')
                
                response = requests.get(f"{host}/camera_properties/{encoded_device}", timeout=5)
                print(f"Status: {response.status_code}")
                if response.status_code == 200:
                    properties = response.json().get('properties', {})
                    print(f"Found {len(properties)} properties:")
                    for prop, value in properties.items():
                        print(f"  - {prop}: {value}")
                else:
                    print(f"Error: {response.text}")
            else:
                print("No cameras found to test")
        else:
            print("Could not get camera list")
    except Exception as e:
        print(f"Error: {e}")
    
    # Test 3: Get camera settings
    print("\n3. Testing /camera_settings endpoint...")
    try:
        response = requests.get(f"{host}/cameras", timeout=5)
        if response.status_code == 200:
            cameras = response.json().get('cameras', [])
            if cameras:
                device = cameras[0]['device']
                print(f"Testing settings for {device}...")
                
                # URL encode the device path
                import urllib.parse
                encoded_device = urllib.parse.quote(device, safe='')
                
                response = requests.get(f"{host}/camera_settings/{encoded_device}", timeout=5)
                print(f"Status: {response.status_code}")
                if response.status_code == 200:
                    settings = response.json().get('settings', {})
                    print(f"Found {len(settings)} saved settings:")
                    for setting, value in settings.items():
                        print(f"  - {setting}: {value}")
                else:
                    print(f"Error: {response.text}")
            else:
                print("No cameras found to test")
        else:
            print("Could not get camera list")
    except Exception as e:
        print(f"Error: {e}")
    
    # Test 4: Get all camera settings
    print("\n4. Testing /camera_settings (all) endpoint...")
    try:
        response = requests.get(f"{host}/camera_settings", timeout=5)
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            all_settings = response.json().get('settings', {})
            print(f"Found settings for {len(all_settings)} devices:")
            for device, settings in all_settings.items():
                print(f"  - {device}: {len(settings)} settings")
        else:
            print(f"Error: {response.text}")
    except Exception as e:
        print(f"Error: {e}")
    
    # Test 5: Test setting camera properties
    print("\n5. Testing setting camera properties...")
    try:
        response = requests.get(f"{host}/cameras", timeout=5)
        if response.status_code == 200:
            cameras = response.json().get('cameras', [])
            if cameras:
                device = cameras[0]['device']
                print(f"Testing setting properties for {device}...")
                
                # URL encode the device path
                import urllib.parse
                encoded_device = urllib.parse.quote(device, safe='')
                
                # Test setting brightness to 128
                test_settings = {'brightness': 128}
                response = requests.post(
                    f"{host}/camera_settings/{encoded_device}",
                    json={'settings': test_settings},
                    timeout=5
                )
                print(f"Status: {response.status_code}")
                if response.status_code == 200:
                    print("Successfully set camera settings")
                else:
                    print(f"Error: {response.text}")
            else:
                print("No cameras found to test")
        else:
            print("Could not get camera list")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    host = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:5000"
    test_endpoints(host) 