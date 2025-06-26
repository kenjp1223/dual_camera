# Dual Camera Raspberry Pi Setup (multi-device ready)

This guide describes how to set up and control multiple Raspberry Pi devices (e.g., `xxlab1`, `xxlab2`, etc.) for synchronized dual USB camera recording using `ffmpeg`. Recording is triggered remotely from a host PC over Ethernet or Wi-Fi using a comprehensive GUI interface.

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

## 3. Running the Recording Script Manually

### ✅ Test Recording

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

---

## 6. Post-Processing and Video Management

### ✅ Fast Video Concatenation

The system includes a high-performance post-processing script that can:

#### **Concatenation Options**
- **Vertical Layout**: cam0 on top, cam1 on bottom
- **Horizontal Layout**: cam0 on left, cam1 on right
- **Camera Rotation**: Rotate individual cameras (0°, 90°, 180°, 270°)
- **Preview Snapshots**: Quick JPG previews to check orientation before processing

#### **Performance Optimizations**
- **Copy Mode**: Fast concatenation when videos have same properties
- **Hardware Acceleration**: Uses Raspberry Pi hardware encoder when available
- **Ultrafast Encoding**: Optimized settings for maximum speed
- **Progress Tracking**: Real-time progress updates during processing

### ✅ Using Post-Processing

#### **Via GUI**
1. Click "Post Process" on any Pi tab
2. Select recording folder containing cam0.mp4 and cam1.mp4
3. Choose layout (vertical/horizontal)
4. Set camera rotations if needed
5. Click "Create Preview" to check orientation
6. Click "Process Videos" for final concatenation

#### **Via Command Line**

```bash
# Basic concatenation
python post_process_videos.py /path/to/recording/folder

# With rotation (cam0 rotated 180°, cam1 normal)
python post_process_videos.py /path/to/folder --cam0-rotation 180

# Create preview snapshot
python post_process_videos.py /path/to/folder --preview

# Horizontal layout with hardware acceleration
python post_process_videos.py /path/to/folder --layout horizontal --super-fast

# List available recording folders
python post_process_videos.py /path/to/captures --list-folders
```

### ✅ Output Files

- **Concatenated Videos**: `{folder_name}_concatenated_fast_{layout}.mp4`
- **Rotated Videos**: `{folder_name}_concatenated_fast_r{rot0}_{rot1}_{layout}.mp4`
- **Preview Snapshots**: `{folder_name}_preview_{layout}.jpg`
- **Hardware Accelerated**: `{folder_name}_concatenated_superfast_{layout}.mp4`

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
6. **Post-Processing**: Concatenate videos with rotation correction
7. **Analysis**: Use the final concatenated videos for analysis

### ✅ Troubleshooting

#### **Camera Orientation Issues**
- Use "Create Preview" to check camera orientation
- Apply rotation (typically 180° for upside-down cameras)
- Common: cam0 rotation 180° for flipped top camera

#### **Network Connectivity**
- Ensure Pis are on 192.168.2.x network
- Check firewall settings on PC
- Verify Pi camera server is running on port 5000

#### **Performance Issues**
- Use "Super Fast" mode for hardware acceleration
- Ensure sufficient storage space on Pis
- Check USB camera compatibility with v4l2

---

## ✅ Done

You now have a complete multi-device recording system where each Pi:

* Has a unique name and static IP
* Can be controlled remotely via PC GUI
* Records synced dual-camera video to local storage
* Supports real-time monitoring and post-processing
* Includes camera rotation and preview capabilities

The system scales from 1-2 Pis to 8+ devices with the tabbed interface, making it suitable for both small experiments and large-scale data collection.

Feel free to extend with:

* Auto-start with systemd
* Real-time video streaming
* Advanced post-processing filters
* Database integration for metadata

PRs and suggestions welcome!


Kentaro Ishii (University of Washington)
ken1223@uw.edu