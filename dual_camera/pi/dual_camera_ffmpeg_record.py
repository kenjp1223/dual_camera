import argparse
import os
import subprocess
import time
from datetime import datetime

def build_ffmpeg_command(device, output_path, width, height, fps, frames):
    return [
        "ffmpeg",
        "-f", "v4l2",
        "-input_format", "mjpeg",
        "-video_size", f"{width}x{height}",
        "-framerate", str(fps),
        "-i", device,
        "-vcodec", "copy",
        "-frames:v", str(frames),
        output_path
    ]

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
    args = parser.parse_args()

    frame_count = args.duration * args.fps
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    save_dir = os.path.join(args.output_dir, f'record_{args.subject}_{timestamp}')
    os.makedirs(save_dir, exist_ok=True)

    cam0_out = os.path.join(save_dir, "cam0.mp4")
    cam1_out = os.path.join(save_dir, "cam1.mp4")

    cmd0 = build_ffmpeg_command(args.cam0, cam0_out, args.width, args.height, args.fps, frame_count)
    cmd1 = build_ffmpeg_command(args.cam1, cam1_out, args.width, args.height, args.fps, frame_count)

    print(f"Recording {frame_count} frames at {args.fps} FPS for {args.duration} seconds")
    print(f"Subject: {args.subject}")
    print("Output directory:", save_dir)

    start_time = time.time()

    # Launch both ffmpeg processes nearly simultaneously
    proc0 = subprocess.Popen(cmd0, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    proc1 = subprocess.Popen(cmd1, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    # Wait for both processes to finish
    proc0.wait()
    proc1.wait()

    elapsed = time.time() - start_time
    print(f"Finished. Elapsed time: {elapsed:.2f} seconds")
    print(f"Expected duration: {args.duration} s, Expected frames: {frame_count}")

if __name__ == '__main__':
    main()
