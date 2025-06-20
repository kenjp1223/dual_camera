import cv2
import argparse
import time
from datetime import datetime

parser = argparse.ArgumentParser(description='Dual USB Camera Recorder')
parser.add_argument('--duration', type=int, default=300, help='Recording duration in seconds')
parser.add_argument('--fps', type=int, default=100, help='Frames per second')
args = parser.parse_args()

duration = args.duration
fps = args.fps

# Open both cameras (assume /dev/video0 and /dev/video1)
cap0 = cv2.VideoCapture(0)
cap1 = cv2.VideoCapture(1)

cap0.set(cv2.CAP_PROP_FPS, fps)
cap1.set(cv2.CAP_PROP_FPS, fps)

width = int(cap0.get(cv2.CAP_PROP_FRAME_WIDTH))
height = int(cap0.get(cv2.CAP_PROP_FRAME_HEIGHT))

fourcc = cv2.VideoWriter_fourcc(*'XVID')
timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
out0 = cv2.VideoWriter(f'camera0_{timestamp}.avi', fourcc, fps, (width, height))
out1 = cv2.VideoWriter(f'camera1_{timestamp}.avi', fourcc, fps, (width, height))

start_time = time.time()
while time.time() - start_time < duration:
    ret0, frame0 = cap0.read()
    ret1, frame1 = cap1.read()
    if ret0:
        out0.write(frame0)
    if ret1:
        out1.write(frame1)
    # Sleep to maintain fps
    time.sleep(1.0 / fps)

cap0.release()
cap1.release()
out0.release()
out1.release() 