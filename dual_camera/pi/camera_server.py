from flask import Flask, request, jsonify, send_file
import subprocess
import threading
import os
import cv2
import tempfile
from datetime import datetime
import glob

app = Flask(__name__)
recording_process = None

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
