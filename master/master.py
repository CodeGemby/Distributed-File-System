from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import random
import os
import io

app = Flask(__name__)
CORS(app)

# ============================================================
# 🔹 Node List & Manual Toggles
# ============================================================
NODES = {
    "Node-1": {"url": "http://127.0.0.1:5001", "status": "active"},
    "Node-2": {"url": "http://127.0.0.1:5002", "status": "active"},
    "Node-3": {"url": "http://127.0.0.1:5003", "status": "active"},
    "Node-4": {"url": "http://127.0.0.1:5004", "status": "active"},
    "Node-5": {"url": "http://127.0.0.1:5005", "status": "active"},
}

MANUAL_TOGGLES = {}   # Active / Down (manual)


# ============================================================
# FIX F-01: define check_node_health (was missing / NameError)
# ============================================================
def check_node_health(node_name):
    """Returns True if the node backend is reachable and healthy."""
    try:
        res = requests.get(f"{NODES[node_name]['url']}/status", timeout=2)
        return res.status_code == 200
    except Exception:
        return False


# ============================================================
# 🔥 PHASE 7 – AUTO RECOVERY ENGINE HELPERS
# ============================================================

def get_global_unique_files():
    """Collect unique files from all active nodes."""
    all_files = set()

    for node, info in NODES.items():
        # Only check active nodes
        if MANUAL_TOGGLES.get(node, info["status"]) == "active":
            try:
                res = requests.get(f"{info['url']}/list", timeout=2).json()
                files = res.get("files", [])
                for f in files:
                    all_files.add(f)
            except:
                pass

    return list(all_files)


def get_missing_files_for(target_node):
    """Returns list of missing files for a node."""
    try:
        res = requests.get(f"{NODES[target_node]['url']}/list", timeout=2).json()
        node_files = res.get("files", [])
    except:
        node_files = []

    global_files = get_global_unique_files()
    return [f for f in global_files if f not in node_files]


def recover_node(target_node):
    """Copy missing files when node comes back ONLINE."""
    missing = get_missing_files_for(target_node)
    recovered = []

    for filename in missing:
        # FIX F-04: try every peer; only break on successful target upload
        for node, info in NODES.items():
            if node == target_node:
                continue
            if MANUAL_TOGGLES.get(node, info["status"]) == "active":
                try:
                    res = requests.get(f"{info['url']}/download/{filename}", timeout=5)
                    if res.status_code == 200:
                        upload_url = f"{NODES[target_node]['url']}/upload"
                        files = {"file": (filename, io.BytesIO(res.content))}
                        up = requests.post(upload_url, files=files, timeout=10)
                        if up.status_code == 200:
                            recovered.append(filename)
                            break   # success — stop trying other peers for this file
                        # else: target upload failed → try next peer
                except:
                    continue

    return recovered


# ============================================================
# 🟢 NODE HEALTH CHECKER + FIX FOR "FORCE ACTIVE" ISSUE
# ============================================================
@app.route("/nodes", methods=["GET"])
def get_nodes():
    node_list = []

    for node, info in NODES.items():
        previous_status = info["status"]
        manual = MANUAL_TOGGLES.get(node)

        # Manual down → always down
        if manual == "down":
            current_status = "down"

        # Manual active → check REAL backend status (IMPORTANT FIX)
        elif manual == "active":
            try:
                res = requests.get(f"{info['url']}/status", timeout=2)
                current_status = "active" if res.status_code == 200 else "down"
            except:
                current_status = "down"

        # No manual override → auto detect
        else:
            try:
                res = requests.get(f"{info['url']}/status", timeout=2)
                current_status = "active" if res.status_code == 200 else "down"
            except:
                current_status = "down"

        # AUTO RECOVERY TRIGGER
        if previous_status == "down" and current_status == "active":
            recovered = recover_node(node)
            if recovered:
                print(f"🔥 AUTO-RECOVERY → Node {node} recovered {recovered}")

        info["status"] = current_status

        node_list.append({
            "name": node,
            "url": info["url"],
            "status": current_status
        })

    return jsonify(node_list)


# ============================================================
# 🔁 TOGGLE NODE (FIXED: cannot activate if backend not running)
# ============================================================
@app.route("/toggle_node", methods=["POST"])
def toggle_node():
    data = request.get_json()
    node_name = data.get("node")

    if node_name not in NODES:
        return jsonify({"message": f"❌ Node {node_name} not found"}), 404

    current = MANUAL_TOGGLES.get(node_name, NODES[node_name]["status"])
    new_state = "down" if current == "active" else "active"

    # If trying to activate a node → check backend running
    if new_state == "active":
        try:
            res = requests.get(f"{NODES[node_name]['url']}/status", timeout=1)
            if res.status_code != 200:
                return jsonify({"message": f"❌ Cannot activate {node_name} — Backend not running!"}), 400
        except:
            return jsonify({"message": f"❌ Cannot activate {node_name} — Backend offline!"}), 400

    MANUAL_TOGGLES[node_name] = new_state
    NODES[node_name]["status"] = new_state

    print(f"[TOGGLE] {node_name} manually set to {new_state.upper()}")
    return jsonify({"message": f"{node_name} manually set to {new_state.upper()}"}), 200


# ============================================================
# 📁 UPLOAD — FIX F-02: read bytes once, send to each node separately
# ============================================================
@app.route("/upload", methods=["POST"])
def upload_file():
    if "file" not in request.files:
        return jsonify({"error": "No file provided"}), 400

    file = request.files["file"]
    filename = file.filename
    mimetype = file.mimetype

    # FIX F-02: read all bytes upfront so each node gets a fresh stream
    file_bytes = file.read()

    active_nodes = [n for n, info in NODES.items()
                    if MANUAL_TOGGLES.get(n, info["status"]) == "active"]

    if not active_nodes:
        return jsonify({"error": "❌ No active nodes available!"}), 500

    selected = random.sample(active_nodes, min(3, len(active_nodes)))
    uploaded_to = []

    for node in selected:
        try:
            url = f"{NODES[node]['url']}/upload"
            # Each node gets a fresh BytesIO from the same bytes buffer
            files = {"file": (filename, io.BytesIO(file_bytes), mimetype)}
            res = requests.post(url, files=files, timeout=10)
            if res.status_code == 200:
                uploaded_to.append(node)
        except:
            pass

    if not uploaded_to:
        return jsonify({"error": "❌ Upload failed on all nodes"}), 500

    return jsonify({
        "message": f"✅ File '{filename}' replicated to: {', '.join(uploaded_to)}",
        "replicated_nodes": uploaded_to
    })


# ============================================================
# 📂 LIST FILES — From All Nodes
# ============================================================
@app.route("/list", methods=["GET"])
def list_all_files():
    all_files = {}

    for node, info in NODES.items():
        try:
            res = requests.get(f"{info['url']}/list", timeout=3)
            if res.status_code == 200:
                all_files[node] = res.json().get("files", [])
            else:
                all_files[node] = "Error fetching files"
        except:
            all_files[node] = "🔴 Node Down"

    return jsonify(all_files)


# ============================================================
# 📥 DOWNLOAD File (master finds correct node)
# ============================================================
@app.route("/download/<filename>", methods=["GET"])
def download_file(filename):
    for node, info in NODES.items():
        if MANUAL_TOGGLES.get(node, info["status"]) == "active":
            try:
                res = requests.get(f"{info['url']}/list", timeout=2)
                if res.status_code == 200:
                    files = res.json().get("files", [])

                    if filename in files:
                        return jsonify({
                            "message": f"File found in {node}",
                            "download_url": f"{info['url']}/download/{filename}"
                        }), 200
            except:
                pass

    return jsonify({"error": f"❌ File '{filename}' not found on any ACTIVE node"}), 404


# ============================================================
# ROOT
# ============================================================
@app.route("/", methods=["GET"])
def home():
    return jsonify({"message": "🚀 DFS Master Node Active", "nodes": list(NODES.keys())})


# ============================================================
# 🗑️ DELETE — FIX F-01: use .get() with default, use check_node_health()
# ============================================================
@app.route("/delete", methods=["POST"])
def delete_from_dfs():
    data = request.json
    filename = data.get("filename")

    if not filename:
        return jsonify({"error": "No filename provided"}), 400

    deleted_from = []

    for node, info in NODES.items():
        # FIX F-01: use .get() to avoid KeyError; check_node_health() is now defined
        toggle_state = MANUAL_TOGGLES.get(node, info["status"])
        if toggle_state != "active" or not check_node_health(node):
            continue

        try:
            url = f"{info['url']}/delete/{filename}"
            res = requests.delete(url, timeout=5)

            if res.status_code == 200:
                deleted_from.append(node)

        except:
            continue

    if len(deleted_from) == 0:
        return jsonify({"error": "File not found on any active node"}), 404

    return jsonify({
        "message": f"✅ {filename} deleted from DFS",
        "deleted_from": deleted_from
    })


if __name__ == "__main__":
    app.run(port=5000, debug=False)
