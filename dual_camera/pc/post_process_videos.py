#!/usr/bin/env python3
"""
Fast post-processing script for dual camera videos.
Concatenates cam0.mp4 and cam1.mp4 into a side-by-side video using optimized ffmpeg settings.
Supports rotation and preview snapshots.
"""

import argparse
import os
import subprocess
import sys
from pathlib import Path

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

def create_preview_snapshot(cam0_path, cam1_path, output_path, layout='vertical', 
                          cam0_rotation=0, cam1_rotation=0):
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
            # Vertical layout: cam0 on top, cam1 on bottom
            total_height = cam0_height + cam1_height
            total_width = max(cam0_width, cam1_width)
            
            scale_filter = f"[v0_rot]scale={total_width}:{cam0_height}[v0_scaled];[v1_rot]scale={total_width}:{cam1_height}[v1_scaled]"
            concat_filter = f"[v0_scaled][v1_scaled]vstack=inputs=2[v]"
        else:
            # Horizontal layout: cam0 on left, cam1 on right
            total_width = cam0_width + cam1_width
            total_height = max(cam0_height, cam1_height)
            
            scale_filter = f"[v0_rot]scale={cam0_width}:{total_height}[v0_scaled];[v1_rot]scale={cam1_width}:{total_height}[v1_scaled]"
            concat_filter = f"[v0_scaled][v1_scaled]hstack=inputs=2[v]"
        
        # Extract frame at 1 second (or 0.5 if video is shorter)
        cmd = [
            'ffmpeg', '-i', cam0_path, '-i', cam1_path,
            '-filter_complex', f"{cam0_rot_filter}{cam1_rot_filter}{scale_filter};{concat_filter}",
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
    try:
        # Get video info
        cam0_width, cam0_height, cam0_duration, cam0_fps, cam0_codec = get_video_info(cam0_path)
        cam1_width, cam1_height, cam1_duration, cam1_fps, cam1_codec = get_video_info(cam1_path)
        
        if any(x is None for x in [cam0_width, cam0_height, cam1_width, cam1_height]):
            print("Error: Could not get video dimensions")
            return False
        
        print(f"Cam0: {cam0_width}x{cam0_height}, {cam0_fps:.2f} fps, {cam0_codec}")
        print(f"Cam1: {cam1_width}x{cam1_height}, {cam1_fps:.2f} fps, {cam1_codec}")
        
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
        
        # Check if we can use copy mode (same codec and similar properties)
        can_copy = (cam0_codec == cam1_codec and 
                   abs(cam0_fps - cam1_fps) < 0.1 and
                   cam0_width == cam1_width and 
                   cam0_height == cam1_height and
                   cam0_rotation == 0 and cam1_rotation == 0)  # Can't copy if rotating
        
        if layout == 'vertical':
            # Vertical layout: cam0 on top, cam1 on bottom
            total_height = cam0_height + cam1_height
            total_width = max(cam0_width, cam1_width)
            
            if can_copy:
                # Fast copy mode - no re-encoding
                print("Using fast copy mode (no re-encoding)...")
                scale_filter = f"[0:v]scale={total_width}:{cam0_height}[v0];[1:v]scale={total_width}:{cam1_height}[v1]"
                concat_filter = f"[v0][v1]vstack=inputs=2[v]"
                
                cmd = [
                    'ffmpeg', '-i', cam0_path, '-i', cam1_path,
                    '-filter_complex', f"{scale_filter};{concat_filter}",
                    '-map', '[v]', '-map', '0:a?',
                    '-c:v', 'copy',  # Fast copy mode
                    '-avoid_negative_ts', 'make_zero',
                    '-y', output_path
                ]
            else:
                # Need to re-encode for compatibility or rotation
                print("Using optimized encoding mode...")
                scale_filter = f"[v0_rot]scale={total_width}:{cam0_height}[v0_scaled];[v1_rot]scale={total_width}:{cam1_height}[v1_scaled]"
                concat_filter = f"[v0_scaled][v1_scaled]vstack=inputs=2[v]"
                
                cmd = [
                    'ffmpeg', '-i', cam0_path, '-i', cam1_path,
                    '-filter_complex', f"{cam0_rot_filter}{cam1_rot_filter}{scale_filter};{concat_filter}",
                    '-map', '[v]', '-map', '0:a?',
                    '-c:v', 'libx264', '-preset', 'ultrafast', '-crf', '23',  # Fast encoding
                    '-threads', '0',  # Use all CPU cores
                    '-y', output_path
                ]
            
        else:  # horizontal layout
            # Horizontal layout: cam0 on left, cam1 on right
            total_width = cam0_width + cam1_width
            total_height = max(cam0_height, cam1_height)
            
            if can_copy:
                # Fast copy mode
                print("Using fast copy mode (no re-encoding)...")
                scale_filter = f"[0:v]scale={cam0_width}:{total_height}[v0];[1:v]scale={cam1_width}:{total_height}[v1]"
                concat_filter = f"[v0][v1]hstack=inputs=2[v]"
                
                cmd = [
                    'ffmpeg', '-i', cam0_path, '-i', cam1_path,
                    '-filter_complex', f"{scale_filter};{concat_filter}",
                    '-map', '[v]', '-map', '0:a?',
                    '-c:v', 'copy',  # Fast copy mode
                    '-avoid_negative_ts', 'make_zero',
                    '-y', output_path
                ]
            else:
                # Need to re-encode
                print("Using optimized encoding mode...")
                scale_filter = f"[v0_rot]scale={cam0_width}:{total_height}[v0_scaled];[v1_rot]scale={cam1_width}:{total_height}[v1_scaled]"
                concat_filter = f"[v0_scaled][v1_scaled]hstack=inputs=2[v]"
                
                cmd = [
                    'ffmpeg', '-i', cam0_path, '-i', cam1_path,
                    '-filter_complex', f"{cam0_rot_filter}{cam1_rot_filter}{scale_filter};{concat_filter}",
                    '-map', '[v]', '-map', '0:a?',
                    '-c:v', 'libx264', '-preset', 'ultrafast', '-crf', '23',  # Fast encoding
                    '-threads', '0',  # Use all CPU cores
                    '-y', output_path
                ]
        
        print(f"Creating concatenated video: {output_path}")
        print(f"Output dimensions: {total_width}x{total_height}")
        print("Running optimized ffmpeg command...")
        
        # Run with progress output
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, 
                                 universal_newlines=True, bufsize=1)
        
        # Show progress
        for line in process.stdout:
            if 'time=' in line:
                print(f"\rProcessing: {line.strip()}", end='', flush=True)
        
        process.wait()
        
        if process.returncode == 0:
            print(f"\nSuccessfully created: {output_path}")
            return True
        else:
            print(f"\nError creating video (return code: {process.returncode})")
            return False
            
    except Exception as e:
        print(f"Error during video processing: {e}")
        return False

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

def main():
    parser = argparse.ArgumentParser(description="Fast concatenation of dual camera videos")
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
            output_path = os.path.join(args.folder, f"{folder_name}_concatenated{speed_suffix}{rotation_suffix}_{args.layout}.mp4")
    
    # Create preview or full video
    if args.preview:
        success = create_preview_snapshot(cam0_path, cam1_path, output_path, args.layout, 
                                        args.cam0_rotation, args.cam1_rotation)
    elif args.super_fast:
        success = create_super_fast_version(cam0_path, cam1_path, output_path, args.layout,
                                          args.cam0_rotation, args.cam1_rotation)
    else:
        success = create_fast_concatenated_video(cam0_path, cam1_path, output_path, args.layout,
                                               args.cam0_rotation, args.cam1_rotation)
    
    if success:
        if args.preview:
            print(f"Preview snapshot complete: {output_path}")
        else:
            print(f"Fast post-processing complete: {output_path}")
    else:
        print("Post-processing failed")
        sys.exit(1)

if __name__ == '__main__':
    main() 