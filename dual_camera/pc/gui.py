import tkinter as tk
from tkinter import ttk, messagebox, simpledialog, filedialog
from PIL import Image, ImageTk
import requests
import json
import os
import io
import socket
import threading
import subprocess
import platform

CONFIG_FILE = 'pi_config.json'

# Load or initialize Pi config
if os.path.exists(CONFIG_FILE):
    try:
        with open(CONFIG_FILE, 'r') as f:
            PI_CONFIG = json.load(f)
    except (json.JSONDecodeError, ValueError) as e:
        print(f"Warning: Corrupted config file detected: {e}")
        # Create backup of corrupted file
        backup_file = f"{CONFIG_FILE}.backup"
        try:
            import shutil
            shutil.copy2(CONFIG_FILE, backup_file)
            print(f"Backup created: {backup_file}")
        except Exception as backup_error:
            print(f"Failed to create backup: {backup_error}")
        PI_CONFIG = []
else:
    PI_CONFIG = []

class NetworkScanner:
    def __init__(self):
        self.found_pis = []
    
    def get_ethernet_interface(self):
        """Get the ethernet interface IP address"""
        try:
            # On Windows, ethernet interfaces often start with 'Ethernet' or have specific names
            if platform.system() == "Windows":
                # Try to get ethernet interface IP
                result = subprocess.run(['ipconfig'], capture_output=True, text=True)
                lines = result.stdout.split('\n')
                for i, line in enumerate(lines):
                    if 'Ethernet adapter' in line and '192.168.2.' in line:
                        # Look for IPv4 address in next few lines
                        for j in range(i+1, min(i+10, len(lines))):
                            if 'IPv4' in lines[j] and '192.168.2.' in lines[j]:
                                ip = lines[j].split(':')[-1].strip()
                                return ip
            else:
                # Linux/macOS approach
                result = subprocess.run(['ip', 'route'], capture_output=True, text=True)
                for line in result.stdout.split('\n'):
                    if '192.168.2.' in line:
                        parts = line.split()
                        if len(parts) >= 3:
                            return parts[2]  # src IP
        except:
            pass
        return None
    
    def check_pi_server(self, ip, port=5000):
        """Check if an IP is running the Pi camera server"""
        try:
            url = f"http://{ip}:{port}/status"
            response = requests.get(url, timeout=2)
            if response.status_code == 200:
                return True
        except:
            pass
        return False
    
    def scan_direct_ethernet(self, progress_callback=None):
        """Scan for Pis connected via direct ethernet (192.168.2.x range)"""
        self.found_pis = []
        
        # Based on README, Pis use 192.168.2.11, 192.168.2.12, etc.
        # Scan a reasonable range: 192.168.2.11 to 192.168.2.20
        base_ip = "192.168.2"
        
        if progress_callback:
            progress_callback("Scanning direct ethernet connections (192.168.2.x)...")
        
        # Try common Pi hostnames first (fast)
        pi_hostnames = [
            "xxlab1.local",  # Based on README naming convention
            "xxlab2.local",
            "raspberrypi.local",
            "pi.local"
        ]
        
        for hostname in pi_hostnames:
            try:
                if progress_callback:
                    progress_callback(f"Trying hostname: {hostname}")
                ip = socket.gethostbyname(hostname)
                if self.check_pi_server(ip):
                    self.found_pis.append({
                        'name': f'Pi-{hostname}',
                        'host': f'http://{ip}:5000',
                        'discovered': True
                    })
                    if progress_callback:
                        progress_callback(f"Found Pi at {hostname} ({ip})")
            except:
                pass
        
        # Scan specific IP range (192.168.2.11 to 192.168.2.20)
        for i in range(11, 21):
            ip = f"{base_ip}.{i}"
            if progress_callback:
                progress_callback(f"Scanning {ip}...")
            
            # Quick port check first
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(1)
                result = sock.connect_ex((ip, 5000))
                sock.close()
                
                if result == 0:  # Port is open
                    if self.check_pi_server(ip):
                        self.found_pis.append({
                            'name': f'Pi-{ip}',
                            'host': f'http://{ip}:5000',
                            'discovered': True
                        })
                        if progress_callback:
                            progress_callback(f"Found Pi at {ip}")
            except:
                pass
        
        return self.found_pis
    
    def scan_network(self, progress_callback=None):
        """Main scanning method - optimized for direct ethernet connections"""
        return self.scan_direct_ethernet(progress_callback)

class PiTab:
    def __init__(self, parent, pi_data, pi_index, gui_instance):
        self.parent = parent
        self.pi_data = pi_data
        self.pi_index = pi_index
        self.gui = gui_instance
        self.frame = ttk.Frame(parent)
        self.setup_tab()
    
    def setup_tab(self):
        # Main layout with two columns
        left_frame = ttk.Frame(self.frame)
        left_frame.pack(side='left', fill='both', expand=True, padx=10, pady=10)
        
        right_frame = ttk.Frame(self.frame)
        right_frame.pack(side='right', fill='both', expand=True, padx=10, pady=10)
        
        # Left side: Controls
        self.setup_controls(left_frame)
        
        # Right side: Camera snapshots
        self.setup_snapshots(right_frame)
    
    def setup_controls(self, parent):
        # Pi info header
        info_frame = ttk.LabelFrame(parent, text=f"Pi: {self.pi_data.get('name', self.pi_data.get('username', 'Unknown'))}")
        info_frame.pack(fill='x', pady=(0, 10))
        
        ttk.Label(info_frame, text=f"Host: {self.pi_data['host']}").pack(anchor='w', padx=5, pady=2)
        ttk.Label(info_frame, text=f"User: {self.pi_data.get('username', 'unknown')}").pack(anchor='w', padx=5, pady=2)
        
        # Recording parameters
        param_frame = ttk.LabelFrame(parent, text="Recording Parameters")
        param_frame.pack(fill='x', pady=(0, 10))
        
        # Row 1: Duration, FPS, Subject
        row1 = ttk.Frame(param_frame)
        row1.pack(fill='x', padx=5, pady=5)
        
        ttk.Label(row1, text='Duration (s):').grid(row=0, column=0, sticky='w')
        self.duration_var = tk.StringVar(value=self.pi_data.get('duration', '300'))
        ttk.Entry(row1, textvariable=self.duration_var, width=8).grid(row=0, column=1, sticky='w', padx=(5, 15))
        
        ttk.Label(row1, text='FPS:').grid(row=0, column=2, sticky='w')
        self.fps_var = tk.StringVar(value=self.pi_data.get('fps', '100'))
        ttk.Entry(row1, textvariable=self.fps_var, width=8).grid(row=0, column=3, sticky='w', padx=(5, 15))
        
        ttk.Label(row1, text='Subject:').grid(row=0, column=4, sticky='w')
        self.subject_var = tk.StringVar(value=self.pi_data.get('subject', 'default'))
        ttk.Entry(row1, textvariable=self.subject_var, width=12).grid(row=0, column=5, sticky='w', padx=5)
        
        # Row 2: Width, Height
        row2 = ttk.Frame(param_frame)
        row2.pack(fill='x', padx=5, pady=5)
        
        ttk.Label(row2, text='Width:').grid(row=0, column=0, sticky='w')
        self.width_var = tk.StringVar(value=self.pi_data.get('width', '640'))
        ttk.Entry(row2, textvariable=self.width_var, width=8).grid(row=0, column=1, sticky='w', padx=(5, 15))
        
        ttk.Label(row2, text='Height:').grid(row=0, column=2, sticky='w')
        self.height_var = tk.StringVar(value=self.pi_data.get('height', '480'))
        ttk.Entry(row2, textvariable=self.height_var, width=8).grid(row=0, column=3, sticky='w', padx=(5, 15))
        
        # Row 3: Camera devices
        row3 = ttk.Frame(param_frame)
        row3.pack(fill='x', padx=5, pady=5)
        
        ttk.Label(row3, text='Cam0:').grid(row=0, column=0, sticky='w')
        self.cam0_var = tk.StringVar(value=self.pi_data.get('cam0', '/dev/video0'))
        self.cam0_combo = ttk.Combobox(row3, textvariable=self.cam0_var, width=12)
        self.cam0_combo.grid(row=0, column=1, sticky='w', padx=(5, 15))
        
        ttk.Label(row3, text='Cam1:').grid(row=0, column=2, sticky='w')
        self.cam1_var = tk.StringVar(value=self.pi_data.get('cam1', '/dev/video2'))
        self.cam1_combo = ttk.Combobox(row3, textvariable=self.cam1_var, width=12)
        self.cam1_combo.grid(row=0, column=3, sticky='w', padx=5)
        
        # Row 4: Output directory
        row4 = ttk.Frame(param_frame)
        row4.pack(fill='x', padx=5, pady=5)
        
        ttk.Label(row4, text='Output Dir:').grid(row=0, column=0, sticky='w')
        default_output = self.pi_data.get('output_dir')
        if not default_output:
            username = self.pi_data.get('username', 'pi')
            default_output = f'/home/{username}/captures'
        self.output_dir_var = tk.StringVar(value=default_output)
        ttk.Entry(row4, textvariable=self.output_dir_var, width=30).grid(row=0, column=1, columnspan=3, sticky='w', padx=5)
        
        # Control buttons
        button_frame = ttk.LabelFrame(parent, text="Controls")
        button_frame.pack(fill='x', pady=(0, 10))
        
        # First row of buttons
        btn_row1 = ttk.Frame(button_frame)
        btn_row1.pack(fill='x', padx=5, pady=5)
        
        ttk.Button(btn_row1, text='Start Recording', command=self.start_recording).grid(row=0, column=0, padx=2)
        ttk.Button(btn_row1, text='Stop Recording', command=self.stop_recording).grid(row=0, column=1, padx=2)
        ttk.Button(btn_row1, text='Check Status', command=self.check_status).grid(row=0, column=2, padx=2)
        ttk.Button(btn_row1, text='Take Snapshot', command=self.take_snapshot).grid(row=0, column=3, padx=2)
        
        # Second row of buttons
        btn_row2 = ttk.Frame(button_frame)
        btn_row2.pack(fill='x', padx=5, pady=5)
        
        ttk.Button(btn_row2, text='Detect Cameras', command=self.detect_cameras).grid(row=0, column=0, padx=2)
        ttk.Button(btn_row2, text='Post Process', command=self.post_process).grid(row=0, column=1, padx=2)
        ttk.Button(btn_row2, text='Save Config', command=self.save_config).grid(row=0, column=2, padx=2)
        ttk.Button(btn_row2, text='Edit Pi', command=self.edit_pi).grid(row=0, column=3, padx=2)
        
        # Third row of buttons
        btn_row3 = ttk.Frame(button_frame)
        btn_row3.pack(fill='x', padx=5, pady=5)
        
        ttk.Button(btn_row3, text='Remove Pi', command=self.remove_pi).grid(row=0, column=0, padx=2)
    
    def setup_snapshots(self, parent):
        snapshot_frame = ttk.LabelFrame(parent, text="Camera Snapshots")
        snapshot_frame.pack(fill='both', expand=True)
        
        # Larger snapshot display
        self.cam0_label = ttk.Label(snapshot_frame, text="Cam0: No image", relief='solid', borderwidth=2)
        self.cam0_label.pack(side='top', fill='both', expand=True, padx=10, pady=10)
        
        self.cam1_label = ttk.Label(snapshot_frame, text="Cam1: No image", relief='solid', borderwidth=2)
        self.cam1_label.pack(side='bottom', fill='both', expand=True, padx=10, pady=10)
        
        # Store references in pi_data for snapshot updates
        self.pi_data['cam0_label'] = self.cam0_label
        self.pi_data['cam1_label'] = self.cam1_label
    
    def start_recording(self):
        self.gui.start_recording(self.pi_index, self.duration_var, self.fps_var, self.subject_var, 
                               self.width_var, self.height_var, self.cam0_var, self.cam1_var, self.output_dir_var)
    
    def stop_recording(self):
        self.gui.stop_recording(self.pi_index)
    
    def check_status(self):
        self.gui.check_status(self.pi_index)
    
    def take_snapshot(self):
        self.gui.take_snapshot(self.pi_index)
    
    def detect_cameras(self):
        self.gui.detect_cameras(self.pi_index)
    
    def save_config(self):
        self.gui.save_pi_config(self.pi_index, self.duration_var, self.fps_var, self.subject_var,
                              self.width_var, self.height_var, self.cam0_var, self.cam1_var, self.output_dir_var)
    
    def edit_pi(self):
        self.gui.edit_pi(self.pi_index)
    
    def remove_pi(self):
        self.gui.remove_pi(self.pi_index)

    def post_process(self):
        """Open post-processing dialog for this Pi"""
        self.gui.post_process_videos(self.pi_index)

class PiControllerGUI:
    def __init__(self, root):
        self.root = root
        self.root.title('Multi-Raspberry Pi Controller')
        self.root.geometry("1200x800")  # Larger default window
        self.pis = PI_CONFIG.copy()
        self.tabs = {}
        self.notebook = None
        self.scanner = NetworkScanner()
        self.setup_menu()
        self.setup_notebook()
        self.refresh_gui()

    def setup_menu(self):
        menubar = tk.Menu(self.root)
        pi_menu = tk.Menu(menubar, tearoff=0)
        pi_menu.add_command(label='Add Pi', command=self.add_pi)
        pi_menu.add_command(label='Quick Scan', command=self.quick_scan)
        pi_menu.add_separator()
        pi_menu.add_command(label='Save All Config', command=self.save_config)
        pi_menu.add_command(label='Load Config', command=self.load_config)
        menubar.add_cascade(label='Pis', menu=pi_menu)
        self.root.config(menu=menubar)

    def setup_notebook(self):
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill='both', expand=True, padx=5, pady=5)

    def check_pi_server(self, ip, port=5000):
        """Check if an IP is running the Pi camera server"""
        try:
            url = f"http://{ip}:{port}/status"
            response = requests.get(url, timeout=2)
            if response.status_code == 200:
                return True
        except:
            pass
        return False

    def get_pi_username(self, host):
        """Get the username from a Pi"""
        try:
            url = f"{host}/username"
            response = requests.get(url, timeout=2)
            if response.status_code == 200:
                return response.json().get('username', 'unknown')
        except:
            pass
        return 'unknown'

    def get_pi_cameras(self, host):
        """Get available cameras from a Pi"""
        try:
            url = f"{host}/cameras"
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                return response.json().get('cameras', [])
        except:
            pass
        return []

    def quick_scan(self):
        """Simple scan for common Pi addresses"""
        def scan_thread():
            # Create progress window
            progress_window = tk.Toplevel(self.root)
            progress_window.title("Quick Pi Scan")
            progress_window.geometry("300x150")
            progress_window.transient(self.root)
            progress_window.grab_set()
            
            progress_label = ttk.Label(progress_window, text="Checking common Pi addresses...")
            progress_label.pack(pady=10)
            
            progress_text = tk.Text(progress_window, height=6, width=40)
            progress_text.pack(pady=10, padx=10)
            
            def update_progress(message):
                progress_text.insert('end', message + '\n')
                progress_text.see('end')
                progress_window.update()
            
            found_pis = []
            
            # Common Pi addresses to try
            addresses_to_try = [
                "192.168.2.11",
                "192.168.2.12", 
                "192.168.2.13",
                "192.168.2.14",
                "192.168.2.15",
                "raspberrypi.local",
                "xxlab1.local",
                "xxlab2.local"
            ]
            
            for addr in addresses_to_try:
                update_progress(f"Checking {addr}...")
                
                try:
                    if self.check_pi_server(addr):
                        host = f"http://{addr}:5000"
                        username = self.get_pi_username(host)
                        found_pis.append({
                            'name': f'Pi-{username}',
                            'host': host,
                            'username': username,
                            'discovered': True,
                            'output_dir': f'/home/{username}/captures'
                        })
                        update_progress(f"Found Pi at {addr} (user: {username})")
                except:
                    pass
            
            progress_window.destroy()
            
            if found_pis:
                self.show_discovered_pis(found_pis)
            else:
                messagebox.showinfo("Scan Complete", "No Raspberry Pis found. Try adding them manually.")
        
        # Run scan in separate thread
        thread = threading.Thread(target=scan_thread)
        thread.daemon = True
        thread.start()

    def show_discovered_pis(self, found_pis):
        """Show dialog to select which discovered Pis to add"""
        dialog = tk.Toplevel(self.root)
        dialog.title("Discovered Raspberry Pis")
        dialog.geometry("400x300")
        dialog.transient(self.root)
        dialog.grab_set()
        
        ttk.Label(dialog, text="Select Pis to add:").pack(pady=10)
        
        # Create checkboxes for each found Pi
        pi_vars = []
        for pi in found_pis:
            var = tk.BooleanVar(value=True)
            pi_vars.append(var)
            ttk.Checkbutton(dialog, text=f"{pi['name']} ({pi['host']})", variable=var).pack(anchor='w', padx=20)
        
        def add_selected():
            added_count = 0
            for i, var in enumerate(pi_vars):
                if var.get():
                    # Check if Pi already exists
                    pi_exists = any(p['host'] == found_pis[i]['host'] for p in self.pis)
                    if not pi_exists:
                        self.pis.append(found_pis[i])
                        added_count += 1
            
            if added_count > 0:
                self.refresh_gui()
                messagebox.showinfo("Add Pis", f"Added {added_count} new Raspberry Pi(s).")
            else:
                messagebox.showinfo("Add Pis", "No new Pis were added (they may already exist).")
            
            dialog.destroy()
        
        ttk.Button(dialog, text="Add Selected", command=add_selected).pack(pady=10)
        ttk.Button(dialog, text="Cancel", command=dialog.destroy).pack(pady=5)

    def detect_cameras(self, idx):
        """Detect available cameras on a specific Pi"""
        pi = self.pis[idx]
        
        def detect_thread():
            try:
                cameras = self.get_pi_cameras(pi['host'])
                
                if cameras:
                    self.show_camera_selection(idx, cameras)
                else:
                    messagebox.showwarning("Camera Detection", f"No cameras found on {pi.get('name', 'Pi')}")
                    
            except Exception as e:
                messagebox.showerror("Camera Detection Error", f"Failed to detect cameras: {str(e)}")
        
        thread = threading.Thread(target=detect_thread)
        thread.daemon = True
        thread.start()

    def show_camera_selection(self, idx, cameras):
        """Show dialog to select cameras for cam0 and cam1"""
        pi = self.pis[idx]
        
        dialog = tk.Toplevel(self.root)
        dialog.title(f"Select Cameras - {pi.get('name', 'Pi')}")
        dialog.geometry("500x400")
        dialog.transient(self.root)
        dialog.grab_set()
        
        ttk.Label(dialog, text="Available cameras:").pack(pady=10)
        
        # Show available cameras
        camera_text = tk.Text(dialog, height=8, width=60)
        camera_text.pack(pady=10, padx=10)
        
        for cam in cameras:
            if cam.get('working', False):
                info = f"✓ {cam['device']} - {cam.get('width', '?')}x{cam.get('height', '?')} @ {cam.get('fps', '?')}fps\n"
            else:
                info = f"✗ {cam['device']} - Not working\n"
            camera_text.insert('end', info)
        
        camera_text.config(state='disabled')
        
        # Camera selection
        selection_frame = ttk.Frame(dialog)
        selection_frame.pack(pady=10)
        
        ttk.Label(selection_frame, text="Cam0:").grid(row=0, column=0, sticky='w', padx=5)
        cam0_var = tk.StringVar(value=pi.get('cam0', '/dev/video0'))
        cam0_combo = ttk.Combobox(selection_frame, textvariable=cam0_var, state='readonly')
        working_cameras = [cam['device'] for cam in cameras if cam.get('working', False)]
        cam0_combo['values'] = working_cameras
        cam0_combo.grid(row=0, column=1, padx=5)
        
        ttk.Label(selection_frame, text="Cam1:").grid(row=1, column=0, sticky='w', padx=5)
        cam1_var = tk.StringVar(value=pi.get('cam1', '/dev/video2'))
        cam1_combo = ttk.Combobox(selection_frame, textvariable=cam1_var, state='readonly')
        cam1_combo['values'] = working_cameras
        cam1_combo.grid(row=1, column=1, padx=5)
        
        def apply_selection():
            pi['cam0'] = cam0_var.get()
            pi['cam1'] = cam1_var.get()
            self.refresh_gui()
            dialog.destroy()
            messagebox.showinfo("Camera Selection", f"Cameras updated for {pi.get('name', 'Pi')}")
        
        ttk.Button(dialog, text="Apply Selection", command=apply_selection).pack(pady=10)
        ttk.Button(dialog, text="Cancel", command=dialog.destroy).pack(pady=5)

    def refresh_gui(self):
        # Clear existing tabs
        for tab_id in self.notebook.tabs():
            self.notebook.forget(tab_id)
        self.tabs.clear()
        
        # Create tabs for each Pi
        for idx, pi in enumerate(self.pis):
            tab = PiTab(self.notebook, pi, idx, self)
            tab_name = pi.get('name', pi.get('username', f'Pi-{idx}'))
            self.notebook.add(tab.frame, text=tab_name)
            self.tabs[idx] = tab
        
        # If no Pis, show a welcome tab
        if not self.pis:
            welcome_frame = ttk.Frame(self.notebook)
            welcome_label = ttk.Label(welcome_frame, text="No Raspberry Pis configured.\nUse 'Pis' menu to add or scan for Pis.", 
                                    font=('Arial', 14), justify='center')
            welcome_label.pack(expand=True, fill='both', padx=50, pady=50)
            self.notebook.add(welcome_frame, text="Welcome")

    def take_snapshot(self, idx):
        """Take snapshots from both cameras and display them"""
        pi = self.pis[idx]
        
        def snapshot_thread():
            try:
                # Take snapshot from camera 0
                cam0_device = pi.get('cam0', '/dev/video0')
                url_cam0 = f"{pi['host']}/snapshot/{cam0_device.replace('/dev/video', '')}"
                resp_cam0 = requests.get(url_cam0, timeout=5)
                if resp_cam0.status_code == 200:
                    img_data = resp_cam0.content
                    image = Image.open(io.BytesIO(img_data))
                    image.thumbnail((320, 240))  # Larger thumbnails
                    photo = ImageTk.PhotoImage(image)
                    pi['cam0_label'].config(image=photo, text="")
                    pi['cam0_label'].image = photo
                else:
                    pi['cam0_label'].config(text=f"Cam0: Error")
                
                # Take snapshot from camera 1
                cam1_device = pi.get('cam1', '/dev/video2')
                url_cam1 = f"{pi['host']}/snapshot/{cam1_device.replace('/dev/video', '')}"
                resp_cam1 = requests.get(url_cam1, timeout=5)
                if resp_cam1.status_code == 200:
                    img_data = resp_cam1.content
                    image = Image.open(io.BytesIO(img_data))
                    image.thumbnail((320, 240))  # Larger thumbnails
                    photo = ImageTk.PhotoImage(image)
                    pi['cam1_label'].config(image=photo, text="")
                    pi['cam1_label'].image = photo
                else:
                    pi['cam1_label'].config(text=f"Cam1: Error")
                    
            except Exception as e:
                messagebox.showerror("Snapshot Error", f"Failed to take snapshots: {str(e)}")
        
        thread = threading.Thread(target=snapshot_thread)
        thread.daemon = True
        thread.start()

    def save_pi_config(self, idx, duration_var, fps_var, subject_var, width_var, height_var, cam0_var, cam1_var, output_dir_var):
        """Save configuration for a specific Pi"""
        pi = self.pis[idx]
        pi.update({
            'duration': duration_var.get(),
            'fps': fps_var.get(),
            'subject': subject_var.get(),
            'width': width_var.get(),
            'height': height_var.get(),
            'cam0': cam0_var.get(),
            'cam1': cam1_var.get(),
            'output_dir': output_dir_var.get()
        })
        self.save_config()
        messagebox.showinfo("Save Config", f"Configuration saved for {pi.get('name', 'Pi')}")

    def add_pi(self):
        name = simpledialog.askstring('Add Pi', 'Enter Pi name:')
        host = simpledialog.askstring('Add Pi', 'Enter Pi host (e.g., http://192.168.2.11:5000):')
        if name and host:
            # Try to get username
            username = self.get_pi_username(host)
            self.pis.append({
                'name': name,
                'host': host,
                'username': username,
                'duration': '300',
                'fps': '100',
                'subject': 'default',
                'width': '640',
                'height': '480',
                'cam0': '/dev/video0',
                'cam1': '/dev/video2',
                'output_dir': f'/home/{username}/captures'
            })
            self.refresh_gui()

    def edit_pi(self, idx):
        pi = self.pis[idx]
        name = simpledialog.askstring('Edit Pi', 'Edit Pi name:', initialvalue=pi.get('name', ''))
        host = simpledialog.askstring('Edit Pi', 'Edit Pi host:', initialvalue=pi['host'])
        if name and host:
            pi['name'] = name
            pi['host'] = host
            # Update username and output directory
            username = self.get_pi_username(host)
            pi['username'] = username
            # Update output directory if it's still using the old default
            if pi.get('output_dir') == '/home/pi/captures' or not pi.get('output_dir'):
                pi['output_dir'] = f'/home/{username}/captures'
            self.refresh_gui()

    def remove_pi(self, idx):
        if messagebox.askyesno('Remove Pi', f"Remove {self.pis[idx].get('name', 'Pi')}?"):
            self.pis.pop(idx)
            self.refresh_gui()

    def save_config(self):
        # Create a clean copy of pis data without Tkinter widgets
        clean_pis = []
        for pi in self.pis:
            clean_pi = {}
            for key, value in pi.items():
                # Skip Tkinter widgets and other non-serializable objects
                if not key.startswith('cam') or not key.endswith('_label'):
                    clean_pi[key] = value
            clean_pis.append(clean_pi)
        
        with open(CONFIG_FILE, 'w') as f:
            json.dump(clean_pis, f, indent=2)
        messagebox.showinfo('Save Config', 'Configuration saved.')

    def load_config(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r') as f:
                    self.pis = json.load(f)
                self.refresh_gui()
                messagebox.showinfo('Load Config', 'Configuration loaded.')
            except (json.JSONDecodeError, ValueError) as e:
                messagebox.showerror('Load Config', f'Error loading config: {e}')
        else:
            messagebox.showerror('Load Config', 'No config file found.')

    def start_recording(self, idx, duration_var, fps_var, subject_var, width_var, height_var, cam0_var, cam1_var, output_dir_var):
        pi = self.pis[idx]
        try:
            duration = int(duration_var.get())
            fps = int(fps_var.get())
            width = int(width_var.get())
            height = int(height_var.get())
        except ValueError:
            messagebox.showerror('Input Error', 'Duration, FPS, width, and height must be integers.')
            return
        
        url = f"{pi['host']}/start_recording"
        payload = {
            'duration': duration,
            'fps': fps,
            'subject': subject_var.get(),
            'width': width,
            'height': height,
            'cam0': cam0_var.get(),
            'cam1': cam1_var.get(),
            'output_dir': output_dir_var.get()
        }
        
        try:
            resp = requests.post(url, json=payload, timeout=5)
            resp.raise_for_status()
            result = resp.json()
            messagebox.showinfo('Start Recording', f"{result.get('status', 'Started')}\nFolder: {result.get('folder', 'Unknown')}")
        except Exception as e:
            messagebox.showerror('Start Recording', str(e))

    def stop_recording(self, idx):
        pi = self.pis[idx]
        url = f"{pi['host']}/stop_recording"
        try:
            resp = requests.post(url, timeout=5)
            resp.raise_for_status()
            messagebox.showinfo('Stop Recording', f"{resp.json()}")
        except Exception as e:
            messagebox.showerror('Stop Recording', str(e))

    def check_status(self, idx):
        pi = self.pis[idx]
        url = f"{pi['host']}/status"
        try:
            resp = requests.get(url, timeout=5)
            resp.raise_for_status()
            messagebox.showinfo('Status', f"{resp.json()}")
        except Exception as e:
            messagebox.showerror('Status', str(e))

    def post_process_videos(self, idx):
        """Post-process videos for a specific Pi"""
        pi = self.pis[idx]
        
        # Create post-processing dialog
        dialog = tk.Toplevel(self.root)
        dialog.title(f"Post Process Videos - {pi.get('name', 'Pi')}")
        dialog.geometry("700x600")
        dialog.transient(self.root)
        dialog.grab_set()
        
        # Get recording folders from Pi
        def get_recording_folders():
            try:
                # Use the output directory from Pi config
                output_dir = pi.get('output_dir', f'/home/{pi.get("username", "pi")}/captures')
                
                # For now, we'll show a file dialog to select the folder
                # In the future, we could fetch the folder list from the Pi
                folder = filedialog.askdirectory(
                    title=f"Select recording folder for {pi.get('name', 'Pi')}",
                    initialdir=output_dir
                )
                return folder
            except Exception as e:
                messagebox.showerror("Error", f"Could not access recording folders: {e}")
                return None
        
        # Folder selection
        folder_frame = ttk.LabelFrame(dialog, text="Recording Folder")
        folder_frame.pack(fill='x', padx=10, pady=10)
        
        folder_var = tk.StringVar()
        ttk.Label(folder_frame, text="Selected folder:").pack(anchor='w', padx=5, pady=5)
        
        folder_entry_frame = ttk.Frame(folder_frame)
        folder_entry_frame.pack(fill='x', padx=5, pady=5)
        
        folder_entry = ttk.Entry(folder_entry_frame, textvariable=folder_var, width=50)
        folder_entry.pack(side='left', fill='x', expand=True)
        
        def browse_folder():
            folder = filedialog.askdirectory(title="Select recording folder")
            if folder:
                folder_var.set(folder)
        
        ttk.Button(folder_entry_frame, text="Browse", command=browse_folder).pack(side='right', padx=(5, 0))
        
        # Processing options
        options_frame = ttk.LabelFrame(dialog, text="Processing Options")
        options_frame.pack(fill='x', padx=10, pady=10)
        
        # Layout selection
        layout_frame = ttk.Frame(options_frame)
        layout_frame.pack(fill='x', padx=5, pady=5)
        
        ttk.Label(layout_frame, text="Layout:").grid(row=0, column=0, sticky='w')
        layout_var = tk.StringVar(value='vertical')
        ttk.Radiobutton(layout_frame, text="Vertical (cam0 on top, cam1 on bottom)", 
                       variable=layout_var, value='vertical').grid(row=0, column=1, sticky='w', padx=10)
        ttk.Radiobutton(layout_frame, text="Horizontal (cam0 left, cam1 right)", 
                       variable=layout_var, value='horizontal').grid(row=1, column=1, sticky='w', padx=10)
        
        # Rotation controls
        rotation_frame = ttk.Frame(options_frame)
        rotation_frame.pack(fill='x', padx=5, pady=5)
        
        ttk.Label(rotation_frame, text="Camera Rotation:").grid(row=0, column=0, sticky='w')
        
        # Cam0 rotation
        cam0_rot_frame = ttk.Frame(rotation_frame)
        cam0_rot_frame.grid(row=1, column=0, sticky='w', padx=20, pady=2)
        ttk.Label(cam0_rot_frame, text="Cam0:").pack(side='left')
        cam0_rotation_var = tk.StringVar(value='0')
        cam0_rot_combo = ttk.Combobox(cam0_rot_frame, textvariable=cam0_rotation_var, 
                                     values=['0', '90', '180', '270'], width=8, state='readonly')
        cam0_rot_combo.pack(side='left', padx=5)
        ttk.Label(cam0_rot_frame, text="degrees").pack(side='left')
        
        # Cam1 rotation
        cam1_rot_frame = ttk.Frame(rotation_frame)
        cam1_rot_frame.grid(row=2, column=0, sticky='w', padx=20, pady=2)
        ttk.Label(cam1_rot_frame, text="Cam1:").pack(side='left')
        cam1_rotation_var = tk.StringVar(value='0')
        cam1_rot_combo = ttk.Combobox(cam1_rot_frame, textvariable=cam1_rotation_var, 
                                     values=['0', '90', '180', '270'], width=8, state='readonly')
        cam1_rot_combo.pack(side='left', padx=5)
        ttk.Label(cam1_rot_frame, text="degrees").pack(side='left')
        
        # Speed options
        speed_frame = ttk.Frame(options_frame)
        speed_frame.pack(fill='x', padx=5, pady=5)
        
        super_fast_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(speed_frame, text="Super Fast (Hardware Acceleration)", 
                       variable=super_fast_var).grid(row=0, column=0, sticky='w', padx=10)
        
        # Frame synchronization options
        sync_frame = ttk.Frame(options_frame)
        sync_frame.pack(fill='x', padx=5, pady=5)
        
        ttk.Label(sync_frame, text="Frame Synchronization:").grid(row=0, column=0, sticky='w', padx=10)
        
        force_sync_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(sync_frame, text="Force Sync (trim to shortest video)", 
                       variable=force_sync_var).grid(row=1, column=0, sticky='w', padx=20)
        
        target_frames_frame = ttk.Frame(sync_frame)
        target_frames_frame.grid(row=2, column=0, sticky='w', padx=20, pady=2)
        ttk.Label(target_frames_frame, text="Target frames:").pack(side='left')
        target_frames_var = tk.StringVar(value='')
        target_frames_entry = ttk.Entry(target_frames_frame, textvariable=target_frames_var, width=10)
        target_frames_entry.pack(side='left', padx=5)
        ttk.Label(target_frames_frame, text="(leave empty for auto)").pack(side='left')
        
        # Output path
        output_frame = ttk.Frame(options_frame)
        output_frame.pack(fill='x', padx=5, pady=5)
        
        ttk.Label(output_frame, text="Output file:").grid(row=0, column=0, sticky='w')
        output_var = tk.StringVar()
        output_entry = ttk.Entry(output_frame, textvariable=output_var, width=40)
        output_entry.grid(row=0, column=1, sticky='w', padx=5)
        
        def update_output_path():
            folder = folder_var.get()
            if folder:
                folder_name = os.path.basename(folder)
                layout = layout_var.get()
                speed_suffix = "_superfast" if super_fast_var.get() else "_fast"
                cam0_rot = cam0_rotation_var.get()
                cam1_rot = cam1_rotation_var.get()
                rotation_suffix = ""
                if cam0_rot != '0' or cam1_rot != '0':
                    rotation_suffix = f"_r{cam0_rot}_{cam1_rot}"
                sync_suffix = "_synced" if force_sync_var.get() else ""
                output_var.set(os.path.join(folder, f"{folder_name}_concatenated{speed_suffix}{rotation_suffix}{sync_suffix}_{layout}.mp4"))
        
        # Update output path when any parameter changes
        folder_var.trace('w', lambda *args: update_output_path())
        layout_var.trace('w', lambda *args: update_output_path())
        super_fast_var.trace('w', lambda *args: update_output_path())
        cam0_rotation_var.trace('w', lambda *args: update_output_path())
        cam1_rotation_var.trace('w', lambda *args: update_output_path())
        force_sync_var.trace('w', lambda *args: update_output_path())
        
        # Progress and status
        status_frame = ttk.LabelFrame(dialog, text="Status")
        status_frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        status_text = tk.Text(status_frame, height=10, width=70)
        status_text.pack(fill='both', expand=True, padx=5, pady=5)
        
        def log_message(message):
            status_text.insert('end', message + '\n')
            status_text.see('end')
            dialog.update()
        
        # Analyze sync function
        def analyze_sync():
            folder = folder_var.get()
            if not folder:
                messagebox.showerror("Error", "Please select a recording folder")
                return
            
            if not os.path.exists(folder):
                messagebox.showerror("Error", "Selected folder does not exist")
                return
            
            # Check for video files
            cam0_path = os.path.join(folder, "cam0.mp4")
            cam1_path = os.path.join(folder, "cam1.mp4")
            
            if not os.path.exists(cam0_path) or not os.path.exists(cam1_path):
                messagebox.showerror("Error", "cam0.mp4 and cam1.mp4 not found in selected folder")
                return
            
            log_message("Analyzing frame synchronization...")
            
            # Run analysis in a separate thread
            def analyze_thread():
                try:
                    import subprocess
                    import sys
                    
                    # Build command for sync analysis
                    cmd = [
                        sys.executable, "post_process_videos.py",
                        folder,
                        "--analyze-sync"
                    ]
                    
                    log_message("Running sync analysis...")
                    log_message(f"Command: {' '.join(cmd)}")
                    
                    # Run with real-time output
                    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, 
                                             universal_newlines=True, bufsize=1)
                    
                    # Show progress in real-time
                    for line in process.stdout:
                        log_message(line.strip())
                    
                    process.wait()
                    
                    if process.returncode == 0:
                        log_message("Sync analysis completed!")
                    else:
                        log_message(f"Error: Analysis returned code {process.returncode}")
                        
                except Exception as e:
                    log_message(f"Error during analysis: {e}")
            
            thread = threading.Thread(target=analyze_thread)
            thread.daemon = True
            thread.start()
        
        # Preview function
        def create_preview():
            folder = folder_var.get()
            if not folder:
                messagebox.showerror("Error", "Please select a recording folder")
                return
            
            if not os.path.exists(folder):
                messagebox.showerror("Error", "Selected folder does not exist")
                return
            
            # Check for video files
            cam0_path = os.path.join(folder, "cam0.mp4")
            cam1_path = os.path.join(folder, "cam1.mp4")
            
            if not os.path.exists(cam0_path) or not os.path.exists(cam1_path):
                messagebox.showerror("Error", "cam0.mp4 and cam1.mp4 not found in selected folder")
                return
            
            layout = layout_var.get()
            cam0_rot = int(cam0_rotation_var.get())
            cam1_rot = int(cam1_rotation_var.get())
            
            # Create preview filename
            folder_name = os.path.basename(folder)
            preview_path = os.path.join(folder, f"{folder_name}_preview_{layout}.jpg")
            
            log_message(f"Creating preview snapshot...")
            log_message(f"Folder: {folder}")
            log_message(f"Layout: {layout}")
            log_message(f"Cam0 rotation: {cam0_rot}°")
            log_message(f"Cam1 rotation: {cam1_rot}°")
            log_message(f"Preview: {preview_path}")
            
            # Run preview creation in a separate thread
            def preview_thread():
                try:
                    import subprocess
                    import sys
                    
                    # Build command for the preview
                    cmd = [
                        sys.executable, "post_process_videos.py",
                        folder,
                        "--preview",
                        "--layout", layout,
                        "--cam0-rotation", str(cam0_rot),
                        "--cam1-rotation", str(cam1_rot)
                    ]
                    
                    log_message("Running preview command...")
                    log_message(f"Command: {' '.join(cmd)}")
                    
                    # Run with real-time output
                    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, 
                                             universal_newlines=True, bufsize=1)
                    
                    # Show progress in real-time
                    for line in process.stdout:
                        log_message(line.strip())
                    
                    process.wait()
                    
                    if process.returncode == 0:
                        log_message("Preview snapshot created successfully!")
                        log_message(f"Preview file: {preview_path}")
                        
                        # Try to open the preview image
                        try:
                            if platform.system() == "Windows":
                                os.startfile(preview_path)
                            elif platform.system() == "Darwin":  # macOS
                                subprocess.run(["open", preview_path])
                            else:  # Linux
                                subprocess.run(["xdg-open", preview_path])
                            log_message("Preview image opened in default viewer")
                        except Exception as e:
                            log_message(f"Could not open preview automatically: {e}")
                            log_message(f"Please open manually: {preview_path}")
                        
                        messagebox.showinfo("Success", f"Preview snapshot created!\nFile: {preview_path}")
                    else:
                        log_message(f"Error: Preview creation returned code {process.returncode}")
                        messagebox.showerror("Error", f"Preview creation failed with return code {process.returncode}")
                        
                except Exception as e:
                    log_message(f"Error during preview creation: {e}")
                    messagebox.showerror("Error", f"Preview creation failed: {e}")
            
            thread = threading.Thread(target=preview_thread)
            thread.daemon = True
            thread.start()
        
        # Process function
        def process_videos():
            folder = folder_var.get()
            if not folder:
                messagebox.showerror("Error", "Please select a recording folder")
                return
            
            if not os.path.exists(folder):
                messagebox.showerror("Error", "Selected folder does not exist")
                return
            
            # Check for video files
            cam0_path = os.path.join(folder, "cam0.mp4")
            cam1_path = os.path.join(folder, "cam1.mp4")
            
            if not os.path.exists(cam0_path) or not os.path.exists(cam1_path):
                messagebox.showerror("Error", "cam0.mp4 and cam1.mp4 not found in selected folder")
                return
            
            output_path = output_var.get()
            layout = layout_var.get()
            super_fast = super_fast_var.get()
            cam0_rot = int(cam0_rotation_var.get())
            cam1_rot = int(cam1_rotation_var.get())
            force_sync = force_sync_var.get()
            target_frames = target_frames_var.get().strip()
            
            log_message(f"Starting fast post-processing...")
            log_message(f"Folder: {folder}")
            log_message(f"Layout: {layout}")
            log_message(f"Cam0 rotation: {cam0_rot}°")
            log_message(f"Cam1 rotation: {cam1_rot}°")
            log_message(f"Force sync: {force_sync}")
            if target_frames:
                log_message(f"Target frames: {target_frames}")
            log_message(f"Super Fast: {super_fast}")
            log_message(f"Output: {output_path}")
            
            # Run post-processing in a separate thread
            def process_thread():
                try:
                    import subprocess
                    import sys
                    
                    # Build command for the fast post-processing script
                    cmd = [
                        sys.executable, "post_process_videos.py",
                        folder,
                        "--output", output_path,
                        "--layout", layout,
                        "--cam0-rotation", str(cam0_rot),
                        "--cam1-rotation", str(cam1_rot)
                    ]
                    
                    # Add force sync if enabled
                    if force_sync:
                        cmd.append("--force-sync")
                    
                    # Add target frames if specified
                    if target_frames:
                        try:
                            target_frames_int = int(target_frames)
                            cmd.extend(["--target-frames", str(target_frames_int)])
                        except ValueError:
                            log_message("Warning: Invalid target frames value, ignoring")
                    
                    # Add super-fast flag if selected
                    if super_fast:
                        cmd.append("--super-fast")
                    
                    log_message("Running fast post-processing command...")
                    log_message(f"Command: {' '.join(cmd)}")
                    
                    # Run with real-time output
                    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, 
                                             universal_newlines=True, bufsize=1)
                    
                    # Show progress in real-time
                    for line in process.stdout:
                        log_message(line.strip())
                    
                    process.wait()
                    
                    if process.returncode == 0:
                        log_message("Fast post-processing completed successfully!")
                        log_message(f"Output file: {output_path}")
                        messagebox.showinfo("Success", f"Fast post-processing completed!\nOutput: {output_path}")
                    else:
                        log_message(f"Error: Process returned code {process.returncode}")
                        messagebox.showerror("Error", f"Post-processing failed with return code {process.returncode}")
                        
                except Exception as e:
                    log_message(f"Error during processing: {e}")
                    messagebox.showerror("Error", f"Post-processing failed: {e}")
            
            thread = threading.Thread(target=process_thread)
            thread.daemon = True
            thread.start()
        
        button_frame = ttk.Frame(dialog)
        button_frame.pack(fill='x', padx=10, pady=10)
        
        ttk.Button(button_frame, text="Analyze Sync", command=analyze_sync).pack(side='left', padx=5)
        ttk.Button(button_frame, text="Create Preview", command=create_preview).pack(side='left', padx=5)
        ttk.Button(button_frame, text="Process Videos", command=process_videos).pack(side='left', padx=5)
        ttk.Button(button_frame, text="Close", command=dialog.destroy).pack(side='right', padx=5)
        
        # Initialize output path
        update_output_path()

if __name__ == '__main__':
    root = tk.Tk()
    app = PiControllerGUI(root)
    root.mainloop()