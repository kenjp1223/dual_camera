from flask import Flask, request, jsonify
import subprocess
import threading

app = Flask(__name__)

recording_process = None

@app.route('/start_recording', methods=['POST'])
def start_recording():
    global recording_process
    data = request.json
    duration = data.get('duration', 300)  # default 5 min
    fps = data.get('fps', 100)
    # Start the dual camera recording in a subprocess
    if recording_process is None or recording_process.poll() is not None:
        recording_process = subprocess.Popen([
            'python3', 'dual_camera_record.py',
            '--duration', str(duration),
            '--fps', str(fps)
        ])
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