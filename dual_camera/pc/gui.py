import tkinter as tk
from tkinter import ttk, messagebox
import requests

# Example config: list of Pi hostnames or IPs
PI_CONFIG = [
    {'name': 'Pi1', 'host': 'http://192.168.1.101:5000'},
    {'name': 'Pi2', 'host': 'http://192.168.1.102:5000'},
]

class PiControllerGUI:
    def __init__(self, root):
        self.root = root
        self.root.title('Dual Camera Pi Controller')
        self.selected_pi = tk.StringVar()
        self.duration = tk.StringVar(value='300')
        self.fps = tk.StringVar(value='100')
        self.status_text = tk.StringVar(value='Select a Pi and set parameters.')

        # Pi selection
        ttk.Label(root, text='Select Raspberry Pi:').grid(row=0, column=0, sticky='w')
        self.pi_combo = ttk.Combobox(root, textvariable=self.selected_pi, state='readonly')
        self.pi_combo['values'] = [f"{pi['name']} ({pi['host']})" for pi in PI_CONFIG]
        self.pi_combo.grid(row=0, column=1, sticky='ew')
        self.pi_combo.current(0)

        # Duration
        ttk.Label(root, text='Duration (s):').grid(row=1, column=0, sticky='w')
        ttk.Entry(root, textvariable=self.duration, width=10).grid(row=1, column=1, sticky='w')

        # FPS
        ttk.Label(root, text='FPS:').grid(row=2, column=0, sticky='w')
        ttk.Entry(root, textvariable=self.fps, width=10).grid(row=2, column=1, sticky='w')

        # Buttons
        ttk.Button(root, text='Start Recording', command=self.start_recording).grid(row=3, column=0, pady=5)
        ttk.Button(root, text='Stop Recording', command=self.stop_recording).grid(row=3, column=1, pady=5)
        ttk.Button(root, text='Check Status', command=self.check_status).grid(row=4, column=0, pady=5)

        # Status/response area
        self.status_area = tk.Text(root, height=8, width=50, state='disabled')
        self.status_area.grid(row=5, column=0, columnspan=2, pady=5)

        root.grid_columnconfigure(1, weight=1)

    def get_selected_pi(self):
        idx = self.pi_combo.current()
        return PI_CONFIG[idx]

    def log(self, msg):
        self.status_area.config(state='normal')
        self.status_area.insert('end', msg + '\n')
        self.status_area.see('end')
        self.status_area.config(state='disabled')

    def start_recording(self):
        pi = self.get_selected_pi()
        try:
            duration = int(self.duration.get())
            fps = int(self.fps.get())
        except ValueError:
            messagebox.showerror('Input Error', 'Duration and FPS must be integers.')
            return
        url = f"{pi['host']}/start_recording"
        payload = {'duration': duration, 'fps': fps}
        self.log(f"[DEBUG] Sending start_recording to {url} with {payload}")
        try:
            resp = requests.post(url, json=payload, timeout=5)
            resp.raise_for_status()
            self.log(f"[INFO] {resp.json()}")
        except Exception as e:
            self.log(f"[ERROR] {e}")

    def stop_recording(self):
        pi = self.get_selected_pi()
        url = f"{pi['host']}/stop_recording"
        self.log(f"[DEBUG] Sending stop_recording to {url}")
        try:
            resp = requests.post(url, timeout=5)
            resp.raise_for_status()
            self.log(f"[INFO] {resp.json()}")
        except Exception as e:
            self.log(f"[ERROR] {e}")

    def check_status(self):
        pi = self.get_selected_pi()
        url = f"{pi['host']}/status"
        self.log(f"[DEBUG] Checking status at {url}")
        try:
            resp = requests.get(url, timeout=5)
            resp.raise_for_status()
            self.log(f"[INFO] {resp.json()}")
        except Exception as e:
            self.log(f"[ERROR] {e}")

if __name__ == '__main__':
    root = tk.Tk()
    app = PiControllerGUI(root)
    root.mainloop() 