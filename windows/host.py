"""Visible Windows desktop host; traffic is bound to the Tailscale IPv4 only."""
import ipaddress
import os
import secrets
import subprocess
import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk

# PyInstaller executes this script from a bundled directory; regular Python from repo root.
if not getattr(sys, 'frozen', False):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from setu import server as host
import uvicorn

PORT = 8000

def tailscale_ipv4():
    exe = Path(os.environ.get('ProgramFiles', r'C:\Program Files')) / 'Tailscale' / 'tailscale.exe'
    command = str(exe) if exe.exists() else 'tailscale'
    try:
        result = subprocess.run([command, 'ip', '-4'], capture_output=True, text=True, timeout=5,
                                creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        addresses = result.stdout.splitlines() if result.returncode == 0 else []
        for address in addresses:
            ip = ipaddress.ip_address(address.strip())
            if ip.version == 4 and ip in ipaddress.ip_network('100.64.0.0/10'):
                return str(ip)
    except (OSError, ValueError, subprocess.SubprocessError):
        pass
    raise RuntimeError('Tailscale is not connected. Install Tailscale, sign in, and try again.')

class HostWindow:
    def __init__(self, root):
        self.root = root
        self.server = None
        self.thread = None
        self.address = tk.StringVar(value='Not sharing')
        self.key = tk.StringVar(value='Start sharing to generate a key')
        self.state = tk.StringVar(value='Your screen is not being shared.')
        root.title('Setu PC Host')
        root.geometry('570x390')
        root.minsize(520, 360)
        root.protocol('WM_DELETE_WINDOW', self.close)
        frame = ttk.Frame(root, padding=24); frame.pack(fill='both', expand=True)
        ttk.Label(frame, text='SETU  /  PC HOST', font=('Segoe UI', 11, 'bold')).pack(anchor='w')
        ttk.Label(frame, text='Your PC, within reach.', font=('Segoe UI', 22)).pack(anchor='w', pady=(12, 4))
        ttk.Label(frame, text='Connect both devices to Tailscale. Keep this window open.', wraplength=500).pack(anchor='w')
        ttk.Separator(frame).pack(fill='x', pady=16)
        ttk.Label(frame, text='STATUS').pack(anchor='w')
        ttk.Label(frame, textvariable=self.state, font=('Segoe UI', 11, 'bold')).pack(anchor='w', pady=(2, 10))
        ttk.Label(frame, text='TAILSCALE ADDRESS').pack(anchor='w')
        ttk.Entry(frame, textvariable=self.address, state='readonly').pack(fill='x', pady=(2, 10))
        ttk.Label(frame, text='ACCESS KEY — keep private').pack(anchor='w')
        ttk.Entry(frame, textvariable=self.key, state='readonly').pack(fill='x', pady=(2, 12))
        buttons = ttk.Frame(frame); buttons.pack(fill='x')
        self.start_button = ttk.Button(buttons, text='Start sharing', command=self.start); self.start_button.pack(side='left')
        self.stop_button = ttk.Button(buttons, text='Stop sharing', command=self.stop, state='disabled'); self.stop_button.pack(side='left', padx=8)
        ttk.Label(frame, text='Only start sharing when you trust the other device.', foreground='#637a68').pack(anchor='w', pady=(14, 0))

    def start(self):
        if self.thread and self.thread.is_alive(): return
        try:
            ip = tailscale_ipv4()
            # Fail before offering the connection if screenshot/control is unavailable.
            pg = host.desktop()
            pg.size()
            pg.screenshot()
        except Exception as exc:
            messagebox.showerror('Cannot start sharing', str(exc)); return
        host.DEMO = False
        host.PASSWORD = secrets.token_urlsafe(18)
        host.SESSIONS.clear()
        host.ATTEMPTS.clear()
        host.SHARED = Path.home() / 'Documents' / 'Setu' / 'shared'
        self.address.set(f'{ip}:{PORT}')
        self.key.set(host.PASSWORD)
        self.state.set('Starting…')
        self.start_button.config(state='disabled')
        self.stop_button.config(state='normal')
        config = uvicorn.Config(host.app, host=ip, port=PORT, log_level='critical', access_log=False)
        self.server = uvicorn.Server(config)
        self.thread = threading.Thread(target=self.server.run, daemon=True)
        self.thread.start()
        self.root.after(200, self.check_started)

    def check_started(self):
        if not self.server: return
        if self.server.started:
            self.state.set('Sharing is ON — your screen can be controlled.')
        elif self.thread.is_alive():
            self.root.after(200, self.check_started)
        else:
            self.state.set('Could not start. Check port 8000 and Tailscale.')
            self.address.set('Not sharing'); self.key.set('Start sharing to generate a key')
            self.start_button.config(state='normal'); self.stop_button.config(state='disabled')
            self.server = None

    def stop(self):
        if self.server: self.server.should_exit = True
        host.SESSIONS.clear()
        self.state.set('Stopping…')
        self.stop_button.config(state='disabled')
        self.root.after(150, self.check_stopped)

    def check_stopped(self):
        if self.thread and self.thread.is_alive():
            self.root.after(150, self.check_stopped); return
        self.server = None
        self.address.set('Not sharing'); self.key.set('Start sharing to generate a key')
        self.state.set('Your screen is not being shared.')
        self.start_button.config(state='normal')

    def close(self):
        if self.server: self.server.should_exit = True
        host.SESSIONS.clear()
        self.root.destroy()

if __name__ == '__main__':
    root = tk.Tk(); HostWindow(root); root.mainloop()
