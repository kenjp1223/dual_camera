import cv2
import argparse
import os
import time
from datetime import datetime

# ---- Arguments ----
parser = argparse.ArgumentParser(description='Dual USB Camera Recorder')
parser.add_argument('--duration', type=int, default=60, help='Duration in seconds')
parser.add_argument('--fps', type=int, default=30, help='Target FPS')
parser.add_argument('--width', type=int, default=640, help='Frame width')
parser.add_argument('--height', type=int, default=480, help='Frame height')
parser.add_argument('--output_dir', type=str, default='/home/pi/captures', help='Output directory')
args = parser.parse_args()

frame_target = args.fps * args.duration
timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
save_dir = os.path.join(args.output_dir, f'record_{timestamp}')
os.makedirs(save_dir, exist_ok=True)

# ---- Initialize Cameras ----
cap0 = cv2.VideoCapture(0)
cap1 = cv2.VideoCapture(1)

cap0.set(cv2.CAP_PROP_FRAME_WIDTH, args.width)
cap0.set(cv2.CAP_PROP_FRAME_HEIGHT, args.height)
cap1.set(cv2.CAP_PROP_FRAME_WIDTH, args.width)
cap1.set(cv2.CAP_PROP_FRAME_HEIGHT, args.height)

print(f"Recording {frame_target} frames at {args.width}x{args.height}")

# ---- Record Frames ----
frame_idx0 = 0
frame_idx1 = 0

start_time = time.time()

while max(frame_idx0, frame_idx1) < frame_target:
    ret0, frame0 = cap0.read()
    ret1, frame1 = cap1.read()
    
    if ret0:
        cv2.imwrite(os.path.join(save_dir, f"cam0_{frame_idx0:05d}.jpg"), frame0)
        frame_idx0 += 1
    if ret1:
        cv2.imwrite(os.path.join(save_dir, f"cam1_{frame_idx1:05d}.jpg"), frame1)
        frame_idx1 += 1

end_time = time.time()
elapsed = end_time - start_time
avg_fps0 = frame_idx0 / elapsed
avg_fps1 = frame_idx1 / elapsed

# ---- Summary ----
print(f"Finished recording.")
print(f"cam0: {frame_idx0} frames at {avg_fps0:.2f} fps")
print(f"cam1: {frame_idx1} frames at {avg_fps1:.2f} fps")
print(f"Elapsed time: {elapsed:.2f} seconds")


cap0.release()
cap1.release()
