import requests
import json
import sys

# Example config: list of Pi hostnames or IPs
PI_CONFIG = [
    {'name': 'Pi1', 'host': 'http://192.168.1.101:5000'},
    {'name': 'Pi2', 'host': 'http://192.168.1.102:5000'},
]

def list_pis():
    print('Available Raspberry Pis:')
    for idx, pi in enumerate(PI_CONFIG):
        print(f'{idx+1}. {pi["name"]} ({pi["host"]})')

def select_pi():
    list_pis()
    while True:
        try:
            idx = int(input('Select a Pi by number: ')) - 1
            if 0 <= idx < len(PI_CONFIG):
                print(f"[DEBUG] Selected Pi: {PI_CONFIG[idx]['name']} at {PI_CONFIG[idx]['host']}")
                return PI_CONFIG[idx]
            else:
                print('[ERROR] Invalid selection. Try again.')
        except ValueError:
            print('[ERROR] Please enter a valid number.')

def start_recording(pi, duration, fps):
    url = f'{pi["host"]}/start_recording'
    payload = {'duration': duration, 'fps': fps}
    print(f"[DEBUG] Sending start_recording to {url} with payload {payload}")
    try:
        resp = requests.post(url, json=payload, timeout=5)
        resp.raise_for_status()
        print('[INFO] Response:', resp.json())
    except requests.exceptions.ConnectionError:
        print(f'[ERROR] Could not connect to {url}. Is the Pi online?')
    except requests.exceptions.Timeout:
        print(f'[ERROR] Request to {url} timed out.')
    except requests.exceptions.HTTPError as e:
        print(f'[ERROR] HTTP error: {e} - {resp.text}')
    except Exception as e:
        print(f'[ERROR] Unexpected error: {e}')

def stop_recording(pi):
    url = f'{pi["host"]}/stop_recording'
    print(f"[DEBUG] Sending stop_recording to {url}")
    try:
        resp = requests.post(url, timeout=5)
        resp.raise_for_status()
        print('[INFO] Response:', resp.json())
    except requests.exceptions.ConnectionError:
        print(f'[ERROR] Could not connect to {url}. Is the Pi online?')
    except requests.exceptions.Timeout:
        print(f'[ERROR] Request to {url} timed out.')
    except requests.exceptions.HTTPError as e:
        print(f'[ERROR] HTTP error: {e} - {resp.text}')
    except Exception as e:
        print(f'[ERROR] Unexpected error: {e}')

def check_status(pi):
    url = f'{pi["host"]}/status'
    print(f"[DEBUG] Checking status at {url}")
    try:
        resp = requests.get(url, timeout=5)
        resp.raise_for_status()
        status = resp.json()
        print(f"[INFO] Status: {status}")
        return status
    except requests.exceptions.ConnectionError:
        print(f'[ERROR] Could not connect to {url}. Is the Pi online?')
    except requests.exceptions.Timeout:
        print(f'[ERROR] Request to {url} timed out.')
    except requests.exceptions.HTTPError as e:
        print(f'[ERROR] HTTP error: {e} - {resp.text}')
    except Exception as e:
        print(f'[ERROR] Unexpected error: {e}')
    return None

def main():
    print('[DEBUG] Starting PC controller')
    pi = select_pi()
    while True:
        action = input('Enter action (start/stop/status/exit): ').strip().lower()
        if action == 'start':
            try:
                duration = int(input('Enter duration (seconds): '))
                fps = int(input('Enter fps: '))
                print(f"[DEBUG] User input - duration: {duration}, fps: {fps}")
                start_recording(pi, duration, fps)
            except ValueError:
                print('[ERROR] Please enter valid numbers for duration and fps.')
        elif action == 'stop':
            stop_recording(pi)
        elif action == 'status':
            check_status(pi)
        elif action == 'exit':
            print('[DEBUG] Exiting controller.')
            break
        else:
            print('[ERROR] Unknown action. Please enter start, stop, status, or exit.')

if __name__ == '__main__':
    main() 