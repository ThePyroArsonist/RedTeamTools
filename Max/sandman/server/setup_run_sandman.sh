#!/bin/bash

set -e

echo "[+] Checking for requirements.txt..."

if [ ! -f "requirements.txt" ]; then
    echo "[-] requirements.txt not found in current directory"
    exit 1
fi

echo "[+] Updating package list..."
sudo apt update -y

echo "[+] Ensuring Python3 and pip are installed..."
sudo apt install -y python3 python3-pip

echo "[+] Installing Python dependencies..."
pip3 install --upgrade pip
pip3 install -r requirements.txt

echo "[+] Dependencies installed successfully"

# ---- RUN APP SECTION ----
APP_FILE="sandman_server.py"

if [ -f "$APP_FILE" ]; then
    echo "[+] Running $APP_FILE ..."
    python3 "$APP_FILE"
else
    echo "[-] $APP_FILE not found. Please update script with your entry file."
    exit 1
fi