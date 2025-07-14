from flask import Flask, request, jsonify, send_file
import subprocess
import threading
import os
import cv2
import tempfile
from datetime import datetime
import glob
import json

app = Flask(__name__)
recording_process = None

# Camera settings storage
CAMERA_SETTINGS_FILE = 'camera_settings.json'

def load_camera_settings():
    """Load camera settings from JSON file"""
    if os.path.exists(CAMERA_SETTINGS_FILE):
        try:
            with open(CAMERA_SETTINGS_FILE, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading camera settings: {e}")
    return {}

def save_camera_settings(settings):
    """Save camera settings to JSON file"""
    try:
        with open(CAMERA_SETTINGS_FILE, 'w') as f:
            json.dump(settings, f, indent=2)
        return True
    except Exception as e:
        print(f"Error saving camera settings: {e}")
        return False

def get_camera_properties(device):
    """Get available camera properties for a device"""
    try:
        print(f"DEBUG: Opening camera with device: '{device}'")
        
        # Try to convert device path to index if it's a /dev/video* path
        if device.startswith('/dev/video'):
            try:
                device_index = int(device.replace('/dev/video', ''))
                print(f"DEBUG: Converting to device index: {device_index}")
                cap = cv2.VideoCapture(device_index)
            except ValueError:
                print(f"DEBUG: Could not convert device path to index, using path directly")
                cap = cv2.VideoCapture(device)
        else:
            cap = cv2.VideoCapture(device)
            
        if not cap.isOpened():
            print(f"DEBUG: Failed to open camera '{device}'")
            return None
        
        properties = {}
        
        # Common camera properties
        prop_mapping = {
            'exposure': cv2.CAP_PROP_EXPOSURE,
            'gain': cv2.CAP_PROP_GAIN,
            'brightness': cv2.CAP_PROP_BRIGHTNESS,
            'contrast': cv2.CAP_PROP_CONTRAST,
            'saturation': cv2.CAP_PROP_SATURATION,
            'hue': cv2.CAP_PROP_HUE,
            'white_balance_blue_u': cv2.CAP_PROP_WHITE_BALANCE_BLUE_U,
            'white_balance_red_v': cv2.CAP_PROP_WHITE_BALANCE_RED_V,
            'gamma': cv2.CAP_PROP_GAMMA,
            'backlight': cv2.CAP_PROP_BACKLIGHT,
            'auto_exposure': cv2.CAP_PROP_AUTO_EXPOSURE,
            'auto_gain': cv2.CAP_PROP_GAIN,
            'focus': cv2.CAP_PROP_FOCUS,
            'auto_focus': cv2.CAP_PROP_AUTOFOCUS,
            'zoom': cv2.CAP_PROP_ZOOM,
            'pan': cv2.CAP_PROP_PAN,
            'tilt': cv2.CAP_PROP_TILT,
            'roll': cv2.CAP_PROP_ROLL,
            'iris': cv2.CAP_PROP_IRIS,
            'settings': cv2.CAP_PROP_SETTINGS
        }
        
        for name, prop_id in prop_mapping.items():
            try:
                value = cap.get(prop_id)
                if value != -1:  # -1 usually means property not supported
                    properties[name] = value
            except:
                pass
        
        cap.release()
        return properties
    except Exception as e:
        print(f"Error getting camera properties for {device}: {e}")
        return None

def set_camera_properties(device, properties):
    """Set camera properties for a device"""
    try:
        print(f"DEBUG: Setting properties for device: '{device}'")
        
        # Try to convert device path to index if it's a /dev/video* path
        if device.startswith('/dev/video'):
            try:
                device_index = int(device.replace('/dev/video', ''))
                print(f"DEBUG: Converting to device index: {device_index}")
                cap = cv2.VideoCapture(device_index)
            except ValueError:
                print(f"DEBUG: Could not convert device path to index, using path directly")
                cap = cv2.VideoCapture(device)
        else:
            cap = cv2.VideoCapture(device)
            
        if not cap.isOpened():
            print(f"DEBUG: Failed to open camera '{device}' for setting properties")
            return False
        
        prop_mapping = {
            'exposure': cv2.CAP_PROP_EXPOSURE,
            'gain': cv2.CAP_PROP_GAIN,
            'brightness': cv2.CAP_PROP_BRIGHTNESS,
            'contrast': cv2.CAP_PROP_CONTRAST,
            'saturation': cv2.CAP_PROP_SATURATION,
            'hue': cv2.CAP_PROP_HUE,
            'white_balance_blue_u': cv2.CAP_PROP_WHITE_BALANCE_BLUE_U,
            'white_balance_red_v': cv2.CAP_PROP_WHITE_BALANCE_RED_V,
            'gamma': cv2.CAP_PROP_GAMMA,
            'backlight': cv2.CAP_PROP_BACKLIGHT,
            'auto_exposure': cv2.CAP_PROP_AUTO_EXPOSURE,
            'auto_gain': cv2.CAP_PROP_GAIN,
            'focus': cv2.CAP_PROP_FOCUS,
            'auto_focus': cv2.CAP_PROP_AUTOFOCUS,
            'zoom': cv2.CAP_PROP_ZOOM,
            'pan': cv2.CAP_PROP_PAN,
            'tilt': cv2.CAP_PROP_TILT,
            'roll': cv2.CAP_PROP_ROLL,
            'iris': cv2.CAP_PROP_IRIS,
            'settings': cv2.CAP_PROP_SETTINGS
        }
        
        success_count = 0
        for name, value in properties.items():
            if name in prop_mapping:
                try:
                    if cap.set(prop_mapping[name], value):
                        success_count += 1
                except:
                    pass
        
        cap.release()
        return success_count > 0
    except Exception as e:
        print(f"Error setting camera properties for {device}: {e}")
        return False

@app.route('/cameras', methods=['GET'])
def list_cameras():
    """List available camera devices on the Pi"""
    try:
        # Find all video devices
        video_devices = glob.glob('/dev/video*')
        cameras = []
        
        for device in sorted(video_devices):
            try:
                # Try to open the camera to see if it's working
                cap = cv2.VideoCapture(device)
                if cap.isOpened():
                    # Get some basic info
                    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                    fps = cap.get(cv2.CAP_PROP_FPS)
                    
                    cameras.append({
                        'device': device,
                        'width': width,
                        'height': height,
                        'fps': fps,
                        'working': True
                    })
                    cap.release()
                else:
                    cameras.append({
                        'device': device,
                        'working': False
                    })
            except Exception as e:
                cameras.append({
                    'device': device,
                    'working': False,
                    'error': str(e)
                })
        
        return jsonify({'cameras': cameras}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/camera_properties/<path:device>', methods=['GET'])
def get_camera_properties_route(device):
    """Get available camera properties for a specific device"""
    try:
        # URL decode the device path
        import urllib.parse
        device = urllib.parse.unquote(device)
        print(f"Getting properties for device: {device}")
        
        properties = get_camera_properties(device)
        if properties is not None:
            return jsonify({'properties': properties}), 200
        else:
            return jsonify({'error': f'Cannot access camera {device}'}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/camera_settings/<path:device>', methods=['GET'])
def get_camera_settings_route(device):
    """Get current camera settings for a specific device"""
    try:
        # URL decode the device path
        import urllib.parse
        device = urllib.parse.unquote(device)
        print(f"Getting settings for device: {device}")
        
        settings = load_camera_settings()
        device_settings = settings.get(device, {})
        return jsonify({'settings': device_settings}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/camera_settings/<path:device>', methods=['POST'])
def set_camera_settings_route(device):
    """Set camera settings for a specific device"""
    try:
        # URL decode the device path
        import urllib.parse
        device = urllib.parse.unquote(device)
        print(f"Setting settings for device: {device}")
        
        data = request.json
        settings = data.get('settings', {})
        
        # Apply settings to camera
        if set_camera_properties(device, settings):
            # Save settings to file
            all_settings = load_camera_settings()
            all_settings[device] = settings
            if save_camera_settings(all_settings):
                return jsonify({'status': 'settings applied and saved'}), 200
            else:
                return jsonify({'status': 'settings applied but not saved'}), 200
        else:
            return jsonify({'error': 'Failed to apply camera settings'}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/camera_settings', methods=['GET'])
def get_all_camera_settings():
    """Get all saved camera settings"""
    try:
        settings = load_camera_settings()
        return jsonify({'settings': settings}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/camera_settings', methods=['POST'])
def save_all_camera_settings():
    """Save all camera settings"""
    try:
        data = request.json
        settings = data.get('settings', {})
        
        if save_camera_settings(settings):
            return jsonify({'status': 'settings saved'}), 200
        else:
            return jsonify({'error': 'Failed to save settings'}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/username', methods=['GET'])
def get_username():
    """Get the username of the Pi"""
    try:
        username = os.getenv('USER') or os.getenv('USERNAME') or 'pi'
        return jsonify({'username': username}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/snapshot/<device>', methods=['GET'])
def snapshot_device(device):
    """Take a snapshot from a specific camera device"""
    try:
        # Convert device path to camera index
        if device.startswith('/dev/video'):
            camera_index = int(device.replace('/dev/video', ''))
        else:
            camera_index = int(device)
        
        # Use OpenCV to capture a frame
        cap = cv2.VideoCapture(camera_index)
        if not cap.isOpened():
            return jsonify({'error': f'Cannot open camera {device}'}), 500
        
        ret, frame = cap.read()
        cap.release()
        
        if not ret:
            return jsonify({'error': f'Failed to capture frame from {device}'}), 500
        
        # Save to temporary file
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.jpg')
        cv2.imwrite(temp_file.name, frame)
        
        return send_file(temp_file.name, mimetype='image/jpeg')
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/snapshot/cam0', methods=['GET'])
def snapshot_cam0():
    """Take a snapshot from camera 0 (legacy endpoint)"""
    return snapshot_device('/dev/video0')

@app.route('/snapshot/cam1', methods=['GET'])
def snapshot_cam1():
    """Take a snapshot from camera 1 (legacy endpoint)"""
    return snapshot_device('/dev/video2')

@app.route('/start_recording', methods=['POST'])
def start_recording():
    global recording_process

    data = request.json
    duration = data.get('duration', 60)
    fps = data.get('fps', 100)
    width = data.get('width', 640)
    height = data.get('height', 480)
    cam0 = data.get('cam0', '/dev/video0')
    cam1 = data.get('cam1', '/dev/video2')
    output_dir = data.get('output_dir', '/home/pi/captures')
    subject = data.get('subject', 'default')
    
    # Apply camera settings before recording
    settings = load_camera_settings()
    if cam0 in settings:
        set_camera_properties(cam0, settings[cam0])
    if cam1 in settings:
        set_camera_properties(cam1, settings[cam1])

    if recording_process is None or recording_process.poll() is not None:
        # Create folder name with subject
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        folder_name = f'record_{subject}_{timestamp}'
        
        cmd = [
            'python3', 'dual_camera_ffmpeg_record.py',
            '--duration', str(duration),
            '--fps', str(fps),
            '--width', str(width),
            '--height', str(height),
            '--cam0', cam0,
            '--cam1', cam1,
            '--output_dir', output_dir,
            '--subject', subject
        ]

        print(f"Launching: {' '.join(cmd)}")
        recording_process = subprocess.Popen(cmd)
        return jsonify({'status': 'recording started', 'folder': folder_name}), 200
    else:
        return jsonify({'status': 'already recording'}), 400

@app.route('/stop_recording', methods=['POST'])
def stop_recording():
    global recording_process
    if recording_process and recording_process.poll() is None:
        recording_process.terminate()
        recording_process = None
        return jsonify({'status': 'recording stopped'}), 200
    else:
        return jsonify({'status': 'not recording'}), 400

@app.route('/status', methods=['GET'])
def status():
    global recording_process
    is_recording = recording_process is not None and recording_process.poll() is None
    return jsonify({'recording': is_recording}), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
