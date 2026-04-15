#!/bin/bash

# Configuration
PORT=${1:-2344}
INTERFACE="0.0.0.0"

echo -e "\n${GREEN}====== Telnet Server Setup ======${NC}"
echo "Port: ${PORT}"
echo "Binding: ${INTERFACE}"
echo "Date: $(date '+%F %T')"

# Cleanup
if ss -tlnp 2>/dev/null | grep -q ":${PORT}"; then
    echo -e "\n${YELLOW}Port ${PORT} already in use...${NC}"
    read -p "Restart (y/n)? " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        pkill -f "${PORT}" 2>/dev/null || pkill -f "bash" 2>/dev/null
        sleep 1
    else
        exit 1
    fi
fi

# Use socat if available (Most Reliable)
if command -v socat &> /dev/null; then
    echo -e "\n${GREEN}Using ${YELLOW}socat${GREEN}...${NC}"
    socat -T 0 TCP-LISTEN:${PORT},reuse,fork EXEC:bash -i,pty
    while true; do sleep 1; done
else
    # Fallback to Python3
    echo -e "\n${GREEN}Using ${YELLOW}python3${GREEN}...${NC}"
    
    # Simple, clean Python script
    PY=$(mktemp /tmp/py_telnet_XXXXXX.py)
    
    cat > "$PY" << 'PYEOF'
import socket
import subprocess
import os

HOST = "${INTERFACE}"
PORT = ${PORT}

print(f"\n[OK] Python Telnet Server Starting...")
print(f"[OK] Listening on {HOST}:{PORT}")
print(f"[OK] Press Ctrl+C to stop")

sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)

sock.bind((HOST, PORT))
sock.listen(5)

while True:
    try:
        conn, addr = sock.accept()
        print(f"[OK] ACCEPTED from: {addr}")
        
        # Set non-blocking socket options
        conn.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        
        # Start bash with direct socket piping
        try:
            subprocess.Popen(
                ['bash', '-i'],
                stdin=conn, stdout=conn, stderr=conn,
                bufsize=1,
                universal_newlines=False
            ).wait()
        except:
            pass
        finally:
            conn.close()
            print(f"[OK] Closed: {addr}")
    except KeyboardInterrupt:
        print("\n[OK] Stopping...")
        break
    except Exception as e:
        print(f"[WARN] Error: {e}")
        break
PYEOF
    
    python3 "$PY"
    rm -f "$PY"
fi

echo -e "\n${GREEN}=== Server Ready ===${NC}"
