# Dual Camera Raspberry Pi Setup (multi-device ready)

This guide describes how to set up and control multiple Raspberry Pi devices (e.g., `xxlab1`, `xxlab2`, etc.) for synchronized dual USB camera recording using `ffmpeg`. Recording is triggered remotely from a host PC over Ethernet or Wi-Fi using a comprehensive GUI interface with advanced post-processing capabilities.

---

## 1. Initial Raspberry Pi Setup (Per Device)

### ✅ Flash OS and Enable SSH

* Use **Raspberry Pi Imager** to flash Raspberry Pi OS Lite (64-bit).
* In advanced options:

  * Set hostname (e.g., `xxlab1`, `xxlab2`, ...)
  * Enable SSH
  * Configure Wi-Fi (SSID, password)
  * Set locale/timezone

### ✅ Assign Static IP Over Ethernet

SSH login if going headless
```bash
ssh <username>@<hostname>
```



Install dhcpcd

```bash
sudo apt update && sudo apt install dhcpcd5 -y
```
Edit the file:

```bash
sudo nano /etc/dhcpcd.conf
```

Append (change IP for each Pi):

```ini
interface eth0
static ip_address=192.168.2.XX/24  # Use 192.168.2.12, .13, etc. for other Pis
static domain_name_servers=8.8.8.8 1.1.1.1
```

Do **not** include `static routers=` if you want to keep internet through Wi-Fi.

Then reboot:

```bash
sudo reboot
```

---

## 2. Environment Setup (Per Pi)

### ✅ Install Dependencies

```bash
sudo apt update && sudo apt install git python3-venv ffmpeg python3-dev -y
```

### ✅ Clone Your Repository

```bash
git clone https://github.com/kenjp1223/dual_camera.git
cd dual_camera/dual_camera/pi
```

### ✅ Create and Activate Python Virtual Environment

```bash
python3 -m venv dualcam-venv
source dualcam-venv/bin/activate
```

### ✅ Install Python Dependencies

```bash
pip install flask RPi.GPIO
```

Or export and use:

```bash
#pip freeze > requirements.txt
pip install -r requirements.txt
```

---

## 2a. High-Speed Recording with RAM Disk (tmpfs) [Recommended]

To prevent dropped frames and maximize write speed, the recording script writes video files to a RAM disk (tmpfs) during capture, then moves them to permanent storage after recording.

**If the RAM disk is not set up, the script will exit with an error and instruct you to read this section.**

### How to Set Up a RAM Disk on Raspberry Pi

1. **Edit `/etc/fstab` to add a RAM disk:**
   ```bash
   sudo nano /etc/fstab
   ```
   Add this line at the end (for a 2GB RAM disk):
   ```
   tmpfs   /mnt/ramdisk   tmpfs   defaults,size=2G   0   0
   ```
   Adjust `size=2G` as needed (e.g., 1G, 3G).

2. **Create the mount point and mount the RAM disk:**
   ```bash
   sudo mkdir -p /mnt/ramdisk
   sudo mount /mnt/ramdisk
   ```

3. **Verify:**
   ```bash
   df -h /mnt/ramdisk
   ```
   You should see the correct size and available space.

4. **The RAM disk will now be available at `/mnt/ramdisk` on every boot.**

### How Recording Works with RAM Disk

- During recording, video files are written to `/mnt/ramdisk/record_<subject>_<timestamp>/`.
- After recording, files are automatically moved to your specified output directory (e.g., `/home/pi/captures`).
- If the RAM disk is missing or not mounted, the script will print an error and exit.  
  **Check this section if you see an error about the RAM disk.**

### Why Use a RAM Disk?

- **Much faster write speeds** (prevents dropped frames at high FPS/resolution).
- **Reduces SD card wear** (important for Pi longevity).
- **Files are only moved to permanent storage after recording is complete.**

---

## 3. Running the Recording Script Manually

### ✅ Test Recording

The script will write to the RAM disk first, then move files to your output directory after recording. If the RAM disk is not available, you will see an error message with instructions.

```bash
source dualcam-venv/bin/activate
cd /home/<username>/dual_camera/dual_camera/pi
python3 dual_camera_ffmpeg_record.py \
  --duration 10 \
  --fps 100 \
  --width 640 \
  --height 480 \
  --output_dir /home/<username>/captures
```

Check that `cam0.mp4` and `cam1.mp4` exist and are similar in frame count and duration.

To debug camera devices:

```bash
v4l2-ctl --list-devices
```

---

## 4. Running Flask Server (Trigger from PC)

### ✅ Start the Server on Pi

```bash
source dualcam-venv/bin/activate
cd /home/<username>/dual_camera/dual_camera/pi
python3 camera_server.py
```

Look for:

```
Running on http://192.168.2.XX:5000
```

### ✅ Trigger Recording from PC

#### PowerShell (Windows):

```powershell
curl -X POST http://192.168.2.XX:5000/start_recording ^
  -H "Content-Type: application/json" ^
  -d "{\"duration\": 10, \"fps\": 100, \"width\": 640, \"height\": 480}"
```

#### Linux/macOS/WSL:

```bash
curl -X POST http://192.168.2.XX:5000/start_recording \
  -H "Content-Type: application/json" \
  -d '{"duration": 10, "fps": 100, "width": 640, "height": 480}'
```

---

## 5. PC GUI Control Interface

### ✅ Setup PC Environment

Navigate to the PC control directory:

```bash
cd dual_camera/dual_camera/pc
```

Install Python dependencies:

```bash
pip install tkinter pillow requests
```

### ✅ Launch the GUI

```bash
python gui.py
```

### ✅ GUI Features

The PC GUI provides a comprehensive interface for managing multiple Raspberry Pis:

#### **Pi Management**
- **Network Discovery**: Automatically scan for Pis on the 192.168.2.x network
- **Add/Edit/Remove Pis**: Manage Pi configurations with custom names and IPs
- **Tabbed Interface**: One tab per Pi for scalable management (4-8+ devices)

#### **Recording Control**
- **Real-time Snapshots**: Live preview from both cameras on each Pi
- **Camera Detection**: Automatic detection of available video devices
- **Device Selection**: Choose which camera is cam0 vs cam1
- **Recording Parameters**: Set duration, FPS, resolution, subject name
- **Start/Stop/Status**: Control recording remotely with status feedback

#### **Configuration Management**
- **Per-Pi Settings**: Save individual configurations for each Pi
- **Config Persistence**: Load/save configurations to JSON files
- **Dynamic Output Paths**: Automatically set output directory based on Pi username

#### **Post-Processing Integration**
- **Manual Sync GUI**: Launch advanced post-processing interface directly from Pi tabs
- **One-Click Processing**: Streamlined workflow from recording to final output

---

## 6. Advanced Post-Processing and Video Management

### ✅ Manual Synchronization and Cropping GUI

The system includes a sophisticated post-processing interface with manual synchronization and advanced cropping capabilities:

#### **Manual Sync Features**
- **Frame-by-Frame Synchronization**: Manually align cam0 and cam1 videos frame by frame
- **Direct Frame Entry**: Enter specific frame numbers for precise synchronization
- **Real-time Preview**: See synchronized frames side-by-side with rotation support
- **Duration Trimming**: Set final video duration after synchronization

#### **Advanced Cropping Interface**
- **2-Column Layout**: Side-by-side cam0 and cam1 cropping controls for easy comparison
- **Rectangular Cropping**: Precise width, height, and offset controls for each camera
- **Percentage-based Controls**: Width and height as percentages of original video
- **Offset Positioning**: X and Y offsets to position the crop area
- **Live Preview**: See cropping effects applied to preview snapshots
- **Settings Persistence**: Save and load cropping configurations

#### **Cropping Parameters**
- **Width/Height**: Set as percentages (0.1 to 1.0) of original video dimensions
- **X/Y Offsets**: Position the crop area (0.0 to 0.9 range)
- **Independent Control**: Different cropping for cam0 and cam1
- **Preview Integration**: Cropping applied to both preview and final processing

### ✅ Post-Processing Workflow

#### **Step 1: Manual Synchronization**
1. Select recording folder containing cam0.mp4 and cam1.mp4
2. Use frame controls to align videos frame by frame
3. Set desired final duration
4. Preview synchronized result

#### **Step 2: Cropping Configuration**
1. Adjust width, height, and offset for cam0 and cam1
2. Use preview to see cropping effects
3. Save cropping settings for reuse
4. Load previous cropping configurations

#### **Step 3: Video Processing**
1. Apply synchronization and cropping to create trimmed videos
2. Concatenate cam0 and cam1 into final merged video
3. Output files: `cam0_trimmed.mp4`, `cam1_trimmed.mp4`, `merged_video.mp4`

### ✅ Performance Optimizations
- **RAM Disk Processing**: Temporary files written to RAM for maximum speed
- **Frame-Accurate Trimming**: Precise video cuts using ffmpeg with re-encoding
- **Efficient Concatenation**: Optimized merging without redundant processing
- **Progress Tracking**: Real-time updates during processing

### ✅ Using Post-Processing

#### **Via GUI**
1. Click "Post Process" on any Pi tab to launch manual sync GUI
2. Select recording folder containing cam0.mp4 and cam1.mp4
3. Synchronize videos frame by frame
4. Configure cropping settings for both cameras
5. Preview results before processing
6. Click "Process Videos" for final output

#### **Via Command Line**

```bash
# Launch manual sync GUI
python post_process_videos.py

# Process with specific settings
python post_process_videos.py /path/to/recording/folder

# List available recording folders
python post_process_videos.py /path/to/captures --list-folders
```

### ✅ Output Files

- **Synchronized Videos**: `cam0_trimmed.mp4`, `cam1_trimmed.mp4` (cropped and duration-trimmed)
- **Final Merged Video**: `merged_video.mp4` (concatenated result)
- **Cropping Settings**: Saved configurations for reuse
- **Preview Snapshots**: JPG previews with cropping applied

---

## 7. Optional: Autostart Script

Create a launcher script:

```bash
nano start_camera_server.sh
```

```bash
#!/bin/bash
cd /home/stuberlab1/dual_camera/dual_camera/pi
source dualcam-venv/bin/activate
python3 camera_server.py
```

Make executable:

```bash
chmod +x start_camera_server.sh
```

---

## 8. Complete Workflow Example

### ✅ Typical Usage

1. **Setup**: Configure multiple Pis with static IPs (192.168.2.11, .12, .13, etc.)
2. **Discovery**: Launch PC GUI and scan for Pis on network
3. **Configuration**: Set recording parameters and camera assignments per Pi
4. **Recording**: Start synchronized recording across all Pis
5. **Monitoring**: View live snapshots and recording status
6. **Post-Processing**: Use manual sync GUI for frame alignment and cropping
7. **Analysis**: Use the final synchronized and cropped videos for analysis

### ✅ Troubleshooting

#### **Synchronization Issues**
- Use manual sync GUI for frame-by-frame alignment
- Check frame counts between cam0 and cam1 videos
- Ensure videos have similar durations before processing

#### **Cropping Problems**
- Use preview function to verify cropping settings
- Adjust width/height percentages and offsets as needed
- Save successful cropping configurations for reuse

#### **Network Connectivity**
- Ensure Pis are on 192.168.2.x network
- Check firewall settings on PC
- Verify Pi camera server is running on port 5000

#### **Performance Issues**
- Use RAM disk for temporary file processing
- Ensure sufficient storage space on Pis
- Check USB camera compatibility with v4l2

---

## ✅ Done

You now have a complete multi-device recording system where each Pi:

* Has a unique name and static IP
* Can be controlled remotely via PC GUI
* Records synced dual-camera video to local storage
* Supports real-time monitoring and advanced post-processing
* Includes manual synchronization, cropping, and preview capabilities
* Features a modern 2-column interface for easy cropping comparison

The system scales from 1-2 Pis to 8+ devices with the tabbed interface, making it suitable for both small experiments and large-scale data collection.

Feel free to extend with:

* Auto-start with systemd
* Real-time video streaming
* Advanced post-processing filters
* Database integration for metadata

PRs and suggestions welcome!


Kentaro Ishii (University of Washington)
ken1223@uw.edu