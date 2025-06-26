import argparse
import os
import subprocess
import time
import threading
import signal
import sys
from datetime import datetime
import cv2

# GPIO setup for LED trigger
try:
    import RPi.GPIO as GPIO
    HAS_GPIO = True
except ImportError:
    HAS_GPIO = False

LED_PIN = 17

def set_led(state):
    if HAS_GPIO:
        print(f"[DEBUG] Setting LED {'ON' if state else 'OFF'} on GPIO{LED_PIN}")
        GPIO.output(LED_PIN, GPIO.HIGH if state else GPIO.LOW)
    else:
        print(f"[DEBUG] GPIO not available, LED {'ON' if state else 'OFF'} requested")

def pre_warm_camera(device, duration=2):
    """Pre-warm camera to ensure it's ready for recording"""
    try:
        print(f"Pre-warming camera {device}...")
        # Use ffmpeg to pre-warm the camera
        warm_cmd = [
            "ffmpeg",
            "-f", "v4l2",
            "-input_format", "mjpeg",
            "-i", device,
            "-t", str(duration),  # Warm for 2 seconds
            "-f", "null",
            "-"
        ]
        
        # Run pre-warming in background
        warm_process = subprocess.Popen(warm_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        warm_process.wait()
        print(f"Camera {device} pre-warmed successfully")
        return True
    except Exception as e:
        print(f"Warning: Failed to pre-warm camera {device}: {e}")
        return False

def flush_camera(device, num_frames=10):
    """Flush camera buffer by grabbing and discarding a few frames."""
    try:
        print(f"Flushing camera buffer for {device}...")
        cap = cv2.VideoCapture(device)
        for _ in range(num_frames):
            cap.read()
        cap.release()
        print(f"Camera {device} buffer flushed.")
    except Exception as e:
        print(f"Warning: Failed to flush buffer for {device}: {e}")

def build_ffmpeg_command(device, output_path, width, height, fps, frames, sync_mode=True, add_timestamp=False):
    """Build ffmpeg command with synchronization options and minimal buffering."""
    cmd = [
        "ffmpeg",
        "-f", "v4l2",
        "-thread_queue_size", "512",
        "-fflags", "nobuffer",
        "-input_format", "mjpeg",
        "-video_size", f"{width}x{height}",
        "-framerate", str(fps),
        "-i", device,
        "-filter:v", f"fps={fps}",               # Resample to target fps
        "-vcodec", "libx264",                    # Compress using H.264
        "-preset", "ultrafast",                  # Fast encoding, larger files
        "-crf", "23",                            # Constant Rate Factor: 0–51 (lower is better)
        "-frames:v", str(frames),
    ]
    if add_timestamp:
        # Overlay timestamp for debugging sync (optional)
        cmd.extend([
            "-vf",
            "drawtext=fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf:text='%{pts\\:localtime\\:%T.%3f}':x=10:y=10:fontsize=24:fontcolor=white:box=1:boxcolor=0x00000099"
        ])
    if sync_mode:
        # Add synchronization options
        cmd.extend([
            "-avoid_negative_ts", "make_zero",   # Ensure consistent timestamps
            "-fflags", "+genpts",                # Generate presentation timestamps
            "-max_interleave_delta", "0",        # Minimize interleaving delays
        ])
    cmd.append(output_path)
    return cmd

def synchronized_recording(cmd0, cmd1, frame_count, fps, duration):
    """Start both cameras with precise synchronization and trigger LED indicator with buffer time."""
    # Create a barrier for synchronization
    start_barrier = threading.Barrier(2)
    processes = []

    def led_buffer_thread(duration):
        print("[DEBUG] LED buffer thread started.")
        time.sleep(1)
        set_led(True)
        print("[DEBUG] LED ON (after 1s buffer)")
        time.sleep(max(0, duration - 2))
        set_led(False)
        print("[DEBUG] LED OFF (1s before end)")

    def run_camera(cmd, camera_name):
        try:
            start_barrier.wait()
            print(f"Starting {camera_name} at {datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')}")
            process = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            processes.append((process, camera_name))
            process.wait()
            print(f"{camera_name} finished at {datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')}")
        except Exception as e:
            print(f"Error in {camera_name}: {e}")
    # GPIO setup
    if HAS_GPIO:
        print(f"[DEBUG] Setting up GPIO{LED_PIN} for LED output.")
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(LED_PIN, GPIO.OUT)
        set_led(False)
        print("[DEBUG] Starting LED buffer thread.")
        led_thread = threading.Thread(target=led_buffer_thread, args=(duration,))
        led_thread.start()
    else:
        print("[DEBUG] GPIO not available, skipping LED setup.")
    # Start both cameras in separate threads
    thread0 = threading.Thread(target=run_camera, args=(cmd0, "cam0"))
    thread1 = threading.Thread(target=run_camera, args=(cmd1, "cam1"))
    thread0.start()
    thread1.start()
    thread0.join()
    thread1.join()
    # Wait for LED thread to finish and cleanup
    if HAS_GPIO:
        led_thread.join()
        print("[DEBUG] Turning LED OFF after recording finished.")
        set_led(False)
        GPIO.cleanup()
    else:
        print("[DEBUG] GPIO not available, skipping LED cleanup.")
    return processes

def get_first_last_frame_timestamps(video_path):
    """Return (first_pts, last_pts) in seconds for a video using ffprobe."""
    try:
        # Get all frame PTS times
        cmd = [
            'ffprobe',
            '-v', 'error',
            '-select_streams', 'v:0',
            '-show_entries', 'frame=pts_time',
            '-of', 'csv=p=0',
            video_path
        ]
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        pts_times = []
        for line in result.stdout.strip().split('\n'):
            if line.strip():
                val = line.strip().split(',')[0]
                try:
                    pts_times.append(float(val))
                except Exception:
                    pass
        if pts_times:
            return pts_times[0], pts_times[-1]
        else:
            return None, None
    except Exception as e:
        print(f"Error extracting frame timestamps from {video_path}: {e}")
        return None, None

def main():
    parser = argparse.ArgumentParser(description="Dual USB camera capture with ffmpeg (synchronized)")
    parser.add_argument('--duration', type=int, default=60, help='Duration in seconds')
    parser.add_argument('--fps', type=int, default=100, help='Target FPS')
    parser.add_argument('--width', type=int, default=640)
    parser.add_argument('--height', type=int, default=480)
    parser.add_argument('--output_dir', type=str, default='/home/pi/captures')
    parser.add_argument('--cam0', type=str, default='/dev/video0')
    parser.add_argument('--cam1', type=str, default='/dev/video2')
    parser.add_argument('--subject', type=str, default='default', help='Subject name for folder naming')
    parser.add_argument('--pre-warm', action='store_true', default=True, help='Pre-warm cameras before recording')
    parser.add_argument('--sync-mode', action='store_true', default=True, help='Use synchronization mode')
    parser.add_argument('--add-timestamp', action='store_true', default=False, help='Overlay timestamp on video for debugging sync')
    args = parser.parse_args()

    # Add 5 seconds to the requested duration
    record_duration = args.duration + 5
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    save_dir = os.path.join(args.output_dir, f'record_{args.subject}_{timestamp}')
    os.makedirs(save_dir, exist_ok=True)

    cam0_out = os.path.join(save_dir, "cam0.mp4")
    cam1_out = os.path.join(save_dir, "cam1.mp4")

    print(f"Recording for {record_duration} seconds at {args.fps} FPS")
    print(f"Subject: {args.subject}")
    print(f"Output directory: {save_dir}")
    print(f"Cam0: {args.cam0} -> {cam0_out}")
    print(f"Cam1: {args.cam1} -> {cam1_out}")

    # Pre-warm cameras if enabled
    if args.pre_warm:
        print("Pre-warming cameras...")
        pre_warm_camera(args.cam0)
        pre_warm_camera(args.cam1)
        print("Pre-warming complete")

    # Flush camera buffers before recording
    flush_camera(args.cam0)
    flush_camera(args.cam1)

    # Build ffmpeg commands (remove frame count restriction, record for time only)
    def build_ffmpeg_command_time(device, output_path, width, height, fps, duration, sync_mode=True, add_timestamp=False):
        cmd = [
            "ffmpeg",
            "-f", "v4l2",
            "-thread_queue_size", "512",
            "-fflags", "nobuffer",
            "-input_format", "mjpeg",
            "-video_size", f"{width}x{height}",
            "-framerate", str(fps),
            "-i", device,
            "-filter:v", f"fps={fps}",
            "-vcodec", "libx264",
            "-preset", "ultrafast",
            "-crf", "23",
            "-t", str(duration),  # Record for time only
        ]
        if add_timestamp:
            cmd.extend([
                "-vf",
                "drawtext=fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf:text='%{pts\\:localtime\\:%T.%3f}':x=10:y=10:fontsize=24:fontcolor=white:box=1:boxcolor=0x00000099"
            ])
        if sync_mode:
            cmd.extend([
                "-avoid_negative_ts", "make_zero",
                "-fflags", "+genpts",
                "-max_interleave_delta", "0",
            ])
        cmd.append(output_path)
        return cmd

    cmd0 = build_ffmpeg_command_time(args.cam0, cam0_out, args.width, args.height, args.fps, record_duration, args.sync_mode, args.add_timestamp)
    cmd1 = build_ffmpeg_command_time(args.cam1, cam1_out, args.width, args.height, args.fps, record_duration, args.sync_mode, args.add_timestamp)

    print("Starting synchronized recording...")
    start_time = time.time()

    # Start synchronized recording
    processes = synchronized_recording(cmd0, cmd1, None, args.fps, record_duration)

    elapsed = time.time() - start_time
    print(f"Recording completed. Elapsed time: {elapsed:.2f} seconds")
    print(f"Expected duration: {record_duration} s")

    # Check if both processes completed successfully
    for process, camera_name in processes:
        if process.returncode != 0:
            print(f"Warning: {camera_name} exited with code {process.returncode}")
        else:
            print(f"{camera_name} completed successfully")

    # Verify output files
    if os.path.exists(cam0_out) and os.path.exists(cam1_out):
        print("Both output files created successfully")
    else:
        print("Error: One or both output files missing")

if __name__ == '__main__':
    main()
