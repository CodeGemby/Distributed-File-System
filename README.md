# 🗂️ Distributed File System (DFS)

A full-stack **Distributed File System** built with Python (Flask) backend and React (Vite) frontend. The system distributes and replicates files across multiple storage nodes with automatic recovery, health monitoring, and a real-time dashboard UI.

---

## 🏗️ Architecture

```
                    ┌──────────────┐
                    │   DFS UI     │
                    │  (React +    │
                    │   Vite)      │
                    └──────┬───────┘
                           │
                    ┌──────▼───────┐
                    │  Master Node │
                    │  (Port 5000) │
                    └──────┬───────┘
                           │
        ┌──────┬───────┬───┴───┬───────┐
        ▼      ▼       ▼       ▼       ▼
    ┌──────┐┌──────┐┌──────┐┌──────┐┌──────┐
    │Node 1││Node 2││Node 3││Node 4││Node 5│
    │:5001 ││:5002 ││:5003 ││:5004 ││:5005 │
    └──────┘└──────┘└──────┘└──────┘└──────┘
```

## ✨ Features

- **File Upload & Replication** — Files are automatically replicated across 3 random active nodes
- **File Download & Delete** — Download or delete files from any active node
- **5 Storage Nodes** — Independent Flask servers (ports 5001–5005)
- **Master Node** — Central coordinator handling routing, replication & health checks
- **Node Health Monitoring** — Real-time active/down status detection
- **Manual Node Toggle** — Manually bring nodes up/down via UI
- **Auto Recovery** — When a downed node comes back online, missing files are automatically synced from peers
- **React Dashboard** — Modern UI built with React, Tailwind CSS & Recharts

## 🛠️ Tech Stack

| Layer     | Technology                        |
|-----------|-----------------------------------|
| Backend   | Python, Flask, Flask-CORS         |
| Frontend  | React 19, Vite 7, Tailwind CSS   |
| Charts    | Recharts                          |
| HTTP      | Axios, Requests                   |

## 🚀 Getting Started

### Prerequisites
- Python 3.10+
- Node.js 18+

### 1. Clone the Repository
```bash
git clone https://github.com/codeGemby/Distributed-File-System.git
cd Distributed-File-System
```

### 2. Setup Python Environment
```bash
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # macOS/Linux

pip install flask flask-cors requests werkzeug
```

### 3. Start All Nodes (Quick Start)
```bash
start_dfs.bat
```
Or manually start each node:
```bash
python master/master.py          # Master on port 5000
python node1/server.py           # Node 1 on port 5001
python node2/server.py           # Node 2 on port 5002
python node3/server.py           # Node 3 on port 5003
python node4/server.py           # Node 4 on port 5004
python node5/server.py           # Node 5 on port 5005
```

### 4. Start the Frontend
```bash
cd dfs-ui
npm install
npm run dev
```

## 📁 Project Structure

```
distributed_file_system/
├── master/
│   └── master.py            # Master node - routing, replication, recovery
├── node1/
│   └── server.py            # Storage node 1
├── node2/
│   └── server.py            # Storage node 2
├── node3/
│   └── server.py            # Storage node 3
├── node4/
│   └── server.py            # Storage node 4
├── node5/
│   └── server.py            # Storage node 5
├── storage/                 # File storage directory for all nodes
├── dfs-ui/                  # React frontend dashboard
│   ├── src/
│   │   ├── App.jsx          # Main application component
│   │   └── NodeMonitor.jsx  # Node monitoring component
│   └── package.json
├── start_dfs.bat            # Quick start script (Windows)
├── test_health.py           # Health check test script
└── test_upload_md.py        # Upload test script
```

## 📡 API Endpoints

| Method   | Endpoint              | Description                  |
|----------|-----------------------|------------------------------|
| `GET`    | `/`                   | Master node status           |
| `GET`    | `/nodes`              | List all nodes with health   |
| `POST`   | `/upload`             | Upload & replicate a file    |
| `GET`    | `/list`               | List files across all nodes  |
| `GET`    | `/download/<filename>`| Find & download a file       |
| `POST`   | `/delete`             | Delete a file from all nodes |
| `POST`   | `/toggle_node`        | Toggle node active/down      |

## 👤 Author

**Vishal Yadav** — [@codeGemby](https://github.com/codeGemby)

## 📄 License

This project is open source and available under the [MIT License](LICENSE).
