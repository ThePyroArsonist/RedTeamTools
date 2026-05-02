from flask import Flask, request, jsonify, render_template
from flask_socketio import SocketIO
import time
import threading

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

# -----------------------------
# In-memory lab state
# -----------------------------
sessions = {}
command_queue = {}

# -----------------------------
# Session tracking
# -----------------------------
def log_session(client_id, data):
    if client_id not in sessions:
        sessions[client_id] = []

    sessions[client_id].append({
        "timestamp": time.time(),
        "data": data
    })

    socketio.emit("update", sessions)

# -----------------------------
# API: receive packet logs
# -----------------------------
@app.route("/ingest", methods=["POST"])
def ingest():
    payload = request.json
    client_id = payload.get("client")
    data = payload.get("data")

    log_session(client_id, data)
    return jsonify({"status": "ok"})

# -----------------------------
# API: queue commands (simulated)
# -----------------------------
@app.route("/command/<client_id>", methods=["POST"])
def add_command(client_id):
    cmd = request.json.get("cmd")

    if client_id not in command_queue:
        command_queue[client_id] = []

    command_queue[client_id].append(cmd)
    return jsonify({"queued": cmd})

# -----------------------------
# API: fetch commands
# -----------------------------
@app.route("/poll/<client_id>")
def poll(client_id):
    cmds = command_queue.get(client_id, [])
    command_queue[client_id] = []
    return jsonify(cmds)

# -----------------------------
# Dashboard UI
# -----------------------------
@app.route("/")
def dashboard():
    return render_template("dashboard.html")

# -----------------------------
# run
# -----------------------------
if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=5000)