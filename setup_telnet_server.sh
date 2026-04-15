#!/bin/bash

# Config
PORT=${1:-2344}

echo -e "\n=== Telnet Server ==="
echo "Config Port: ${PORT}"
echo "Binding: 0.0.0.0 (Local + External)"

# Cleanup
if ss -tlnp 2>/dev/null | grep -q ":${PORT}"; then
    echo -e "\nPort ${PORT} in use..."
    pkill -f "2344" 2>/dev/null || pkill -f "bash"
    sleep 1
fi

# Use socat first
if command -v socat &> /dev/null; then
    echo -e "\nUsing socat...";
    socat -T 0 TCP-LISTEN:${PORT},reuse,fork EXEC:bash -i,pty
    while true; do sleep 1; done
else
    echo -e "\nUsing python3..."

    # KEY: Create temp file with variable expanded BEFORE Python sees it
    PYFILE="/tmp/py_telnet_$(date +%s).py"

    # Write the Python code using a simple heredoc
    echo "import socket" > "$PYFILE"
    echo "import subprocess" >> "$PYFILE"
    echo "" >> "$PYFILE"
    echo "HOST = \"0.0.0.0\"" >> "$PYFILE"
    echo "PORT = ${PORT}" >> "$PYFILE"  # This line gets: PORT = 2344
    echo "" >> "$PYFILE"
    echo "print(f'[OK] Starting...')" >> "$PYFILE"
    echo "print(f'[OK] Listening on {HOST}:{PORT}')" >> "$PYFILE"
    echo "" >> "$PYFILE"
    echo "sock = socket.socket()" >> "$PYFILE"
    echo "sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)" >> "$PYFILE"
    echo "sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)" >> "$PYFILE"
    echo "sock.bind((HOST, PORT))" >> "$PYFILE"
    echo "sock.listen(5)" >> "$PYFILE"
    echo "" >> "$PYFILE"
    echo "while True:" >> "$PYFILE"
    echo "    try:" >> "$PYFILE"
    echo "        conn, addr = sock.accept()" >> "$PYFILE"
    echo "        print(f'[OK] ACCEPTED: {addr}')" >> "$PYFILE"
    echo "        conn.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)" >> "$PYFILE"
    echo "        subprocess.Popen(['bash', '-i'], stdin=conn, stdout=conn, stderr=conn, bufsize=1).wait()" >> "$PYFILE"
    echo "        conn.close()" >> "$PYFILE"
    echo "    except KeyboardInterrupt:" >> "$PYFILE"
    echo "        break" >> "$PYFILE"
    echo "    except Exception as e:" >> "$PYFILE"
    echo "        print(f'[WARN] Error: {e}')" >> "$PYFILE"
    echo "        break" >> "$PYFILE"

    echo "[BASH] Running Python: ${PYFILE}"
    python3 "$PYFILE"
fi

echo -e "\n=== Server Ready ==="
