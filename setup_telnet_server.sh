#!/bin/bash

# Configuration
PORT=${1:-2344}
INTERFACE="0.0.0.0"

echo -e "${GREEN}=== Unauthenticated Telnet/Shell Server Setup ===${NC}"
echo "Binding to: ${INTERFACE}:${PORT}"
echo "Mode: ${INTERFACE} (Local + External Accessable)"
echo ""

# Helper: Check if port is already in use
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
        pkill -f "${PORT}" 2>/dev/null || true
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
    socat -T 1 TCP-LISTEN:${PORT},reuse,fork EXEC:bash -i,pty
    echo "Server started on ${INTERFACE}:${PORT}. Press Ctrl+C to stop."
    socat -T 0 TCP-LISTEN:${PORT},reuse,fork EXEC:bash -i,pty
elif command -v python3 &> /dev/null; then
    echo -e "${YELLOW}Detected ${GREEN}python3${YELLOW} (Fallback Mode - Optimized for Speed)${NC}"
    
    # Create a temp Python script to avoid heredoc issues
    PY_SCRIPT=$(mktemp /tmp/py_telnet_XXXXXX.py)
    
    # KEY: Unquoted heredoc to allow Bash variable expansion
    cat > "$PY_SCRIPT" << PYEOF
import socket
import subprocess
import os

HOST = "${INTERFACE}"
PORT = ${PORT}

print(f"Python Telnet Server starting on {HOST}:{PORT} (Local + External).")

sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)  # Disable Nagle's algorithm
sock.bind((HOST, PORT))
sock.listen(1)  # Listen queue of 1
print(f"Listening on socket. Hit Ctrl+C to stop.")

while True:
    try:
        conn, addr = sock.accept()
        print(f"Accepted connection from {addr}")
        
        # Set TCP_NODELAY for the connection to avoid buffering
        conn.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        
        # Pass the socket directly to the shell subprocess with unbuffered I/O
        try:
            cmd = subprocess.Popen(
                ['bash', '-i'], 
                stdin=sock, 
                stdout=sock, 
                stderr=sock,
                bufsize=1,  # Unbuffered I/O
                universal_newlines=False  # Use raw bytes
            )
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
PYEOF

    echo "Running Python script: $PY_SCRIPT"
    python3 "$PY_SCRIPT"
    
    # Cleanup
    rm -f "$PY_SCRIPT"

elif command -v nc &> /dev/null; then
    echo -e "${YELLOW}Detected ${GREEN}nc${YELLOW} (Netcat Fallback)${NC}"
    nc -l -p ${PORT} -k -e bash -i
else
    echo -e "${RED}Error: No suitable server found (Try installing python3 or netcat)${NC}"
    exit 1
fi
