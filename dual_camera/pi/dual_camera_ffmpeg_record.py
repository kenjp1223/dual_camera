import cv2
import argparse
import os
import time
import subprocess
import threading
from datetime import datetime
import json

# GPIO setup for LED indicator
try:
    import RPi.GPIO as GPIO
    HAS_GPIO = True
    LED_PIN = 18  # GPIO18
except ImportError:
    HAS_GPIO = False
    print("GPIO not available - LED indicator disabled")

def set_led(state):
    """Set LED state (if GPIO available)"""
    if HAS_GPIO:
        GPIO.output(LED_PIN, GPIO.HIGH if state else GPIO.LOW)

def apply_camera_settings(device, settings):
    """Apply camera settings using v4l2-ctl"""
    if not settings:
        return True
    
    try:
        # Convert device path to device number
        if device.startswith('/dev/video'):
            device_num = device.replace('/dev/video', '')
        else:
            device_num = device
        
        # Property mapping for v4l2-ctl
        v4l2_props = {
            'exposure': 'exposure_absolute',
            'gain': 'gain',
            'brightness': 'brightness',
            'contrast': 'contrast',
            'saturation': 'saturation',
            'hue': 'hue',
            'white_balance_blue_u': 'white_balance_blue_u',
            'white_balance_red_v': 'white_balance_red_v',
            'gamma': 'gamma',
            'backlight': 'backlight_compensation',
            'auto_exposure': 'exposure_auto',
            'focus': 'focus_absolute',
            'auto_focus': 'focus_auto',
            'zoom': 'zoom_absolute',
            'pan': 'pan_absolute',
            'tilt': 'tilt_absolute',
            'roll': 'roll_absolute',
            'iris': 'iris_absolute'
        }
        
        success_count = 0
        for prop_name, value in settings.items():
            if prop_name in v4l2_props:
                v4l2_prop = v4l2_props[prop_name]
                try:
                    # Use v4l2-ctl to set the property
                    cmd = ['v4l2-ctl', '-d', f'/dev/video{device_num}', '-c', f'{v4l2_prop}={value}']
                    result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
                    if result.returncode == 0:
                        success_count += 1
                        print(f"Set {v4l2_prop}={value} for {device}")
                    else:
                        print(f"Failed to set {v4l2_prop}={value} for {device}: {result.stderr}")
                except Exception as e:
                    print(f"Error setting {v4l2_prop} for {device}: {e}")
        
        return success_count > 0
    except Exception as e:
        print(f"Error applying camera settings for {device}: {e}")
        return False

def load_camera_settings():
    """Load camera settings from JSON file"""
    settings_file = 'camera_settings.json'
    if os.path.exists(settings_file):
        try:
            with open(settings_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading camera settings: {e}")
    return {}

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
    """Flush camera buffer by reading a few frames"""
    try:
        print(f"Flushing camera buffer for {device}...")
        # Use ffmpeg to flush buffer
        flush_cmd = [
            "ffmpeg",
            "-f", "v4l2",
            "-input_format", "mjpeg",
            "-i", device,
            "-frames:v", str(num_frames),
            "-f", "null",
            "-"
        ]
        
        flush_process = subprocess.Popen(flush_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        flush_process.wait()
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
    start_barrier = threading.Barrier(2)
    processes = []
    led_start_event = threading.Event()

    def run_camera(cmd, camera_name):
        try:
            start_barrier.wait()
            print(f"Starting {camera_name} at {datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')}")
            process = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            processes.append((process, camera_name))
            # Signal LED thread after both cameras have started
            if not led_start_event.is_set():
                led_start_event.set()
            process.wait()
            print(f"{camera_name} finished at {datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')}")
        except Exception as e:
            print(f"Error in {camera_name}: {e}")

    def led_buffer_thread(duration):
        led_start_event.wait()  # Wait until both cameras have started
        print("[DEBUG] LED buffer thread started after camera trigger.")
        time.sleep(2.5)
        set_led(True)
        print("[DEBUG] LED ON (after 2.5s buffer)")
        time.sleep(max(0, duration - 5))
        set_led(False)
        print("[DEBUG] LED OFF (2.5s before end)")

    # GPIO setup
    if HAS_GPIO:
        print(f"[DEBUG] Setting up GPIO{LED_PIN} for LED output.")
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(LED_PIN, GPIO.OUT)
        set_led(False)
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

    # --- RAMDISK LOGIC ---
    RAMDISK_PATH = '/mnt/ramdisk'
    ramdisk_save_dir = os.path.join(RAMDISK_PATH, f'record_{args.subject}_{timestamp}')
    try:
        os.makedirs(ramdisk_save_dir, exist_ok=True)
    except Exception as e:
        print(f"\nERROR: RAM disk not found or not mounted at {RAMDISK_PATH}.")
        print("Please see the README.md for instructions on setting up the RAM disk (tmpfs).\n")
        print(f"Details: {e}")
        exit(1)

    cam0_out = os.path.join(ramdisk_save_dir, "cam0.mp4")
    cam1_out = os.path.join(ramdisk_save_dir, "cam1.mp4")

    print(f"Recording for {record_duration} seconds at {args.fps} FPS")
    print(f"Subject: {args.subject}")
    print(f"Temporary RAM disk directory: {ramdisk_save_dir}")
    print(f"Final output directory: {args.output_dir}")
    print(f"Cam0: {args.cam0} -> {cam0_out}")
    print(f"Cam1: {args.cam1} -> {cam1_out}")

    # Load and apply camera settings
    print("Loading camera settings...")
    settings = load_camera_settings()
    
    if args.cam0 in settings:
        print(f"Applying settings to {args.cam0}...")
        if apply_camera_settings(args.cam0, settings[args.cam0]):
            print(f"Settings applied to {args.cam0}")
        else:
            print(f"Warning: Failed to apply settings to {args.cam0}")
    
    if args.cam1 in settings:
        print(f"Applying settings to {args.cam1}...")
        if apply_camera_settings(args.cam1, settings[args.cam1]):
            print(f"Settings applied to {args.cam1}")
        else:
            print(f"Warning: Failed to apply settings to {args.cam1}")

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
    processes = synchronized_recording(cmd0, cmd1, None, args.fps, record_duration)

    # Move files from RAM disk to final location
    final_save_dir = os.path.join(args.output_dir, f'record_{args.subject}_{timestamp}')
    try:
        os.makedirs(final_save_dir, exist_ok=True)
        
        # Move files
        import shutil
        shutil.move(cam0_out, os.path.join(final_save_dir, "cam0.mp4"))
        shutil.move(cam1_out, os.path.join(final_save_dir, "cam1.mp4"))
        
        # Clean up RAM disk directory
        os.rmdir(ramdisk_save_dir)
        
        print(f"Recording complete. Files saved to: {final_save_dir}")
        
        # Analyze synchronization
        cam0_path = os.path.join(final_save_dir, "cam0.mp4")
        cam1_path = os.path.join(final_save_dir, "cam1.mp4")
        
        if os.path.exists(cam0_path) and os.path.exists(cam1_path):
            print("\n--- Synchronization Analysis ---")
            first0, last0 = get_first_last_frame_timestamps(cam0_path)
            first1, last1 = get_first_last_frame_timestamps(cam1_path)
            
            if first0 is not None and first1 is not None:
                sync_diff = abs(first0 - first1)
                print(f"Start time difference: {sync_diff:.3f} seconds")
                if sync_diff < 0.1:
                    print("✓ Cameras appear to be well synchronized")
                else:
                    print("⚠ Cameras may have synchronization issues")
            
            # Get file sizes
            size0 = os.path.getsize(cam0_path) / (1024*1024)  # MB
            size1 = os.path.getsize(cam1_path) / (1024*1024)  # MB
            print(f"File sizes: cam0={size0:.1f}MB, cam1={size1:.1f}MB")
        
    except Exception as e:
        print(f"Error moving files: {e}")
        print(f"Files may still be in RAM disk: {ramdisk_save_dir}")

if __name__ == "__main__":
    main()
