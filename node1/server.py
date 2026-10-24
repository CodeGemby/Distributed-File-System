from flask import Flask, request, jsonify, send_from_directory
from werkzeug.utils import secure_filename
import os

app = Flask(__name__)

# NODE-1 SETTINGS — FIX F-05: use absolute path anchored to this script's location
PORT = 5001
NODE_NAME = "node1"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STORAGE_PATH = os.path.normpath(os.path.join(BASE_DIR, "..", "storage", NODE_NAME))
os.makedirs(STORAGE_PATH, exist_ok=True)

# ============================================================
# STATUS
# ============================================================
@app.route('/status', methods=['GET'])
def status():
    return jsonify({"message": "Node 1 active"}), 200

# ============================================================
# UPLOAD — FIX F-08: sanitize filename before saving
# ============================================================
@app.route('/upload', methods=['POST'])
def upload_file():
    try:
        file = request.files['file']
        filename = secure_filename(file.filename)   # FIX F-08
        if not filename:
            return jsonify({"error": "Invalid filename"}), 400
        save_path = os.path.join(STORAGE_PATH, filename)
        file.save(save_path)
        return jsonify({"message": f"File '{filename}' saved on Node 1"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ============================================================
# LIST FILES
# ============================================================
@app.route('/list', methods=['GET'])
def list_files():
    try:
        files = os.listdir(STORAGE_PATH)
        return jsonify({"files": files}), 200
    except:
        return jsonify({"error": "Error listing files"}), 500

# ============================================================
# DOWNLOAD FILE
# ============================================================
@app.route('/download/<filename>', methods=['GET'])
def download_file(filename):
    try:
        safe_name = secure_filename(filename)
        return send_from_directory(STORAGE_PATH, safe_name, as_attachment=True)
    except:
        return jsonify({"error": "File not found"}), 404

# ============================================================
# STORAGE ENDPOINT (RETURN SIZE IN KB)
# ============================================================
@app.route('/storage', methods=['GET'])
def get_storage():
    try:
        total_size = 0
        for f in os.listdir(STORAGE_PATH):
            fp = os.path.join(STORAGE_PATH, f)
            if os.path.isfile(fp):
                total_size += os.path.getsize(fp)
        return jsonify({"total_kb": round(total_size / 1024, 2)})
    except:
        return jsonify({"total_kb": 0})

# ============================================================
# DELETE FILE
# ============================================================
@app.route("/delete/<filename>", methods=["DELETE"])
def delete_file(filename):
    safe_name = secure_filename(filename)
    file_path = os.path.join(STORAGE_PATH, safe_name)

    if os.path.exists(file_path):
        os.remove(file_path)
        return jsonify({"message": f"{safe_name} deleted successfully"}), 200

    return jsonify({"error": "File not found"}), 404


# ============================================================
# START SERVER
# ============================================================
if __name__ == '__main__':
    app.run(port=PORT, debug=False)
