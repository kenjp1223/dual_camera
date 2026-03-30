# Dual Camera Raspberry Pi Setup (multi-device ready)

This guide describes how to set up and control multiple Raspberry Pi devices (e.g., `xxlab1`, `xxlab2`, etc.) for synchronized dual USB camera recording using `ffmpeg`. Recording is triggered remotely from a host PC over Ethernet or Wi-Fi using a comprehensive GUI interface with advanced post-processing capabilities and camera settings management.

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
sudo apt update && sudo apt install git python3-venv ffmpeg python3-dev v4l-utils -y
```

**Note**: `v4l-utils` is required for camera settings management.

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

For high-speed recording, create a RAM disk to avoid SD card write speed limitations:

```bash
# Create mount point
sudo mkdir -p /mnt/ramdisk

# Add to /etc/fstab (add this line)
echo "tmpfs /mnt/ramdisk tmpfs defaults,size=2G 0 0" | sudo tee -a /etc/fstab

# Mount RAM disk
sudo mount -a

# Verify
df -h /mnt/ramdisk
```

This creates a 2GB RAM disk. Adjust size as needed (e.g., `size=4G` for 4GB).

---

## 3. Camera Settings Management

### ✅ Camera Settings Overview

The system now includes comprehensive camera settings management with the following features:

#### **Supported Camera Parameters**
- **Exposure & Gain**: Manual exposure control, gain adjustment, auto-exposure modes
- **Image Quality**: Brightness, contrast, saturation, gamma correction
- **Color Settings**: Hue adjustment, white balance (blue/red channels)
- **Focus & Zoom**: Manual focus, auto-focus, zoom control
- **Advanced**: Backlight compensation, pan/tilt/roll, iris control

#### **Settings Persistence**
- **Automatic Application**: Settings are automatically applied before each recording
- **JSON Storage**: Settings saved to `camera_settings.json` on each Pi
- **Import/Export**: Settings can be saved to and loaded from external files
- **Per-Device Configuration**: Different settings for each camera device

### ✅ Using Camera Settings via PC GUI

1. **Access Settings**: Click "Cam0 Settings" or "Cam1 Settings" buttons in the Pi tab
2. **Configure Parameters**: Adjust sliders and controls for each camera property
3. **Apply Settings**: Click "Apply Settings" to immediately apply to the camera
4. **Save Configuration**: Click "Save Settings" to save to a JSON file
5. **Load Configuration**: Click "Load Settings" to load from a file or Pi storage
6. **Reset to Default**: Click "Reset to Default" to restore original values

### ✅ Camera Settings via Command Line

You can also manage camera settings directly on the Pi using `v4l2-ctl`:

```bash
# List available camera properties
v4l2-ctl -d /dev/video0 --list-ctrls

# Set exposure
v4l2-ctl -d /dev/video0 -c exposure_absolute=100

# Set gain
v4l2-ctl -d /dev/video0 -c gain=50

# Set brightness
v4l2-ctl -d /dev/video0 -c brightness=128

# Set white balance
v4l2-ctl -d /dev/video0 -c white_balance_blue_u=128
v4l2-ctl -d /dev/video0 -c white_balance_red_v=128
```

### ✅ Testing Camera Settings

Test your camera settings before recording:

```bash
# Test recording with current settings
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

#### **Camera Settings Management**
- **Per-Camera Configuration**: Individual settings for cam0 and cam1
- **Real-time Adjustment**: Apply settings immediately to cameras
- **Settings Persistence**: Save and load camera configurations
- **Property Categories**: Organized settings by exposure, quality, color, focus, etc.
- **Import/Export**: Save settings to files for backup or sharing

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

For detailed command-line and GUI usage of the underlying post-processing tool, see `dual_camera/pc/POST_PROCESS_VIDEOS.md` (script: `dual_camera/pc/post_process_videos.py`).

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

#### **Post-Processing Workflow**
1. **Load Videos**: Select cam0.mp4 and cam1.mp4 from recording folder
2. **Manual Sync**: Align videos frame-by-frame for perfect synchronization
3. **Apply Cropping**: Set rectangular cropping parameters for each camera
4. **Preview Results**: Generate preview snapshots to verify settings
5. **Process Videos**: Create final synchronized and cropped output
6. **Save Settings**: Store cropping parameters for future use

#### **Output Files**
- **cam0_trimmed.mp4**: Synchronized and cropped cam0 video
- **cam1_trimmed.mp4**: Synchronized and cropped cam1 video
- **combined.mp4**: Side-by-side or stacked final output
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
4. **Camera Settings**: Configure exposure, gain, white balance, and other parameters
5. **Recording**: Start synchronized recording across all Pis with applied settings
6. **Monitoring**: View live snapshots and recording status
7. **Post-Processing**: Use manual sync GUI for frame alignment and cropping
8. **Analysis**: Use the final synchronized and cropped videos for analysis

### ✅ Camera Settings Workflow

1. **Access Settings**: Open camera settings dialog for cam0 or cam1
2. **Configure Parameters**: Adjust exposure, gain, brightness, contrast, etc.
3. **Apply Settings**: Click "Apply Settings" to test on camera
4. **Save Configuration**: Save settings to file for backup
5. **Verify**: Take snapshots to verify settings look correct
6. **Record**: Start recording - settings are automatically applied

### ✅ Troubleshooting

#### **Camera Settings Issues**
- **Settings Not Applied**: Check if camera supports the parameter using `v4l2-ctl --list-ctrls`
- **Settings Reset**: Some cameras reset settings on disconnect - reapply before recording
- **Parameter Range**: Use `v4l2-ctl -d /dev/videoX --list-ctrls` to see valid ranges
- **Camera Compatibility**: Not all USB cameras support all parameters

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
* Supports comprehensive camera settings management
* Records synced dual-camera video to local storage
* Applies saved camera settings automatically before recording
* Provides advanced post-processing with manual sync and cropping

The system is now ready for high-quality, synchronized dual-camera recording with full camera parameter control and professional post-processing capabilities.

Feel free to extend with:

* Auto-start with systemd
* Real-time video streaming
* Advanced post-processing filters
* Database integration for metadata

PRs and suggestions welcome!


Kentaro Ishii (University of Washington)
ken1223@uw.edu