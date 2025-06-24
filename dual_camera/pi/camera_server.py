from flask import Flask, request, jsonify
import subprocess
import threading
import os

app = Flask(__name__)
recording_process = None

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

    if recording_process is None or recording_process.poll() is not None:
        cmd = [
            'python3', 'dual_camera_ffmpeg_record.py',
            '--duration', str(duration),
            '--fps', str(fps),
            '--width', str(width),
            '--height', str(height),
            '--cam0', cam0,
            '--cam1', cam1,
            '--output_dir', output_dir
        ]

        print(f"Launching: {' '.join(cmd)}")
        recording_process = subprocess.Popen(cmd)
        return jsonify({'status': 'recording started'}), 200
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
