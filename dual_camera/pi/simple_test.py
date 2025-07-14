#!/usr/bin/env python3
"""
Simple test to debug URL encoding issue
"""

import requests
import urllib.parse

def test_url_encoding():
    host = "http://192.168.2.11:5000"
    device = "/dev/video0"
    
    print(f"Testing device: {device}")
    
    # Test different encoding methods
    encodings = [
        ("No encoding", device),
        ("quote with safe=''", urllib.parse.quote(device, safe='')),
        ("quote with safe='/'", urllib.parse.quote(device, safe='/')),
        ("quote_plus", urllib.parse.quote_plus(device)),
    ]
    
    for name, encoded in encodings:
        print(f"\n--- {name} ---")
        print(f"Encoded: {encoded}")
        
        try:
            url = f"{host}/camera_properties?device={encoded}"
            print(f"URL: {url}")
            
            response = requests.get(url, timeout=5)
            print(f"Status: {response.status_code}")
            
            if response.status_code == 200:
                print("✅ SUCCESS!")
                properties = response.json().get('properties', {})
                print(f"Found {len(properties)} properties")
            else:
                print(f"❌ Error: {response.text}")
                
        except Exception as e:
            print(f"❌ Exception: {e}")

if __name__ == "__main__":
    test_url_encoding() 