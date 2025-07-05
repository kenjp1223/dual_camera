#!/usr/bin/env python3
"""
Fast post-processing script for dual camera videos.
Concatenates cam0.mp4 and cam1.mp4 into a side-by-side video using optimized ffmpeg settings.
Supports rotation, preview snapshots, frame synchronization, and FOV cropping.
"""

import argparse
import os
import subprocess
import sys
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox
from PIL import Image, ImageTk
import cv2
import math

def calculate_fov_crop(width, height, fov_degrees, center_x=None, center_y=None):
    """
    Calculate crop parameters for a given FOV in degrees.
    
    Args:
        width: Original video width
        height: Original video height
        fov_degrees: Field of view in degrees (0-360)
        center_x: Center point X coordinate (0-1, default: 0.5)
        center_y: Center point Y coordinate (0-1, default: 0.5)
    
    Returns:
        tuple: (crop_width, crop_height, crop_x, crop_y) or None if no cropping needed
    """
    if fov_degrees >= 360 or fov_degrees <= 0:
        return None  # No cropping needed
    
    # Default center point
    if center_x is None:
        center_x = 0.5
    if center_y is None:
        center_y = 0.5
    
    # Calculate the crop size based on FOV
    # For a circular FOV, the crop area is proportional to the FOV angle
    fov_radians = math.radians(fov_degrees)
    
    # Calculate crop dimensions (maintaining aspect ratio)
    if width >= height:
        # Landscape video
        crop_width = int(width * (fov_degrees / 360))
        crop_height = int(height * (fov_degrees / 360))
    else:
        # Portrait video
        crop_height = int(height * (fov_degrees / 360))
        crop_width = int(width * (fov_degrees / 360))
    
    # Ensure minimum size
    crop_width = max(crop_width, 64)
    crop_height = max(crop_height, 64)
    
    # Calculate crop position
    crop_x = int((width - crop_width) * center_x)
    crop_y = int((height - crop_height) * center_y)
    
    # Ensure crop stays within bounds
    crop_x = max(0, min(crop_x, width - crop_width))
    crop_y = max(0, min(crop_y, height - crop_height))
    
    return crop_width, crop_height, crop_x, crop_y

def check_video_files(folder_path):
    """Check if both cam0.mp4 and cam1.mp4 exist in the folder"""
    cam0_path = os.path.join(folder_path, "cam0.mp4")
    cam1_path = os.path.join(folder_path, "cam1.mp4")
    
    if not os.path.exists(cam0_path):
        print(f"Error: cam0.mp4 not found in {folder_path}")
        return False, None, None
    
    if not os.path.exists(cam1_path):
        print(f"Error: cam1.mp4 not found in {folder_path}")
        return False, None, None
    
    return True, cam0_path, cam1_path

def get_video_info(video_path):
    """Get video dimensions and duration using ffprobe"""
    try:
        cmd = [
            'ffprobe', '-v', 'quiet', '-print_format', 'json',
            '-show_streams', '-select_streams', 'v:0', video_path
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        
        import json
        data = json.loads(result.stdout)
        stream = data['streams'][0]
        
        width = int(stream['width'])
        height = int(stream['height'])
        duration = float(stream.get('duration', 0))
        fps = eval(stream.get('r_frame_rate', '30/1'))
        codec = stream.get('codec_name', 'unknown')
        
        return width, height, duration, fps, codec
    except Exception as e:
        print(f"Error getting video info for {video_path}: {e}")
        return None, None, None, None, None

def get_frame_count(video_path):
    """Get exact frame count of a video"""
    try:
        cmd = [
            'ffprobe', '-v', 'quiet', '-select_streams', 'v:0',
            '-count_packets', '-show_entries', 'stream=nb_read_packets',
            '-print_format', 'csv=p=0', video_path
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return int(result.stdout.strip())
    except Exception as e:
        print(f"Error getting frame count for {video_path}: {e}")
        return None

def analyze_frame_sync(cam0_path, cam1_path):
    """Analyze frame synchronization between two videos"""
    print("Analyzing frame synchronization...")
    
    # Get frame counts
    frames0 = get_frame_count(cam0_path)
    frames1 = get_frame_count(cam1_path)
    
    if frames0 is None or frames1 is None:
        print("Error: Could not get frame counts")
        return None
    
    print(f"Frame counts - cam0: {frames0}, cam1: {frames1}")
    
    # Get video info
    cam0_width, cam0_height, cam0_duration, cam0_fps, _ = get_video_info(cam0_path)
    cam1_width, cam1_height, cam1_duration, cam1_fps, _ = get_video_info(cam1_path)
    
    print(f"Duration - cam0: {cam0_duration:.3f}s, cam1: {cam1_duration:.3f}s")
    print(f"FPS - cam0: {cam0_fps:.2f}, cam1: {cam1_fps:.2f}")
    
    # Calculate differences
    frame_diff = abs(frames0 - frames1)
    duration_diff = abs(cam0_duration - cam1_duration)
    
    print(f"Frame difference: {frame_diff}")
    print(f"Duration difference: {duration_diff:.3f}s")
    
    # Determine sync issues
    sync_info = {
        'frames0': frames0,
        'frames1': frames1,
        'frame_diff': frame_diff,
        'duration0': cam0_duration,
        'duration1': cam1_duration,
        'duration_diff': duration_diff,
        'fps0': cam0_fps,
        'fps1': cam1_fps,
        'has_sync_issues': frame_diff > 1 or duration_diff > 0.1
    }
    
    if sync_info['has_sync_issues']:
        print("⚠️  Frame synchronization issues detected!")
        if frame_diff > 1:
            print(f"   - Frame count mismatch: {frame_diff} frames")
        if duration_diff > 0.1:
            print(f"   - Duration mismatch: {duration_diff:.3f}s")
    else:
        print("✅ Videos appear to be well synchronized")
    
    return sync_info

def create_synchronized_video(cam0_path, cam1_path, output_path, layout='vertical', 
                            cam0_rotation=0, cam1_rotation=0, force_sync=False, target_frames=None,
                            cam0_crop_width=None, cam0_crop_height=None, cam0_crop_x=None, cam0_crop_y=None,
                            cam1_crop_width=None, cam1_crop_height=None, cam1_crop_x=None, cam1_crop_y=None):
    """
    Create synchronized concatenated video with optional frame alignment
    """
    try:
        # Analyze synchronization
        sync_info = analyze_frame_sync(cam0_path, cam1_path)
        
        if sync_info is None:
            print("Error: Could not analyze video synchronization")
            return False
        
        # If force_sync is enabled and there are sync issues, align frames
        if force_sync and sync_info['has_sync_issues']:
            print("Applying frame synchronization...")
            
            # Determine target frame count (use the shorter video)
            if target_frames is None:
                target_frames = min(sync_info['frames0'], sync_info['frames1'])
            
            print(f"Target frame count: {target_frames}")
            
            # Create temporary synchronized videos
            temp_cam0 = cam0_path + ".sync_temp.mp4"
            temp_cam1 = cam1_path + ".sync_temp.mp4"
            
            # Trim videos to target frame count
            cmd0 = [
                'ffmpeg', '-i', cam0_path,
                '-vcodec', 'copy',
                '-frames:v', str(target_frames),
                '-y', temp_cam0
            ]
            
            cmd1 = [
                'ffmpeg', '-i', cam1_path,
                '-vcodec', 'copy',
                '-frames:v', str(target_frames),
                '-y', temp_cam1
            ]
            
            print("Creating synchronized versions...")
            result0 = subprocess.run(cmd0, capture_output=True, text=True)
            result1 = subprocess.run(cmd1, capture_output=True, text=True)
            
            if result0.returncode != 0 or result1.returncode != 0:
                print("Error creating synchronized videos")
                return False
            
            # Use synchronized videos for concatenation
            cam0_path = temp_cam0
            cam1_path = temp_cam1
            
            print("Frame synchronization applied successfully")
        
        # Get video info (may have changed after sync)
        cam0_width, cam0_height, _, _, _ = get_video_info(cam0_path)
        cam1_width, cam1_height, _, _, _ = get_video_info(cam1_path)
        print(f"Detected cam0: {cam0_width}x{cam0_height}, cam1: {cam1_width}x{cam1_height}")
        
        if any(x is None for x in [cam0_width, cam0_height, cam1_width, cam1_height]):
            print("Error: Could not get video dimensions")
            return False
        
        # Apply rotations and FOV cropping
        cam0_rot_filter = ""
        cam1_rot_filter = ""
        cam0_rotated_width, cam0_rotated_height = cam0_width, cam0_height
        cam1_rotated_width, cam1_rotated_height = cam1_width, cam1_height
        
        # Apply rotation to cam0
        if cam0_rotation == 90:
            cam0_rot_filter = "[0:v]transpose=1[v0_rot];"
            cam0_rotated_width, cam0_rotated_height = cam0_height, cam0_width
        elif cam0_rotation == 180:
            cam0_rot_filter = "[0:v]transpose=1,transpose=1[v0_rot];"
        elif cam0_rotation == 270:
            cam0_rot_filter = "[0:v]transpose=2[v0_rot];"
            cam0_rotated_width, cam0_rotated_height = cam0_height, cam0_width
        else:
            cam0_rot_filter = "[0:v]copy[v0_rot];"
        
        # Apply rotation to cam1
        if cam1_rotation == 90:
            cam1_rot_filter = "[1:v]transpose=1[v1_rot];"
            cam1_rotated_width, cam1_rotated_height = cam1_height, cam1_width
        elif cam1_rotation == 180:
            cam1_rot_filter = "[1:v]transpose=1,transpose=1[v1_rot];"
        elif cam1_rotation == 270:
            cam1_rot_filter = "[1:v]transpose=2[v1_rot];"
            cam1_rotated_width, cam1_rotated_height = cam1_height, cam1_width
        else:
            cam1_rot_filter = "[1:v]copy[v1_rot];"
        
        # Apply rectangular cropping to cam0
        cam0_crop_filter = ""
        if cam0_crop_width is not None and cam0_crop_height is not None:
            crop_width = int(cam0_rotated_width * cam0_crop_width)
            crop_height = int(cam0_rotated_height * cam0_crop_height)
            crop_x = int(cam0_rotated_width * cam0_crop_x) if cam0_crop_x is not None else 0
            crop_y = int(cam0_rotated_height * cam0_crop_y) if cam0_crop_y is not None else 0
            
            # Ensure crop stays within bounds
            crop_x = max(0, min(crop_x, cam0_rotated_width - crop_width))
            crop_y = max(0, min(crop_y, cam0_rotated_height - crop_height))
            
            cam0_crop_filter = f"[v0_rot]crop={crop_width}:{crop_height}:{crop_x}:{crop_y}[v0_crop];"
            cam0_rotated_width, cam0_rotated_height = crop_width, crop_height
            print(f"Applied rectangular crop to cam0: {crop_width}x{crop_height} at ({crop_x},{crop_y})")
        else:
            cam0_crop_filter = "[v0_rot]copy[v0_crop];"
        
        # Apply rectangular cropping to cam1
        cam1_crop_filter = ""
        if cam1_crop_width is not None and cam1_crop_height is not None:
            crop_width = int(cam1_rotated_width * cam1_crop_width)
            crop_height = int(cam1_rotated_height * cam1_crop_height)
            crop_x = int(cam1_rotated_width * cam1_crop_x) if cam1_crop_x is not None else 0
            crop_y = int(cam1_rotated_height * cam1_crop_y) if cam1_crop_y is not None else 0
            
            # Ensure crop stays within bounds
            crop_x = max(0, min(crop_x, cam1_rotated_width - crop_width))
            crop_y = max(0, min(crop_y, cam1_rotated_height - crop_height))
            
            cam1_crop_filter = f"[v1_rot]crop={crop_width}:{crop_height}:{crop_x}:{crop_y}[v1_crop];"
            cam1_rotated_width, cam1_rotated_height = crop_width, crop_height
            print(f"Applied rectangular crop to cam1: {crop_width}x{crop_height} at ({crop_x},{crop_y})")
        else:
            cam1_crop_filter = "[v1_rot]copy[v1_crop];"
        
        # Check if we can use copy mode
        can_copy = (cam0_rotated_width == cam1_rotated_width and 
                   cam0_rotated_height == cam1_rotated_height and
                   cam0_rotation == 0 and cam1_rotation == 0 and
                   not force_sync)  # Can't copy if we did frame sync
        
        # After cropping, do not scale. Stack as-is.
        # WARNING: The cropped regions must have the same height (for hstack) or same width (for vstack)!
        if layout == 'vertical':
            total_height = cam0_rotated_height + cam1_rotated_height
            total_width = max(cam0_rotated_width, cam1_rotated_width)
            print("Using fast mode (re-encoding)...")
            # No scale filter
            concat_filter = f"[v0_crop][v1_crop]vstack=inputs=2[v]"
            filter_complex = f"{cam0_rot_filter}{cam1_rot_filter}{cam0_crop_filter}{cam1_crop_filter}{concat_filter}"
            cmd = [
                'ffmpeg', '-i', cam0_path, '-i', cam1_path,
                '-filter_complex', filter_complex,
                '-map', '[v]', '-map', '0:a?',
                '-c:v', 'libx264', '-preset', 'ultrafast', '-crf', '23',
                '-avoid_negative_ts', 'make_zero',
                '-y', output_path
            ]
        else:  # horizontal layout
            total_width = cam0_rotated_width + cam1_rotated_width
            total_height = max(cam0_rotated_height, cam1_rotated_height)
            print("Using fast mode (re-encoding)...")
            # No scale filter
            concat_filter = f"[v0_crop][v1_crop]hstack=inputs=2[v]"
            filter_complex = f"{cam0_rot_filter}{cam1_rot_filter}{cam0_crop_filter}{cam1_crop_filter}{concat_filter}"
            cmd = [
                'ffmpeg', '-i', cam0_path, '-i', cam1_path,
                '-filter_complex', filter_complex,
                '-map', '[v]', '-map', '0:a?',
                '-c:v', 'libx264', '-preset', 'ultrafast', '-crf', '23',
                '-avoid_negative_ts', 'make_zero',
                '-y', output_path
            ]
        print(f"cam0_path: {cam0_path}, cam1_path: {cam1_path}")
        print(f"ffmpeg command: {' '.join(cmd)}")
        print(f"Creating concatenated video: {output_path}")
        print(f"Output dimensions: {total_width}x{total_height}")
        
        # Run with progress output
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, 
                                 universal_newlines=True, bufsize=1)
        ffmpeg_output = []
        for line in process.stdout:
            ffmpeg_output.append(line)
            if 'time=' in line:
                print(f"\rProcessing: {line.strip()}", end='', flush=True)
        process.wait()
        
        if process.returncode == 0:
            print(f"\nSuccessfully created: {output_path}")
            
            # Clean up temporary files if they were created
            if force_sync and sync_info['has_sync_issues']:
                try:
                    os.remove(temp_cam0)
                    os.remove(temp_cam1)
                    print("Cleaned up temporary files")
                except:
                    pass
            
            return True
        else:
            print(f"\nError creating video (return code: {process.returncode})")
            print("ffmpeg output:")
            print(''.join(ffmpeg_output))
            return False
    except Exception as e:
        print(f"Error during video processing: {e}")
        return False

def create_preview_snapshot(cam0_path, cam1_path, output_path, layout='vertical', 
                          cam0_rotation=0, cam1_rotation=0,
                          cam0_crop_width=None, cam0_crop_height=None, cam0_crop_x=None, cam0_crop_y=None,
                          cam1_crop_width=None, cam1_crop_height=None, cam1_crop_x=None, cam1_crop_y=None):
    """
    Create a preview snapshot of the concatenated video for checking orientation
    """
    try:
        # Get video info
        cam0_width, cam0_height, _, _, _ = get_video_info(cam0_path)
        cam1_width, cam1_height, _, _, _ = get_video_info(cam1_path)
        
        if any(x is None for x in [cam0_width, cam0_height, cam1_width, cam1_height]):
            print("Error: Could not get video dimensions")
            return False
        
        # Apply rotations and FOV cropping
        cam0_rot_filter = ""
        cam1_rot_filter = ""
        cam0_rotated_width, cam0_rotated_height = cam0_width, cam0_height
        cam1_rotated_width, cam1_rotated_height = cam1_width, cam1_height
        
        # Apply rotation to cam0
        if cam0_rotation == 90:
            cam0_rot_filter = "[0:v]transpose=1[v0_rot];"
            cam0_rotated_width, cam0_rotated_height = cam0_height, cam0_width
        elif cam0_rotation == 180:
            cam0_rot_filter = "[0:v]transpose=1,transpose=1[v0_rot];"
        elif cam0_rotation == 270:
            cam0_rot_filter = "[0:v]transpose=2[v0_rot];"
            cam0_rotated_width, cam0_rotated_height = cam0_height, cam0_width
        else:
            cam0_rot_filter = "[0:v]copy[v0_rot];"
        
        # Apply rotation to cam1
        if cam1_rotation == 90:
            cam1_rot_filter = "[1:v]transpose=1[v1_rot];"
            cam1_rotated_width, cam1_rotated_height = cam1_height, cam1_width
        elif cam1_rotation == 180:
            cam1_rot_filter = "[1:v]transpose=1,transpose=1[v1_rot];"
        elif cam1_rotation == 270:
            cam1_rot_filter = "[1:v]transpose=2[v1_rot];"
            cam1_rotated_width, cam1_rotated_height = cam1_height, cam1_width
        else:
            cam1_rot_filter = "[1:v]copy[v1_rot];"
        
        # Apply rectangular cropping to cam0
        cam0_crop_filter = ""
        if cam0_crop_width is not None and cam0_crop_height is not None:
            crop_width = int(cam0_rotated_width * cam0_crop_width)
            crop_height = int(cam0_rotated_height * cam0_crop_height)
            crop_x = int(cam0_rotated_width * cam0_crop_x) if cam0_crop_x is not None else 0
            crop_y = int(cam0_rotated_height * cam0_crop_y) if cam0_crop_y is not None else 0
            
            # Ensure crop stays within bounds
            crop_x = max(0, min(crop_x, cam0_rotated_width - crop_width))
            crop_y = max(0, min(crop_y, cam0_rotated_height - crop_height))
            
            cam0_crop_filter = f"[v0_rot]crop={crop_width}:{crop_height}:{crop_x}:{crop_y}[v0_crop];"
            cam0_rotated_width, cam0_rotated_height = crop_width, crop_height
            print(f"Applied rectangular crop to cam0: {crop_width}x{crop_height} at ({crop_x},{crop_y})")
        else:
            cam0_crop_filter = "[v0_rot]copy[v0_crop];"
        
        # Apply rectangular cropping to cam1
        cam1_crop_filter = ""
        if cam1_crop_width is not None and cam1_crop_height is not None:
            crop_width = int(cam1_rotated_width * cam1_crop_width)
            crop_height = int(cam1_rotated_height * cam1_crop_height)
            crop_x = int(cam1_rotated_width * cam1_crop_x) if cam1_crop_x is not None else 0
            crop_y = int(cam1_rotated_height * cam1_crop_y) if cam1_crop_y is not None else 0
            
            # Ensure crop stays within bounds
            crop_x = max(0, min(crop_x, cam1_rotated_width - crop_width))
            crop_y = max(0, min(crop_y, cam1_rotated_height - crop_height))
            
            cam1_crop_filter = f"[v1_rot]crop={crop_width}:{crop_height}:{crop_x}:{crop_y}[v1_crop];"
            cam1_rotated_width, cam1_rotated_height = crop_width, crop_height
            print(f"Applied rectangular crop to cam1: {crop_width}x{crop_height} at ({crop_x},{crop_y})")
        else:
            cam1_crop_filter = "[v1_rot]copy[v1_crop];"
        
        if layout == 'vertical':
            # Vertical layout: cam0 on top, cam1 on bottom
            total_height = cam0_rotated_height + cam1_rotated_height
            total_width = max(cam0_rotated_width, cam1_rotated_width)
            
            scale_filter = f"[v0_crop]scale={total_width}:{cam0_rotated_height}[v0_scaled];[v1_crop]scale={total_width}:{cam1_rotated_height}[v1_scaled]"
            concat_filter = f"[v0_crop][v1_crop]vstack=inputs=2[v]"
        else:
            # Horizontal layout: cam0 on left, cam1 on right
            total_width = cam0_rotated_width + cam1_rotated_width
            total_height = max(cam0_rotated_height, cam1_rotated_height)
            
            scale_filter = f"[v0_crop]scale={cam0_rotated_width}:{total_height}[v0_scaled];[v1_crop]scale={cam1_rotated_width}:{total_height}[v1_scaled]"
            concat_filter = f"[v0_crop][v1_crop]hstack=inputs=2[v]"
        
        # Combine all filters
        filter_complex = f"{cam0_rot_filter}{cam1_rot_filter}{cam0_crop_filter}{cam1_crop_filter}{scale_filter};{concat_filter}"
        
        # Extract frame at 1 second (or 0.5 if video is shorter)
        cmd = [
            'ffmpeg', '-i', cam0_path, '-i', cam1_path,
            '-filter_complex', filter_complex,
            '-map', '[v]',
            '-ss', '0.5', '-vframes', '1',  # Extract frame at 0.5 seconds
            '-y', output_path
        ]
        
        print(f"Creating preview snapshot: {output_path}")
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            print(f"Preview snapshot created: {output_path}")
            return True
        else:
            print(f"Error creating preview: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"Error during preview creation: {e}")
        return False

def create_fast_concatenated_video(cam0_path, cam1_path, output_path, layout='vertical', 
                                 cam0_rotation=0, cam1_rotation=0):
    """
    Create concatenated video using optimized ffmpeg settings for speed
    """
    return create_synchronized_video(cam0_path, cam1_path, output_path, layout, 
                                   cam0_rotation, cam1_rotation, force_sync=False)

def create_super_fast_version(cam0_path, cam1_path, output_path, layout='vertical', 
                            cam0_rotation=0, cam1_rotation=0):
    """
    Super fast version using hardware acceleration if available
    """
    try:
        # Check for hardware acceleration
        hw_accel = None
        try:
            # Test for hardware acceleration
            test_cmd = ['ffmpeg', '-hide_banner', '-f', 'lavfi', '-i', 'testsrc=duration=1:size=640x480:rate=1', 
                       '-c:v', 'h264_v4l2m2m', '-f', 'null', '-']
            result = subprocess.run(test_cmd, capture_output=True, timeout=5)
            if result.returncode == 0:
                hw_accel = 'h264_v4l2m2m'  # Raspberry Pi hardware encoder
                print("Using Raspberry Pi hardware acceleration!")
        except:
            pass
        
        # Get video info
        cam0_width, cam0_height, cam0_duration, cam0_fps, cam0_codec = get_video_info(cam0_path)
        cam1_width, cam1_height, cam1_duration, cam1_fps, cam1_codec = get_video_info(cam1_path)
        
        # Apply rotations
        cam0_rot_filter = ""
        cam1_rot_filter = ""
        
        if cam0_rotation == 90:
            cam0_rot_filter = "[0:v]transpose=1[v0_rot];"
            cam0_width, cam0_height = cam0_height, cam0_width
        elif cam0_rotation == 180:
            cam0_rot_filter = "[0:v]transpose=1,transpose=1[v0_rot];"
        elif cam0_rotation == 270:
            cam0_rot_filter = "[0:v]transpose=2[v0_rot];"
            cam0_width, cam0_height = cam0_height, cam0_width
        else:
            cam0_rot_filter = "[0:v]copy[v0_rot];"
        
        if cam1_rotation == 90:
            cam1_rot_filter = "[1:v]transpose=1[v1_rot];"
            cam1_width, cam1_height = cam1_height, cam1_width
        elif cam1_rotation == 180:
            cam1_rot_filter = "[1:v]transpose=1,transpose=1[v1_rot];"
        elif cam1_rotation == 270:
            cam1_rot_filter = "[1:v]transpose=2[v1_rot];"
            cam1_width, cam1_height = cam1_height, cam1_width
        else:
            cam1_rot_filter = "[1:v]copy[v1_rot];"
        
        if layout == 'vertical':
            total_height = cam0_height + cam1_height
            total_width = max(cam0_width, cam1_width)
            scale_filter = f"[v0_rot]scale={total_width}:{cam0_height}[v0_scaled];[v1_rot]scale={total_width}:{cam1_height}[v1_scaled]"
            concat_filter = f"[v0_scaled][v1_scaled]vstack=inputs=2[v]"
        else:
            total_width = cam0_width + cam1_width
            total_height = max(cam0_height, cam1_height)
            scale_filter = f"[v0_rot]scale={cam0_width}:{total_height}[v0_scaled];[v1_rot]scale={cam1_width}:{total_height}[v1_scaled]"
            concat_filter = f"[v0_scaled][v1_scaled]hstack=inputs=2[v]"
        
        if hw_accel:
            # Use hardware acceleration
            cmd = [
                'ffmpeg', '-i', cam0_path, '-i', cam1_path,
                '-filter_complex', f"{cam0_rot_filter}{cam1_rot_filter}{scale_filter};{concat_filter}",
                '-map', '[v]', '-map', '0:a?',
                '-c:v', hw_accel, '-b:v', '5M',  # Hardware encoding
                '-threads', '0',
                '-y', output_path
            ]
        else:
            # Fallback to software encoding with ultrafast preset
            cmd = [
                'ffmpeg', '-i', cam0_path, '-i', cam1_path,
                '-filter_complex', f"{cam0_rot_filter}{cam1_rot_filter}{scale_filter};{concat_filter}",
                '-map', '[v]', '-map', '0:a?',
                '-c:v', 'libx264', '-preset', 'ultrafast', '-crf', '25',  # Faster encoding
                '-threads', '0',
                '-y', output_path
            ]
        
        print(f"Creating super fast concatenated video: {output_path}")
        print(f"Output dimensions: {total_width}x{total_height}")
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            print(f"Successfully created: {output_path}")
            return True
        else:
            print(f"Error creating video: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"Error during video processing: {e}")
        return False

def launch_manual_sync_gui():
    class VideoSyncGUI:
        def __init__(self, master):
            self.master = master
            self.master.title("Dual Camera Manual Sync & Trimming")
            self.folder = None
            self.cam0_path = None
            self.cam1_path = None
            self.cap0 = None
            self.cap1 = None
            self.frame0 = 0
            self.frame1 = 0
            self.total_frames0 = 0
            self.total_frames1 = 0
            self.frame0_zero = 0
            self.frame0_last = 0
            self.frame1_zero = 0
            self.frame1_last = 0
            self.duration = 0
            self.fps0 = 30
            self.fps1 = 30
            self.layout = tk.StringVar(value='vertical')
            # Rectangular cropping variables
            self.enable_crop = tk.BooleanVar(value=False)
            self.cam0_crop_width = tk.DoubleVar(value=1.0)  # 1.0 = 100% of original width
            self.cam0_crop_height = tk.DoubleVar(value=1.0)  # 1.0 = 100% of original height
            self.cam0_crop_x = tk.DoubleVar(value=0.0)  # 0.0 = start from left edge
            self.cam0_crop_y = tk.DoubleVar(value=0.0)  # 0.0 = start from top edge
            self.cam1_crop_width = tk.DoubleVar(value=1.0)
            self.cam1_crop_height = tk.DoubleVar(value=1.0)
            self.cam1_crop_x = tk.DoubleVar(value=0.0)
            self.cam1_crop_y = tk.DoubleVar(value=0.0)
            self.init_gui()

        def init_gui(self):
            # Folder selection
            folder_btn = tk.Button(self.master, text="Select Folder", command=self.select_folder)
            folder_btn.grid(row=0, column=0, columnspan=2, sticky="ew")
            self.folder_label = tk.Label(self.master, text="No folder selected")
            self.folder_label.grid(row=1, column=0, columnspan=2, sticky="ew")

            # Video canvases
            self.canvas0 = tk.Label(self.master)
            self.canvas0.grid(row=2, column=0)
            self.canvas1 = tk.Label(self.master)
            self.canvas1.grid(row=2, column=1)

            # Frame navigation and direct entry
            nav_frame = tk.Frame(self.master)
            nav_frame.grid(row=3, column=0, columnspan=2)
            # cam0 controls
            tk.Button(nav_frame, text="<< Prev0", command=lambda: self.change_frame(0, -1)).pack(side=tk.LEFT)
            tk.Button(nav_frame, text="Next0 >>", command=lambda: self.change_frame(0, 1)).pack(side=tk.LEFT)
            tk.Button(nav_frame, text="Set Frame Zero 0", command=lambda: self.set_frame_zero(0)).pack(side=tk.LEFT)
            tk.Button(nav_frame, text="Set Frame Last 0", command=lambda: self.set_frame_last(0)).pack(side=tk.LEFT)
            # cam0 direct entry
            tk.Label(nav_frame, text="  Go to frame 0:").pack(side=tk.LEFT)
            self.frame0_entry = tk.Entry(nav_frame, width=6)
            self.frame0_entry.pack(side=tk.LEFT)
            tk.Button(nav_frame, text="Go", command=lambda: self.goto_frame(0)).pack(side=tk.LEFT)
            self.frame0_entry.bind('<Return>', lambda event: self.goto_frame(0))
            tk.Label(nav_frame, text="   ").pack(side=tk.LEFT)
            # cam1 controls
            tk.Button(nav_frame, text="<< Prev1", command=lambda: self.change_frame(1, -1)).pack(side=tk.LEFT)
            tk.Button(nav_frame, text="Next1 >>", command=lambda: self.change_frame(1, 1)).pack(side=tk.LEFT)
            tk.Button(nav_frame, text="Set Frame Zero 1", command=lambda: self.set_frame_zero(1)).pack(side=tk.LEFT)
            tk.Button(nav_frame, text="Set Frame Last 1", command=lambda: self.set_frame_last(1)).pack(side=tk.LEFT)
            # cam1 direct entry
            tk.Label(nav_frame, text="  Go to frame 1:").pack(side=tk.LEFT)
            self.frame1_entry = tk.Entry(nav_frame, width=6)
            self.frame1_entry.pack(side=tk.LEFT)
            tk.Button(nav_frame, text="Go", command=lambda: self.goto_frame(1)).pack(side=tk.LEFT)
            self.frame1_entry.bind('<Return>', lambda event: self.goto_frame(1))

            # Info labels
            self.info0 = tk.Label(self.master, text="cam0: Frame 0/0")
            self.info0.grid(row=4, column=0)
            self.info1 = tk.Label(self.master, text="cam1: Frame 0/0")
            self.info1.grid(row=4, column=1)

            # Layout selector
            options_frame = tk.Frame(self.master)
            options_frame.grid(row=5, column=0, columnspan=2)
            tk.Label(options_frame, text="Layout:").pack(side=tk.LEFT)
            tk.OptionMenu(options_frame, self.layout, 'vertical', 'horizontal').pack(side=tk.LEFT)
            # Duration on its own row
            duration_frame = tk.Frame(self.master)
            duration_frame.grid(row=6, column=0, columnspan=2, sticky="ew")
            tk.Label(duration_frame, text="Duration (s):").pack(side=tk.LEFT)
            self.duration_entry = tk.Entry(duration_frame, width=8)
            self.duration_entry.pack(side=tk.LEFT)
            self.duration_entry.insert(0, "0")

            # Rotation controls for preview
            rot_frame = tk.Frame(self.master)
            rot_frame.grid(row=7, column=0, columnspan=2)
            tk.Label(rot_frame, text="Cam0 Rotation:").pack(side=tk.LEFT)
            self.cam0_rot_var = tk.IntVar(value=0)
            tk.OptionMenu(rot_frame, self.cam0_rot_var, 0, 90, 180, 270, command=lambda _: self.update_preview(0)).pack(side=tk.LEFT)
            tk.Label(rot_frame, text="   Cam1 Rotation:").pack(side=tk.LEFT)
            self.cam1_rot_var = tk.IntVar(value=0)
            tk.OptionMenu(rot_frame, self.cam1_rot_var, 0, 90, 180, 270, command=lambda _: self.update_preview(1)).pack(side=tk.LEFT)
            tk.Button(rot_frame, text="Preview Rotated Frames", command=self.preview_both).pack(side=tk.LEFT, padx=10)

            # Rectangular cropping controls
            crop_frame = tk.Frame(self.master)
            crop_frame.grid(row=8, column=0, columnspan=2, sticky="ew")
            
            # Enable cropping toggle
            crop_toggle_frame = tk.Frame(crop_frame)
            crop_toggle_frame.pack(fill='x', pady=2)
            tk.Checkbutton(crop_toggle_frame, text="Enable Rectangular Cropping", variable=self.enable_crop, 
                          command=self.toggle_crop_controls).pack(side=tk.LEFT)
            
            # Cropping controls (initially disabled)
            self.crop_controls_frame = tk.Frame(crop_frame)
            self.crop_controls_frame.pack(fill='x', pady=2)
            
            # Create 2-column layout for cropping controls
            crop_columns_frame = tk.Frame(self.crop_controls_frame)
            crop_columns_frame.pack(fill='x', pady=2)
            
            # Cam0 column (left)
            cam0_column = tk.Frame(crop_columns_frame)
            cam0_column.pack(side=tk.LEFT, fill='x', expand=True, padx=(0, 10))
            
            # Cam0 header
            tk.Label(cam0_column, text="Cam0 Settings", font=('Arial', 10, 'bold')).pack(pady=(0, 5))
            
            # Cam0 Width row
            cam0_width_frame = tk.Frame(cam0_column)
            cam0_width_frame.pack(fill='x', pady=1)
            tk.Label(cam0_width_frame, text="Width (%):").pack(side=tk.LEFT)
            tk.Scale(cam0_width_frame, from_=0.1, to=1.0, orient=tk.HORIZONTAL, 
                    variable=self.cam0_crop_width, resolution=0.01, length=100, 
                    command=self.update_cam0_width_entry).pack(side=tk.LEFT, padx=5)
            self.cam0_width_entry = tk.Entry(cam0_width_frame, width=6)
            self.cam0_width_entry.pack(side=tk.LEFT, padx=2)
            self.cam0_width_entry.insert(0, "1.00")
            self.cam0_width_entry.bind('<Return>', lambda e: self.update_cam0_width_slider())
            
            # Cam0 Height row
            cam0_height_frame = tk.Frame(cam0_column)
            cam0_height_frame.pack(fill='x', pady=1)
            tk.Label(cam0_height_frame, text="Height (%):").pack(side=tk.LEFT)
            tk.Scale(cam0_height_frame, from_=0.1, to=1.0, orient=tk.HORIZONTAL, 
                    variable=self.cam0_crop_height, resolution=0.01, length=100,
                    command=self.update_cam0_height_entry).pack(side=tk.LEFT, padx=5)
            self.cam0_height_entry = tk.Entry(cam0_height_frame, width=6)
            self.cam0_height_entry.pack(side=tk.LEFT, padx=2)
            self.cam0_height_entry.insert(0, "1.00")
            self.cam0_height_entry.bind('<Return>', lambda e: self.update_cam0_height_slider())
            
            # Cam0 X Offset row
            cam0_x_frame = tk.Frame(cam0_column)
            cam0_x_frame.pack(fill='x', pady=1)
            tk.Label(cam0_x_frame, text="X Offset:").pack(side=tk.LEFT)
            tk.Scale(cam0_x_frame, from_=0.0, to=0.9, orient=tk.HORIZONTAL, 
                    variable=self.cam0_crop_x, resolution=0.01, length=100,
                    command=self.update_cam0_x_entry).pack(side=tk.LEFT, padx=5)
            self.cam0_x_entry = tk.Entry(cam0_x_frame, width=6)
            self.cam0_x_entry.pack(side=tk.LEFT, padx=2)
            self.cam0_x_entry.insert(0, "0.00")
            self.cam0_x_entry.bind('<Return>', lambda e: self.update_cam0_x_slider())
            
            # Cam0 Y Offset row
            cam0_y_frame = tk.Frame(cam0_column)
            cam0_y_frame.pack(fill='x', pady=1)
            tk.Label(cam0_y_frame, text="Y Offset:").pack(side=tk.LEFT)
            tk.Scale(cam0_y_frame, from_=0.0, to=0.9, orient=tk.HORIZONTAL, 
                    variable=self.cam0_crop_y, resolution=0.01, length=100,
                    command=self.update_cam0_y_entry).pack(side=tk.LEFT, padx=5)
            self.cam0_y_entry = tk.Entry(cam0_y_frame, width=6)
            self.cam0_y_entry.pack(side=tk.LEFT, padx=2)
            self.cam0_y_entry.insert(0, "0.00")
            self.cam0_y_entry.bind('<Return>', lambda e: self.update_cam0_y_slider())
            
            # Cam1 column (right)
            cam1_column = tk.Frame(crop_columns_frame)
            cam1_column.pack(side=tk.RIGHT, fill='x', expand=True, padx=(10, 0))
            
            # Cam1 header
            tk.Label(cam1_column, text="Cam1 Settings", font=('Arial', 10, 'bold')).pack(pady=(0, 5))
            
            # Cam1 Width row
            cam1_width_frame = tk.Frame(cam1_column)
            cam1_width_frame.pack(fill='x', pady=1)
            tk.Label(cam1_width_frame, text="Width (%):").pack(side=tk.LEFT)
            tk.Scale(cam1_width_frame, from_=0.1, to=1.0, orient=tk.HORIZONTAL, 
                    variable=self.cam1_crop_width, resolution=0.01, length=100,
                    command=self.update_cam1_width_entry).pack(side=tk.LEFT, padx=5)
            self.cam1_width_entry = tk.Entry(cam1_width_frame, width=6)
            self.cam1_width_entry.pack(side=tk.LEFT, padx=2)
            self.cam1_width_entry.insert(0, "1.00")
            self.cam1_width_entry.bind('<Return>', lambda e: self.update_cam1_width_slider())
            
            # Cam1 Height row
            cam1_height_frame = tk.Frame(cam1_column)
            cam1_height_frame.pack(fill='x', pady=1)
            tk.Label(cam1_height_frame, text="Height (%):").pack(side=tk.LEFT)
            tk.Scale(cam1_height_frame, from_=0.1, to=1.0, orient=tk.HORIZONTAL, 
                    variable=self.cam1_crop_height, resolution=0.01, length=100,
                    command=self.update_cam1_height_entry).pack(side=tk.LEFT, padx=5)
            self.cam1_height_entry = tk.Entry(cam1_height_frame, width=6)
            self.cam1_height_entry.pack(side=tk.LEFT, padx=2)
            self.cam1_height_entry.insert(0, "1.00")
            self.cam1_height_entry.bind('<Return>', lambda e: self.update_cam1_height_slider())
            
            # Cam1 X Offset row
            cam1_x_frame = tk.Frame(cam1_column)
            cam1_x_frame.pack(fill='x', pady=1)
            tk.Label(cam1_x_frame, text="X Offset:").pack(side=tk.LEFT)
            tk.Scale(cam1_x_frame, from_=0.0, to=0.9, orient=tk.HORIZONTAL, 
                    variable=self.cam1_crop_x, resolution=0.01, length=100,
                    command=self.update_cam1_x_entry).pack(side=tk.LEFT, padx=5)
            self.cam1_x_entry = tk.Entry(cam1_x_frame, width=6)
            self.cam1_x_entry.pack(side=tk.LEFT, padx=2)
            self.cam1_x_entry.insert(0, "0.00")
            self.cam1_x_entry.bind('<Return>', lambda e: self.update_cam1_x_slider())
            
            # Cam1 Y Offset row
            cam1_y_frame = tk.Frame(cam1_column)
            cam1_y_frame.pack(fill='x', pady=1)
            tk.Label(cam1_y_frame, text="Y Offset:").pack(side=tk.LEFT)
            tk.Scale(cam1_y_frame, from_=0.0, to=0.9, orient=tk.HORIZONTAL, 
                    variable=self.cam1_crop_y, resolution=0.01, length=100,
                    command=self.update_cam1_y_entry).pack(side=tk.LEFT, padx=5)
            self.cam1_y_entry = tk.Entry(cam1_y_frame, width=6)
            self.cam1_y_entry.pack(side=tk.LEFT, padx=2)
            self.cam1_y_entry.insert(0, "0.00")
            self.cam1_y_entry.bind('<Return>', lambda e: self.update_cam1_y_slider())
            
            # Preview cropping button
            tk.Button(self.crop_controls_frame, text="Preview Cropped Frames", 
                     command=self.preview_cropped).pack(pady=2)
            
            # Save/Load cropping parameters
            save_load_frame = tk.Frame(self.crop_controls_frame)
            save_load_frame.pack(fill='x', pady=2)
            tk.Button(save_load_frame, text="Save Crop Settings", 
                     command=self.save_crop_settings).pack(side=tk.LEFT, padx=5)
            tk.Button(save_load_frame, text="Load Crop Settings", 
                     command=self.load_crop_settings).pack(side=tk.LEFT, padx=5)
            
            # Initially disable cropping controls
            self.toggle_crop_controls()

            # Process button
            process_btn = tk.Button(self.master, text="Trim && Concatenate", command=self.process_videos)
            process_btn.grid(row=9, column=0, columnspan=2, sticky="ew")

        def select_folder(self):
            folder = filedialog.askdirectory()
            if not folder:
                return
            self.folder = folder
            self.folder_label.config(text=folder)
            self.cam0_path = os.path.join(folder, "cam0.mp4")
            self.cam1_path = os.path.join(folder, "cam1.mp4")
            if not (os.path.exists(self.cam0_path) and os.path.exists(self.cam1_path)):
                messagebox.showerror("Error", "cam0.mp4 or cam1.mp4 not found in selected folder")
                return
            self.cap0 = cv2.VideoCapture(self.cam0_path)
            self.cap1 = cv2.VideoCapture(self.cam1_path)
            self.total_frames0 = int(self.cap0.get(cv2.CAP_PROP_FRAME_COUNT))
            self.total_frames1 = int(self.cap1.get(cv2.CAP_PROP_FRAME_COUNT))
            self.fps0 = self.cap0.get(cv2.CAP_PROP_FPS) or 30
            self.fps1 = self.cap1.get(cv2.CAP_PROP_FPS) or 30
            self.frame0 = 0
            self.frame1 = 0
            self.frame0_zero = 0
            self.frame1_zero = 0
            self.frame0_last = self.total_frames0 - 1
            self.frame1_last = self.total_frames1 - 1
            self.duration_entry.delete(0, tk.END)
            self.duration_entry.insert(0, str(int(min(self.total_frames0/self.fps0, self.total_frames1/self.fps1))))
            self.show_frame(0)
            self.show_frame(1)
            self.update_info()

        def rotate_frame(self, frame, angle):
            if angle == 90:
                return cv2.rotate(frame, cv2.ROTATE_90_CLOCKWISE)
            elif angle == 180:
                return cv2.rotate(frame, cv2.ROTATE_180)
            elif angle == 270:
                return cv2.rotate(frame, cv2.ROTATE_90_COUNTERCLOCKWISE)
            return frame

        def apply_rectangular_crop(self, frame, width_ratio, height_ratio, x_offset, y_offset):
            """Apply rectangular cropping to a frame"""
            height, width = frame.shape[:2]
            
            # Calculate crop dimensions
            crop_width = int(width * width_ratio)
            crop_height = int(height * height_ratio)
            
            # Ensure minimum size
            crop_width = max(crop_width, 64)
            crop_height = max(crop_height, 64)
            
            # Calculate crop position
            crop_x = int(width * x_offset)
            crop_y = int(height * y_offset)
            
            # Ensure crop stays within bounds
            crop_x = max(0, min(crop_x, width - crop_width))
            crop_y = max(0, min(crop_y, height - crop_height))
            
            # Apply crop
            return frame[crop_y:crop_y+crop_height, crop_x:crop_x+crop_width]

        def update_preview(self, cam):
            if cam == 0:
                self.show_frame(0, apply_rotation=True)
            else:
                self.show_frame(1, apply_rotation=True)

        def preview_both(self):
            self.show_frame(0, apply_rotation=True)
            self.show_frame(1, apply_rotation=True)

        def toggle_crop_controls(self):
            """Enable/disable cropping controls based on checkbox state"""
            def set_widget_state(widget, state):
                """Safely set widget state, only for widgets that support it"""
                try:
                    widget.configure(state=state)
                except tk.TclError:
                    # Widget doesn't support state configuration, skip it
                    pass
            
            if self.enable_crop.get():
                for child in self.crop_controls_frame.winfo_children():
                    set_widget_state(child, 'normal')
            else:
                for child in self.crop_controls_frame.winfo_children():
                    set_widget_state(child, 'disabled')

        def preview_cropped(self):
            """Preview frames with rectangular cropping applied"""
            if not self.enable_crop.get():
                messagebox.showinfo("Crop Preview", "Please enable rectangular cropping first.")
                return
            self.show_frame(0, apply_rotation=True, apply_crop=True)
            self.show_frame(1, apply_rotation=True, apply_crop=True)

        # Update methods for Cam0 sliders -> entry fields
        def update_cam0_width_entry(self, value=None):
            if value is None:
                value = self.cam0_crop_width.get()
            self.cam0_width_entry.delete(0, tk.END)
            self.cam0_width_entry.insert(0, f"{value:.2f}")

        def update_cam0_height_entry(self, value=None):
            if value is None:
                value = self.cam0_crop_height.get()
            self.cam0_height_entry.delete(0, tk.END)
            self.cam0_height_entry.insert(0, f"{value:.2f}")

        def update_cam0_x_entry(self, value=None):
            if value is None:
                value = self.cam0_crop_x.get()
            self.cam0_x_entry.delete(0, tk.END)
            self.cam0_x_entry.insert(0, f"{value:.2f}")

        def update_cam0_y_entry(self, value=None):
            if value is None:
                value = self.cam0_crop_y.get()
            self.cam0_y_entry.delete(0, tk.END)
            self.cam0_y_entry.insert(0, f"{value:.2f}")

        # Update methods for Cam1 sliders -> entry fields
        def update_cam1_width_entry(self, value=None):
            if value is None:
                value = self.cam1_crop_width.get()
            self.cam1_width_entry.delete(0, tk.END)
            self.cam1_width_entry.insert(0, f"{value:.2f}")

        def update_cam1_height_entry(self, value=None):
            if value is None:
                value = self.cam1_crop_height.get()
            self.cam1_height_entry.delete(0, tk.END)
            self.cam1_height_entry.insert(0, f"{value:.2f}")

        def update_cam1_x_entry(self, value=None):
            if value is None:
                value = self.cam1_crop_x.get()
            self.cam1_x_entry.delete(0, tk.END)
            self.cam1_x_entry.insert(0, f"{value:.2f}")

        def update_cam1_y_entry(self, value=None):
            if value is None:
                value = self.cam1_crop_y.get()
            self.cam1_y_entry.delete(0, tk.END)
            self.cam1_y_entry.insert(0, f"{value:.2f}")

        # Update methods for entry fields -> sliders
        def update_cam0_width_slider(self):
            try:
                value = float(self.cam0_width_entry.get())
                value = max(0.1, min(1.0, value))
                self.cam0_crop_width.set(value)
                self.update_cam0_width_entry(value)
            except ValueError:
                self.update_cam0_width_entry()

        def update_cam0_height_slider(self):
            try:
                value = float(self.cam0_height_entry.get())
                value = max(0.1, min(1.0, value))
                self.cam0_crop_height.set(value)
                self.update_cam0_height_entry(value)
            except ValueError:
                self.update_cam0_height_entry()

        def update_cam0_x_slider(self):
            try:
                value = float(self.cam0_x_entry.get())
                value = max(0.0, min(0.9, value))
                self.cam0_crop_x.set(value)
                self.update_cam0_x_entry(value)
            except ValueError:
                self.update_cam0_x_entry()

        def update_cam0_y_slider(self):
            try:
                value = float(self.cam0_y_entry.get())
                value = max(0.0, min(0.9, value))
                self.cam0_crop_y.set(value)
                self.update_cam0_y_entry(value)
            except ValueError:
                self.update_cam0_y_entry()

        def update_cam1_width_slider(self):
            try:
                value = float(self.cam1_width_entry.get())
                value = max(0.1, min(1.0, value))
                self.cam1_crop_width.set(value)
                self.update_cam1_width_entry(value)
            except ValueError:
                self.update_cam1_width_entry()

        def update_cam1_height_slider(self):
            try:
                value = float(self.cam1_height_entry.get())
                value = max(0.1, min(1.0, value))
                self.cam1_crop_height.set(value)
                self.update_cam1_height_entry(value)
            except ValueError:
                self.update_cam1_height_entry()

        def update_cam1_x_slider(self):
            try:
                value = float(self.cam1_x_entry.get())
                value = max(0.0, min(0.9, value))
                self.cam1_crop_x.set(value)
                self.update_cam1_x_entry(value)
            except ValueError:
                self.update_cam1_x_entry()

        def update_cam1_y_slider(self):
            try:
                value = float(self.cam1_y_entry.get())
                value = max(0.0, min(0.9, value))
                self.cam1_crop_y.set(value)
                self.update_cam1_y_entry(value)
            except ValueError:
                self.update_cam1_y_entry()

        def save_crop_settings(self):
            """Save current cropping parameters to a JSON file"""
            settings = {
                'cam0_crop_width': self.cam0_crop_width.get(),
                'cam0_crop_height': self.cam0_crop_height.get(),
                'cam0_crop_x': self.cam0_crop_x.get(),
                'cam0_crop_y': self.cam0_crop_y.get(),
                'cam1_crop_width': self.cam1_crop_width.get(),
                'cam1_crop_height': self.cam1_crop_height.get(),
                'cam1_crop_x': self.cam1_crop_x.get(),
                'cam1_crop_y': self.cam1_crop_y.get()
            }
            
            filename = filedialog.asksaveasfilename(
                defaultextension=".json",
                filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
                title="Save Crop Settings"
            )
            
            if filename:
                try:
                    with open(filename, 'w') as f:
                        json.dump(settings, f, indent=2)
                    messagebox.showinfo("Save Settings", f"Crop settings saved to {filename}")
                except Exception as e:
                    messagebox.showerror("Save Error", f"Failed to save settings: {e}")

        def load_crop_settings(self):
            """Load cropping parameters from a JSON file"""
            filename = filedialog.askopenfilename(
                filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
                title="Load Crop Settings"
            )
            
            if filename:
                try:
                    with open(filename, 'r') as f:
                        settings = json.load(f)
                    
                    # Update variables
                    self.cam0_crop_width.set(settings.get('cam0_crop_width', 1.0))
                    self.cam0_crop_height.set(settings.get('cam0_crop_height', 1.0))
                    self.cam0_crop_x.set(settings.get('cam0_crop_x', 0.0))
                    self.cam0_crop_y.set(settings.get('cam0_crop_y', 0.0))
                    self.cam1_crop_width.set(settings.get('cam1_crop_width', 1.0))
                    self.cam1_crop_height.set(settings.get('cam1_crop_height', 1.0))
                    self.cam1_crop_x.set(settings.get('cam1_crop_x', 0.0))
                    self.cam1_crop_y.set(settings.get('cam1_crop_y', 0.0))
                    
                    # Update entry fields
                    self.update_cam0_width_entry()
                    self.update_cam0_height_entry()
                    self.update_cam0_x_entry()
                    self.update_cam0_y_entry()
                    self.update_cam1_width_entry()
                    self.update_cam1_height_entry()
                    self.update_cam1_x_entry()
                    self.update_cam1_y_entry()
                    
                    messagebox.showinfo("Load Settings", f"Crop settings loaded from {filename}")
                except Exception as e:
                    messagebox.showerror("Load Error", f"Failed to load settings: {e}")

        def show_frame(self, cam, apply_rotation=False, apply_crop=False):
            if cam == 0 and self.cap0:
                self.cap0.set(cv2.CAP_PROP_POS_FRAMES, self.frame0)
                ret, frame = self.cap0.read()
                if ret:
                    angle = self.cam0_rot_var.get() if apply_rotation else 0
                    frame = self.rotate_frame(frame, angle)
                    
                    # Apply rectangular cropping if enabled and requested
                    if apply_crop and self.enable_crop.get():
                        frame = self.apply_rectangular_crop(frame, 
                                                          self.cam0_crop_width.get(),
                                                          self.cam0_crop_height.get(),
                                                          self.cam0_crop_x.get(),
                                                          self.cam0_crop_y.get())
                    
                    img = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    img = Image.fromarray(img)
                    img = img.resize((320, 240))
                    imgtk = ImageTk.PhotoImage(img)
                    self.canvas0.imgtk = imgtk
                    self.canvas0.config(image=imgtk)
            elif cam == 1 and self.cap1:
                self.cap1.set(cv2.CAP_PROP_POS_FRAMES, self.frame1)
                ret, frame = self.cap1.read()
                if ret:
                    angle = self.cam1_rot_var.get() if apply_rotation else 0
                    frame = self.rotate_frame(frame, angle)
                    
                    # Apply rectangular cropping if enabled and requested
                    if apply_crop and self.enable_crop.get():
                        frame = self.apply_rectangular_crop(frame, 
                                                          self.cam1_crop_width.get(),
                                                          self.cam1_crop_height.get(),
                                                          self.cam1_crop_x.get(),
                                                          self.cam1_crop_y.get())
                    
                    img = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    img = Image.fromarray(img)
                    img = img.resize((320, 240))
                    imgtk = ImageTk.PhotoImage(img)
                    self.canvas1.imgtk = imgtk
                    self.canvas1.config(image=imgtk)

        def change_frame(self, cam, delta):
            if cam == 0:
                self.frame0 = max(0, min(self.total_frames0-1, self.frame0+delta))
                self.show_frame(0)
            else:
                self.frame1 = max(0, min(self.total_frames1-1, self.frame1+delta))
                self.show_frame(1)
            self.update_info()

        def set_frame_zero(self, cam):
            if cam == 0:
                self.frame0_zero = self.frame0
            else:
                self.frame1_zero = self.frame1
            self.update_info()

        def set_frame_last(self, cam):
            if cam == 0:
                self.frame0_last = self.frame0
            else:
                self.frame1_last = self.frame1
            self.update_info()

        def goto_frame(self, cam):
            try:
                if cam == 0:
                    val = int(self.frame0_entry.get()) - 1
                    if 0 <= val < self.total_frames0:
                        self.frame0 = val
                        self.show_frame(0)
                else:
                    val = int(self.frame1_entry.get()) - 1
                    if 0 <= val < self.total_frames1:
                        self.frame1 = val
                        self.show_frame(1)
            except Exception:
                pass

        def update_info(self):
            self.info0.config(text=f"cam0: Frame {self.frame0+1}/{self.total_frames0} | Zero: {self.frame0_zero+1} | Last: {self.frame0_last+1}")
            self.info1.config(text=f"cam1: Frame {self.frame1+1}/{self.total_frames1} | Zero: {self.frame1_zero+1} | Last: {self.frame1_last+1}")

        def process_videos(self):
            try:
                duration = float(self.duration_entry.get())
                # Calculate start and end times in seconds for each video
                start0 = self.frame0_zero / self.fps0
                end0 = (self.frame0_last + 1) / self.fps0
                trim_duration0 = end0 - start0
                start1 = self.frame1_zero / self.fps1
                end1 = (self.frame1_last + 1) / self.fps1
                trim_duration1 = end1 - start1
                # Output paths
                out0 = os.path.normpath(os.path.join(self.folder, "cam0_trimmed.mp4"))
                out1 = os.path.normpath(os.path.join(self.folder, "cam1_trimmed.mp4"))
                # Number of frames to use (from cam0)
                frame_count0 = self.frame0_last - self.frame0_zero + 1
                frame_count1 = self.frame1_last - self.frame1_zero + 1
                frame_diff = abs(frame_count0 - frame_count1)
                if frame_diff > 10:
                    messagebox.showerror("Error", f"Frame count between zero and last differs by more than 10!\ncam0: {frame_count0}, cam1: {frame_count1}\nPlease re-align.")
                    return
                elif frame_diff > 0:
                    messagebox.showwarning("Warning", f"Frame count between zero and last differs by {frame_diff}.\ncam0: {frame_count0}, cam1: {frame_count1}\nProceeding with cam0's frame count.")
                # Apply cropping and duration trim directly to cam0_trimmed.mp4 and cam1_trimmed.mp4
                if self.enable_crop.get():
                    # Get cropping parameters
                    cam0_crop_width = self.cam0_crop_width.get()
                    cam0_crop_height = self.cam0_crop_height.get()
                    cam0_crop_x = self.cam0_crop_x.get()
                    cam0_crop_y = self.cam0_crop_y.get()
                    cam1_crop_width = self.cam1_crop_width.get()
                    cam1_crop_height = self.cam1_crop_height.get()
                    cam1_crop_x = self.cam1_crop_x.get()
                    cam1_crop_y = self.cam1_crop_y.get()
                    
                    # Calculate crop dimensions for cam0
                    cam0_width, cam0_height, _, _, _ = get_video_info(self.cam0_path)
                    cam0_crop_w = int(cam0_width * cam0_crop_width)
                    cam0_crop_h = int(cam0_height * cam0_crop_height)
                    cam0_crop_x_px = int(cam0_width * cam0_crop_x)
                    cam0_crop_y_px = int(cam0_height * cam0_crop_y)
                    
                    # Calculate crop dimensions for cam1
                    cam1_width, cam1_height, _, _, _ = get_video_info(self.cam1_path)
                    cam1_crop_w = int(cam1_width * cam1_crop_width)
                    cam1_crop_h = int(cam1_height * cam1_crop_height)
                    cam1_crop_x_px = int(cam1_width * cam1_crop_x)
                    cam1_crop_y_px = int(cam1_height * cam1_crop_y)
                    
                    # Ensure crops stay within bounds
                    cam0_crop_x_px = max(0, min(cam0_crop_x_px, cam0_width - cam0_crop_w))
                    cam0_crop_y_px = max(0, min(cam0_crop_y_px, cam0_height - cam0_crop_h))
                    cam1_crop_x_px = max(0, min(cam1_crop_x_px, cam1_width - cam1_crop_w))
                    cam1_crop_y_px = max(0, min(cam1_crop_y_px, cam1_height - cam1_crop_h))
                    
                    # Create cam0_trimmed.mp4 with cropping and duration trim
                    cmd0 = [
                        'ffmpeg', '-y', '-i', self.cam0_path,
                        '-ss', str(start0), '-t', str(duration),  # Apply duration trim
                        '-filter:v', f'crop={cam0_crop_w}:{cam0_crop_h}:{cam0_crop_x_px}:{cam0_crop_y_px}',
                        '-c:v', 'libx264', '-preset', 'ultrafast', '-crf', '23',
                        out0
                    ]
                    
                    # Create cam1_trimmed.mp4 with cropping and duration trim
                    cmd1 = [
                        'ffmpeg', '-y', '-i', self.cam1_path,
                        '-ss', str(start1), '-t', str(duration),  # Apply duration trim
                        '-filter:v', f'crop={cam1_crop_w}:{cam1_crop_h}:{cam1_crop_x_px}:{cam1_crop_y_px}',
                        '-c:v', 'libx264', '-preset', 'ultrafast', '-crf', '23',
                        out1
                    ]
                else:
                    # No cropping, just trim to duration
                    cmd0 = [
                        'ffmpeg', '-y', '-i', self.cam0_path,
                        '-ss', str(start0), '-t', str(duration),  # Apply duration trim
                        '-c:v', 'libx264', '-preset', 'ultrafast', '-crf', '23',
                        out0
                    ]
                    cmd1 = [
                        'ffmpeg', '-y', '-i', self.cam1_path,
                        '-ss', str(start1), '-t', str(duration),  # Apply duration trim
                        '-c:v', 'libx264', '-preset', 'ultrafast', '-crf', '23',
                        out1
                    ]
                
                subprocess.run(cmd0, check=True)
                subprocess.run(cmd1, check=True)
                # Check if trimmed videos exist
                if not (os.path.exists(out0) and os.path.exists(out1)):
                    messagebox.showerror("Error", "Failed to create trimmed videos.")
                    return
                # Concatenate the already-trimmed and cropped videos
                layout = self.layout.get()
                final_output = os.path.normpath(os.path.join(self.folder, f"manualsync_concatenated_{layout}_final.mp4"))
                
                # Simple concatenation without additional cropping (already done)
                success = create_synchronized_video(out0, out1, final_output, layout=layout,
                                                   cam0_rotation=self.cam0_rot_var.get(),
                                                   cam1_rotation=self.cam1_rot_var.get())
                if not success or not os.path.exists(final_output):
                    messagebox.showerror("Error", f"Failed to create concatenated video: {final_output}")
                    return
                # Show completion message
                messagebox.showinfo("Done", f"Processing complete!\n\nFinal merged video: {final_output}\nCam0 trimmed: {out0}\nCam1 trimmed: {out1}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to process videos: {e}")

    root = tk.Tk()
    app = VideoSyncGUI(root)
    root.mainloop()

def main():
    parser = argparse.ArgumentParser(description="Fast concatenation of dual camera videos with frame synchronization")
    parser.add_argument('folder', help='Folder containing cam0.mp4 and cam1.mp4')
    parser.add_argument('--output', '-o', help='Output video path (default: concatenated.mp4 in same folder)')
    parser.add_argument('--layout', choices=['vertical', 'horizontal'], default='vertical',
                       help='Layout: vertical (cam0 on top) or horizontal (side by side)')
    parser.add_argument('--super-fast', action='store_true', 
                       help='Use hardware acceleration for maximum speed')
    parser.add_argument('--list-folders', action='store_true', 
                       help='List all recording folders in the captures directory')
    parser.add_argument('--preview', action='store_true',
                       help='Create a preview snapshot instead of full video')
    parser.add_argument('--cam0-rotation', type=int, choices=[0, 90, 180, 270], default=0,
                       help='Rotation for cam0 in degrees (0, 90, 180, 270)')
    parser.add_argument('--cam1-rotation', type=int, choices=[0, 90, 180, 270], default=0,
                       help='Rotation for cam1 in degrees (0, 90, 180, 270)')
    parser.add_argument('--force-sync', action='store_true',
                       help='Force frame synchronization by trimming to shortest video')
    parser.add_argument('--analyze-sync', action='store_true',
                       help='Analyze frame synchronization without processing')
    parser.add_argument('--target-frames', type=int,
                       help='Target frame count for synchronization (default: use shortest video)')
    parser.add_argument('--cam0-crop-width', type=float,
                       help='Crop width ratio for cam0 (0.1-1.0)')
    parser.add_argument('--cam0-crop-height', type=float,
                       help='Crop height ratio for cam0 (0.1-1.0)')
    parser.add_argument('--cam0-crop-x', type=float, default=0.0,
                       help='Crop X offset for cam0 (0.0-0.9, default: 0.0)')
    parser.add_argument('--cam0-crop-y', type=float, default=0.0,
                       help='Crop Y offset for cam0 (0.0-0.9, default: 0.0)')
    parser.add_argument('--cam1-crop-width', type=float,
                       help='Crop width ratio for cam1 (0.1-1.0)')
    parser.add_argument('--cam1-crop-height', type=float,
                       help='Crop height ratio for cam1 (0.1-1.0)')
    parser.add_argument('--cam1-crop-x', type=float, default=0.0,
                       help='Crop X offset for cam1 (0.0-0.9, default: 0.0)')
    parser.add_argument('--cam1-crop-y', type=float, default=0.0,
                       help='Crop Y offset for cam1 (0.0-0.9, default: 0.0)')
    
    args = parser.parse_args()
    
    # Handle list-folders option
    if args.list_folders:
        captures_dir = os.path.join(args.folder, '..') if args.folder != '.' else '.'
        if os.path.exists(captures_dir):
            print(f"Recording folders in {captures_dir}:")
            for item in sorted(os.listdir(captures_dir)):
                item_path = os.path.join(captures_dir, item)
                if os.path.isdir(item_path) and item.startswith('record_'):
                    cam0_exists = os.path.exists(os.path.join(item_path, 'cam0.mp4'))
                    cam1_exists = os.path.exists(os.path.join(item_path, 'cam1.mp4'))
                    status = "✓" if cam0_exists and cam1_exists else "✗"
                    print(f"  {status} {item}")
        else:
            print(f"Directory not found: {captures_dir}")
        return
    
    # Check if folder exists
    if not os.path.exists(args.folder):
        print(f"Error: Folder '{args.folder}' does not exist")
        sys.exit(1)
    
    # Check for video files
    files_ok, cam0_path, cam1_path = check_video_files(args.folder)
    if not files_ok:
        sys.exit(1)
    
    # Handle analyze-sync option
    if args.analyze_sync:
        analyze_frame_sync(cam0_path, cam1_path)
        return
    
    # Set output path
    if args.output:
        output_path = args.output
    else:
        folder_name = os.path.basename(args.folder)
        if args.preview:
            output_path = os.path.join(args.folder, f"{folder_name}_preview_{args.layout}.jpg")
        else:
            speed_suffix = "_superfast" if args.super_fast else "_fast"
            rotation_suffix = ""
            if args.cam0_rotation > 0 or args.cam1_rotation > 0:
                rotation_suffix = f"_r{args.cam0_rotation}_{args.cam1_rotation}"
            sync_suffix = "_synced" if args.force_sync else ""
            crop_suffix = ""
            if (args.cam0_crop_width is not None or args.cam1_crop_width is not None or 
                args.cam0_crop_height is not None or args.cam1_crop_height is not None):
                crop_suffix = f"_crop{args.cam0_crop_width or 1.0}_{args.cam1_crop_width or 1.0}"
            output_path = os.path.join(args.folder, f"{folder_name}_concatenated{speed_suffix}{rotation_suffix}{sync_suffix}{crop_suffix}_{args.layout}.mp4")
    
    # Create preview or full video
    if args.preview:
        success = create_preview_snapshot(cam0_path, cam1_path, output_path, args.layout, 
                                        args.cam0_rotation, args.cam1_rotation,
                                        args.cam0_crop_width, args.cam0_crop_height,
                                        args.cam0_crop_x, args.cam0_crop_y,
                                        args.cam1_crop_width, args.cam1_crop_height,
                                        args.cam1_crop_x, args.cam1_crop_y)
    elif args.super_fast:
        success = create_super_fast_version(cam0_path, cam1_path, output_path, args.layout,
                                          args.cam0_rotation, args.cam1_rotation)
    else:
        success = create_synchronized_video(cam0_path, cam1_path, output_path, args.layout,
                                          args.cam0_rotation, args.cam1_rotation, 
                                          args.force_sync, args.target_frames,
                                          args.cam0_crop_width, args.cam0_crop_height,
                                          args.cam0_crop_x, args.cam0_crop_y,
                                          args.cam1_crop_width, args.cam1_crop_height,
                                          args.cam1_crop_x, args.cam1_crop_y)
    
    if success:
        if args.preview:
            print(f"Preview snapshot complete: {output_path}")
        else:
            print(f"Fast post-processing complete: {output_path}")
    else:
        print("Post-processing failed")
        sys.exit(1)

if __name__ == '__main__':
    if '--gui' in sys.argv:
        launch_manual_sync_gui()
    else:
        main() 