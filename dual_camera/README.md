# Dual Camera Raspberry Pi Setup (multi-device ready)

This guide describes how to set up and control multiple Raspberry Pi devices (e.g., `xxlab1`, `xxlab2`, etc.) for synchronized dual USB camera recording using `ffmpeg`. Recording is triggered remotely from a host PC over Ethernet or Wi-Fi.

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

Edit the file:

```bash
sudo nano /etc/dhcpcd.conf
```

Append (change IP for each Pi):

```ini
interface eth0
static ip_address=192.168.2.11/24  # Use 192.168.2.12, .13, etc. for other Pis
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
sudo apt update && sudo apt install git python3-venv ffmpeg -y
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
pip install flask
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
cd /home/stuberlab1/dual_camera/dual_camera/pi
source dualcam-venv/bin/activate

python3 dual_camera_ffmpeg_record.py \
  --duration 10 \
  --fps 100 \
  --width 640 \
  --height 480 \
  --output_dir /home/stuberlab1/captures
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
cd /home/stuberlab1/dual_camera/dual_camera/pi
source dualcam-venv/bin/activate
python3 camera_server.py
```

Look for:

```
Running on http://192.168.2.11:5000
```

### ✅ Trigger Recording from PC

#### PowerShell (Windows):

```powershell
curl -X POST http://192.168.2.11:5000/start_recording ^
  -H "Content-Type: application/json" ^
  -d "{\"duration\": 10, \"fps\": 100, \"width\": 640, \"height\": 480}"
```

#### Linux/macOS/WSL:

```bash
curl -X POST http://192.168.2.11:5000/start_recording \
  -H "Content-Type: application/json" \
  -d '{"duration": 10, "fps": 100, "width": 640, "height": 480}'
```

---

## 5. Optional: Autostart Script

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

## ✅ Done

You now have a multi-device recording system where each Pi:

* Has a unique name and static IP
* Can be triggered remotely over Ethernet or Wi-Fi
* Records synced dual-camera video to local storage

Feel free to extend with:

* Auto-start with systemd
* Real-time status feedback
* Parallel multi-Pi trigger script from the PC

PRs and suggestions welcome!


Kentaro Ishii (University of Washington)
ken1223@uw.edu