#!/bin/bash

# ==========================================
# CONFIGURATION
# ==========================================
PORT=${1:-2344}
INTERFACE="0.0.0.0" # 0.0.0.0 = Listen on ALL (Local & External)

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "\n${GREEN}==========================================${NC}"
echo -e "${GREEN}=== Unauthenticated Telnet/Shell Server ===${NC}"
echo -e "${GREEN}==========================================${NC}"
echo "Config Port: ${PORT}"
echo "Binding IP:  ${INTERFACE}"
echo "Date/Time:   $(date '+%F %T')"

# ==========================================
# 1. Cleanup Existing Process
# ==========================================
if ss -tlnp 2>/dev/null | grep -q ":${PORT}"; then
    echo -e "${YELLOW}Warning: Port ${PORT} is already in use.${NC}"
    read -p "Kill existing process and restart? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        pkill -f "bash" 2>/dev/null || pkill -f "${PORT}" || true
        sleep 1
    else
        exit 1
    fi
fi

# ==========================================
# 2. Detect Best Server
# ==========================================
if command -v socat &> /dev/null; then
    echo -e "\n${GREEN}Using ${YELLOW}socat${GREEN} (Fastest/Most Reliable)${NC}"
    socat -T 0 TCP-LISTEN:${PORT},reuse,fork EXEC:bash -i,pty
    # socat keeps running, script needs to sleep forever or be detached
    while true; do sleep 1; done
elif command -v python3 &> /dev/null; then
    echo -e "\n${GREEN}Using ${YELLOW}python3${GREEN} (Fallback - Optimized)${NC}"
    
    # Create a temp Python script for clean variable handling
    PY_SCRIPT=$(mktemp /tmp/py_telnet_XXXXXX.py)
    cat > "$PY_SCRIPT" << PYEOF
import socket
import subprocess
import os

HOST = "${INTERFACE}"
PORT = ${PORT}

print(f"\n[PYTHON] Starting Telnet Server: {HOST}:{PORT}")
print(f"[PYTHON] Current IP:     {os.popen('hostname -I 2>/dev/null || ip -4 addr show eth0 2>/dev/null | grep -oP \"(?:\\d{{1,3}\\.}){{3}}\\d{1,3}\"')[0] if os.popen('hostname -I 2>/dev/null || ip -4 addr show eth0 2>/dev/null | grep -oP \"(?:\\d{{1,3}\\.}){{3}}\\d{1,3}\"') else 'Unknown'")

sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)  # Fix #1: Disable Buffering

# Bind to HOST:PORT
sock.bind((HOST, PORT))
sock.listen(5)
print(f"[PYTHON] Listening on {HOST}:{PORT} ...")

while True:
    try:
        conn, addr = sock.accept()
        print(f"[PYTHON] ACCEPTED from {addr}")
        # Fix #2: Set TCP_NODELAY on the connection
        conn.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        
        # Fix #3: Unbuffered I/O for raw bytes
        cmd = subprocess.Popen(
            ['bash', '-i'], 
            stdin=conn, 
            stdout=conn, 
            stderr=conn,
            bufsize=1, 
            universal_newlines=False
        )
        cmd.wait()
        conn.close()
    except KeyboardInterrupt:
        print("\n[PYTHON] Shutting down gracefully...")
        break
    except Exception as e:
        print(f"[PYTHON] Error: {e}")
        break
PYEOF
    
    python3 "$PY_SCRIPT"
    rm -f "$PY_SCRIPT"
elif command -v nc &> /dev/null; then
    echo -e "\n${GREEN}Using ${YELLOW}nc (Netcat Fallback)${NC}"
    nc -l -p ${PORT} -k -e bash -i
else
    echo -e "\n${RED}Error: No suitable server found!${NC}"
    echo "Install python3, socat, or netcat."
    exit 1
fi
