import argparse
import os
import subprocess
import time
import threading
import signal
import sys
from datetime import datetime

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

def build_ffmpeg_command(device, output_path, width, height, fps, frames, sync_mode=True):
    """Build ffmpeg command with synchronization options"""
    cmd = [
        "ffmpeg",
        "-f", "v4l2",
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
    """Start both cameras with precise synchronization"""
    
    # Create a barrier for synchronization
    start_barrier = threading.Barrier(2)
    processes = []
    
    def run_camera(cmd, camera_name):
        """Run a single camera with synchronization"""
        try:
            # Wait for both cameras to be ready
            start_barrier.wait()
            
            print(f"Starting {camera_name} at {time.time():.6f}")
            
            # Start the ffmpeg process
            process = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            processes.append((process, camera_name))
            
            # Wait for process to complete
            process.wait()
            print(f"{camera_name} finished at {time.time():.6f}")
            
        except Exception as e:
            print(f"Error in {camera_name}: {e}")
    
    # Start both cameras in separate threads
    thread0 = threading.Thread(target=run_camera, args=(cmd0, "cam0"))
    thread1 = threading.Thread(target=run_camera, args=(cmd1, "cam1"))
    
    thread0.start()
    thread1.start()
    
    # Wait for both threads to complete
    thread0.join()
    thread1.join()
    
    return processes

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
    args = parser.parse_args()

    frame_count = args.duration * args.fps
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    save_dir = os.path.join(args.output_dir, f'record_{args.subject}_{timestamp}')
    os.makedirs(save_dir, exist_ok=True)

    cam0_out = os.path.join(save_dir, "cam0.mp4")
    cam1_out = os.path.join(save_dir, "cam1.mp4")

    print(f"Recording {frame_count} frames at {args.fps} FPS for {args.duration} seconds")
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

    # Build ffmpeg commands
    cmd0 = build_ffmpeg_command(args.cam0, cam0_out, args.width, args.height, args.fps, frame_count, args.sync_mode)
    cmd1 = build_ffmpeg_command(args.cam1, cam1_out, args.width, args.height, args.fps, frame_count, args.sync_mode)

    print("Starting synchronized recording...")
    start_time = time.time()

    # Start synchronized recording
    processes = synchronized_recording(cmd0, cmd1, frame_count, args.fps, args.duration)

    elapsed = time.time() - start_time
    print(f"Recording completed. Elapsed time: {elapsed:.2f} seconds")
    print(f"Expected duration: {args.duration} s, Expected frames: {frame_count}")

    # Check if both processes completed successfully
    for process, camera_name in processes:
        if process.returncode != 0:
            print(f"Warning: {camera_name} exited with code {process.returncode}")
        else:
            print(f"{camera_name} completed successfully")

    # Verify output files
    if os.path.exists(cam0_out) and os.path.exists(cam1_out):
        print("Both output files created successfully")
        
        # Get file sizes for verification
        size0 = os.path.getsize(cam0_out)
        size1 = os.path.getsize(cam1_out)
        print(f"File sizes - cam0: {size0:,} bytes, cam1: {size1:,} bytes")
        
        # Check for significant size differences (potential sync issues)
        size_diff = abs(size0 - size1)
        size_ratio = size_diff / max(size0, size1)
        if size_ratio > 0.1:  # More than 10% difference
            print(f"Warning: Large file size difference detected ({size_ratio:.1%})")
            print("This may indicate synchronization issues")
    else:
        print("Error: One or both output files missing")

if __name__ == '__main__':
    main()
