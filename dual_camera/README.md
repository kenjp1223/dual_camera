# Dual Camera Animal Behavior Recording System

## Overview
This project enables remote video recording of animal behavior using multiple Raspberry Pis, each with two USB cameras, controlled from a central PC. The PC can trigger recordings, set parameters, and monitor status for each Pi. An optional GUI is provided for ease of use.

---

## Folder Structure
```
dual_camera/
  pi/
    camera_server.py         # REST API server for Pi
    dual_camera_record.py    # Dual camera video recording script
  pc/
    controller.py            # CLI controller for PC
    gui.py                   # GUI controller for PC
```

---

## Requirements
- **Raspberry Pi:**
  - Python 3
  - `opencv-python` (`pip install opencv-python`)
  - `flask` (`pip install flask`)
- **PC:**
  - Python 3
  - `requests` (`pip install requests`)
  - `tkinter` (usually included with Python)

---

## Installing Python Environments and Packages on Raspberry Pi

1. **Update your system:**
   ```bash
   sudo apt update
   sudo apt upgrade
   ```
2. **Install Python 3 and pip (if not already installed):**
   ```bash
   sudo apt install python3 python3-pip
   ```
3. **(Recommended) Create a virtual environment:**
   This keeps your project dependencies isolated.
   ```bash
   sudo apt install python3-venv
   python3 -m venv dualcam-env
   source dualcam-env/bin/activate
   ```
   - To deactivate:
     ```bash
     deactivate
     ```
4. **Install required Python packages:**
   From within your (activated) environment:
   ```bash
   pip install flask opencv-python
   ```
   - If you get errors with `opencv-python`, try:
     ```bash
     pip install opencv-contrib-python
     ```
   - For some Pi models, you may need to install system dependencies:
     ```bash
     sudo apt install libatlas-base-dev libjasper-dev libqtgui4 python3-pyqt5 libqt4-test
     ```
5. **(Optional) List all dependencies in a requirements file:**
   Create a `requirements.txt`:
   ```
   flask
   opencv-python
   ```
   Then install with:
   ```bash
   pip install -r requirements.txt
   ```

---

## Setup
### On Each Raspberry Pi
1. Connect two USB cameras.
2. Copy the `pi/` folder to the Pi.
3. Install dependencies:
   ```bash
   pip install flask opencv-python
   ```
4. Start the camera server:
   ```bash
   python3 camera_server.py
   ```
   - The server listens on port 5000 by default.

### On the PC
1. Copy the `pc/` folder to your PC.
2. Install dependencies:
   ```bash
   pip install requests
   ```
   - `tkinter` is usually included with Python. If not, install it via your OS package manager.
3. Edit the `PI_CONFIG` list in `controller.py` and `gui.py` to match your Pi IP addresses.

---

## Usage
### Command Line Controller
Run from the `pc/` directory:
```bash
python controller.py
```
- Follow prompts to select a Pi, set duration/fps, and start/stop recording.

### GUI Controller
Run from the `pc/` directory:
```bash
python gui.py
```
- Use the dropdown to select a Pi, set parameters, and control recording with buttons.

---

## Workflow
1. Start the server on each Pi.
2. Use the PC controller (CLI or GUI) to:
   - Select a Pi
   - Set recording parameters
   - Start/stop recording
   - Check status
3. Videos are saved on the Pi SD card as `camera0_*.avi` and `camera1_*.avi`.

---

## Notes
- Ensure the PC and all Pis are on the same network.
- The video preview feature is not yet implemented.
- For troubleshooting, check the debug/info/error messages in the CLI or GUI. 