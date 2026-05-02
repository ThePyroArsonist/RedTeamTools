#!/bin/bash

echo "[+] Checking libpcap..."

if ! dpkg -s libpcap-dev >/dev/null 2>&1; then
    echo "[!] libpcap not found. Installing..."
    sudo apt update && sudo apt install -y libpcap-dev
fi

echo "[+] Compiling..."
gcc dns_sniffer.c -o dns_sniffer -lpcap

echo "[+] Done."