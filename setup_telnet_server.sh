#!/bin/bash

PORT=${1:-2344}

echo -e "\n${GREEN}=== Telnet Server ===${NC}"
echo "Port: ${PORT}"
echo "Binding: 0.0.0.0 (Local + External)"

# Cleanup
if ss -tlnp 2>/dev/null | grep -q ":${PORT}"; then
    echo -e "\n${YELLOW}Port ${PORT} already in use...${NC}"
    pkill -f "2344" 2>/dev/null || pkill -f "bash"
    sleep 1
fi

# Use socat first
if command -v socat &> /dev/null; then
    echo -e "\n${GREEN}Using ${YELLOW}socat${GREEN}...${NC}"
    socat -T 0 TCP-LISTEN:${PORT},reuse,fork EXEC:bash -i,pty
    while true; do sleep 1; done
else
    echo -e "\n${GREEN}Using ${YELLOW}python3${GREEN}...${NC}"
    
    # Write Python script to file with UNQUOTED heredoc (variables expand!)
    PYFILE="/tmp/py_telnet_server.py"
    
    cat > "$PYFILE" << PYEOF
import socket
import subprocess

HOST = "0.0.0.0"
PORT = ${PORT}

print(f"\n[OK] Python Telnet Server Starting...")
print(f"[OK] Listening on {HOST}:{PORT}")
print(f"[OK] Press Ctrl+C to stop")

sock = socket.socket()
sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)

sock.bind((HOST, PORT))
sock.listen(5)

while True:
    try:
        conn, addr = sock.accept()
        print(f"[OK] ACCEPTED from: {addr}")
        
        # Set TCP_NODELAY on connection
        conn.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        
        # Start bash with direct socket piping
        subprocess.Popen(
            ['bash', '-i'],
            stdin=conn, stdout=conn, stderr=conn,
            bufsize=1
        ).wait()
        
        conn.close()
        print(f"[OK] Closed: {addr}")
    except KeyboardInterrupt:
        print("\n[OK] Stopping...")
        break
    except Exception as e:
        print(f"[WARN] Error: {e}")
        break
PYEOF

    echo "[BASH] Running Python server: ${PYFILE}"
    python3 "$PYFILE"
fi

echo -e "\n${GREEN}=== Server Ready ===${NC}"
