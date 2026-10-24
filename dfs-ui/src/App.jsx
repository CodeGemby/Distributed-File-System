import React, { useState, useEffect, useRef } from "react";
import {
  LineChart,
  Line,
  CartesianGrid,
  XAxis,
  YAxis,
  Tooltip,
  Legend,
  BarChart,
  Bar,
  ResponsiveContainer,
} from "recharts";

function App() {
  const [nodes, setNodes] = useState([]);
  const [logs, setLogs] = useState([]);
  const [files, setFiles] = useState({});
  const [uploading, setUploading] = useState(false);

  const [metrics, setMetrics] = useState([]);
  const METRIC_SAMPLES = 36;

  const fileRef = useRef(null);
  const MASTER_URL = "http://127.0.0.1:5000";

  const countUploadsLastMinute = () => {
    const cutoff = Date.now() - 60000;
    let count = 0;

    for (let i = logs.length - 1; i >= 0; i--) {
      const line = logs[i];
      const match = line.match(/^(\d{1,2}:\d{2}:\d{2}) → /);
      if (!match) continue;

      const [h, m, s] = match[1].split(":").map(Number);
      const now = new Date();
      let ts = new Date(now.getFullYear(), now.getMonth(), now.getDate(), h, m, s).getTime();

      if (ts > Date.now() + 2000) ts -= 86400000;
      if (ts < cutoff) break;

      if (line.toLowerCase().includes("uploaded") || line.toLowerCase().includes("replicated"))
        count++;
    }
    return count;
  };

  const fetchNodes = async () => {
    try {
      const res = await fetch(`${MASTER_URL}/nodes`);
      const data = await res.json();
      setNodes(data);

      const active = data.filter((n) => n.status === "active").length;
      const down = data.filter((n) => n.status === "down").length;

      const uploads = countUploadsLastMinute();

      setMetrics((prev) => {
        const ts = new Date().toLocaleTimeString();
        const updated = [...prev, { ts, active, down, uploads }];
        if (updated.length > METRIC_SAMPLES) updated.shift();
        return updated;
      });
    } catch (err) {
      console.error(err);
    }
  };

  const fetchFiles = async () => {
    try {
      const res = await fetch(`${MASTER_URL}/list`);
      const data = await res.json();
      setFiles(data);
    } catch (err) {
      console.error(err);
    }
  };

  useEffect(() => {
    fetchNodes();
    fetchFiles();
    const i = setInterval(() => {
      fetchNodes();
      fetchFiles();
    }, 5000);
    return () => clearInterval(i);
  }, []);

  // FIX F-06: check res.ok before treating toggle as success
  const toggleNode = async (name) => {
    try {
      const res = await fetch(`${MASTER_URL}/toggle_node`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ node: name }),
      });
      const data = await res.json();

      if (!res.ok) {
        setLogs((p) => [...p, `${new Date().toLocaleTimeString()} → ❌ ${data.message || data.error}`]);
      } else {
        setLogs((p) => [...p, `${new Date().toLocaleTimeString()} → ${data.message}`]);
      }
      setTimeout(fetchNodes, 800);
    } catch (err) {
      console.error(err);
      setLogs((p) => [...p, `${new Date().toLocaleTimeString()} → ❌ Toggle failed (network error)`]);
    }
  };

  // FIX F-06: check res.ok for upload, display actual error from server
  const handleUpload = async () => {
    if (!fileRef.current.files.length) return alert("Select a file!");

    const form = new FormData();
    form.append("file", fileRef.current.files[0]);

    setUploading(true);
    try {
      const res = await fetch(`${MASTER_URL}/upload`, { method: "POST", body: form });
      const data = await res.json();

      if (!res.ok) {
        setLogs((p) => [...p, `${new Date().toLocaleTimeString()} → ❌ Upload failed: ${data.error || "Unknown error"}`]);
      } else {
        setLogs((p) => [...p, `${new Date().toLocaleTimeString()} → ${data.message}`]);
        fetchFiles();
      }
    } catch (err) {
      console.error(err);
      setLogs((p) => [...p, `${new Date().toLocaleTimeString()} → ❌ Upload failed (network error)`]);
    } finally {
      setUploading(false);
      fileRef.current.value = "";
    }
  };

  const handleDownload = async (fname) => {
    try {
      const res = await fetch(`${MASTER_URL}/download/${fname}`);
      const data = await res.json();

      if (!res.ok) return alert(data.error || "Download failed");

      const a = document.createElement("a");
      a.href = data.download_url;
      a.download = fname;
      a.click();
    } catch (err) {
      console.error(err);
      alert("Download failed!");
    }
  };

  // FIX F-06: check res.ok for delete, display actual server error/success
  const handleDelete = async (fname) => {
    if (!window.confirm(`Delete file: ${fname}?`)) return;
    try {
      const res = await fetch(`${MASTER_URL}/delete`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ filename: fname }),
      });
      const data = await res.json();

      if (!res.ok) {
        setLogs((prev) => [...prev, `${new Date().toLocaleTimeString()} → ❌ Delete failed: ${data.error || "Unknown error"}`]);
      } else {
        setLogs((prev) => [...prev, `${new Date().toLocaleTimeString()} → ✅ ${data.message || "Deleted " + fname}`]);
        fetchFiles();
      }
    } catch (error) {
      console.error(error);
      setLogs((prev) => [...prev, `${new Date().toLocaleTimeString()} → ❌ Delete failed (network error)`]);
    }
  };

  const uniqueFiles = () => {
    const set = new Set();
    Object.values(files).forEach((arr) => arr?.forEach?.((f) => set.add(f)));
    return [...set].sort();
  };

  return (
    <div className="min-h-screen bg-[#0b1221] text-white p-6 flex flex-col items-center">
      <h1 className="text-4xl font-bold text-blue-400 mb-6">❤️ Distributed File System Dashboard</h1>

      {/* Metrics */}
      <div className="bg-[#151c2c] p-5 rounded-2xl w-11/12 max-w-6xl mb-6 shadow-lg">
        <h2 className="text-xl font-semibold mb-3">📊 Live Cluster Metrics</h2>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="bg-[#0f1724] p-3 rounded">
            <ResponsiveContainer width="100%" height={200}>
              <LineChart data={metrics}>
                <CartesianGrid stroke="#222" strokeDasharray="3 3" />
                <XAxis dataKey="ts" />
                <YAxis />
                <Tooltip />
                <Legend />
                <Line type="monotone" dataKey="active" stroke="#22c55e" />
                <Line type="monotone" dataKey="down" stroke="#ef4444" />
              </LineChart>
            </ResponsiveContainer>
          </div>

          <div className="bg-[#0f1724] p-3 rounded">
            <ResponsiveContainer width="100%" height={200}>
              <BarChart data={metrics}>
                <CartesianGrid stroke="#222" strokeDasharray="3 3" />
                <XAxis dataKey="ts" />
                <YAxis />
                <Tooltip />
                <Bar dataKey="uploads" fill="#60A5FA" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      {/* Upload */}
      <div className="bg-[#151c2c] p-5 rounded-2xl w-11/12 max-w-4xl mb-6 shadow-lg">
        <h2 className="text-xl font-semibold mb-3">📤 Upload File</h2>
        <div className="flex gap-2">
          <input ref={fileRef} type="file" className="flex-grow bg-[#0d1324] p-2 rounded" />
          <button onClick={handleUpload} disabled={uploading} className="bg-blue-600 px-4 py-2 rounded hover:bg-blue-700">
            {uploading ? "Uploading..." : "Upload"}
          </button>
        </div>
      </div>

      {/* Nodes */}
      <div className="bg-[#151c2c] p-5 rounded-2xl w-11/12 max-w-4xl mb-6 shadow-lg">
        <h2 className="text-xl font-semibold mb-3">🖥️ Nodes Monitor</h2>
        <p className="text-sm text-gray-400 mb-3">Click a node to toggle it DOWN / ACTIVE (backend must be running to re-activate)</p>
        <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
          {nodes.map((n) => (
            <div
              key={n.name}
              onClick={() => toggleNode(n.name)}
              className={`p-4 rounded-xl text-center cursor-pointer ${
                n.status === "active" ? "bg-green-600 hover:bg-green-700" : "bg-red-600 hover:bg-red-700"
              }`}
            >
              {n.name} — {n.status.toUpperCase()}
            </div>
          ))}
        </div>
      </div>

      {/* Files */}
      <div className="bg-[#151c2c] p-5 rounded-2xl w-11/12 max-w-4xl mb-6 shadow-lg">
        <h2 className="text-xl font-semibold mb-3">📁 Files on DFS</h2>

        {uniqueFiles().length === 0 && <p className="text-gray-400">No files available. Upload a file to get started.</p>}

        {uniqueFiles().map((fname) => (
          <div key={fname} className="flex justify-between items-center bg-[#0f1724] p-3 rounded mb-2">
            <div>
              <p className="font-semibold">{fname}</p>
              <p className="text-sm text-gray-400">
                Present on:
                {Object.entries(files)
                  .filter(([_, arr]) => Array.isArray(arr) && arr.includes(fname))
                  .map(([node]) => ` ${node}`)
                  .join(", ")}
              </p>
            </div>

            <div className="flex gap-2">
              <button onClick={() => handleDownload(fname)} className="px-3 py-1 bg-blue-600 rounded hover:bg-blue-700">
                Download
              </button>

              <button onClick={() => handleDelete(fname)} className="px-3 py-1 bg-red-600 rounded hover:bg-red-700">
                Delete
              </button>
            </div>
          </div>
        ))}
      </div>

      {/* Logs */}
      <div className="bg-[#151c2c] p-5 rounded-2xl w-11/12 max-w-4xl shadow-lg">
        <h2 className="text-xl font-semibold mb-3">🧾 System Logs</h2>
        <div className="h-48 overflow-y-auto bg-[#0d1324] text-gray-300 p-3 rounded font-mono text-sm">
          {logs.length === 0 && <p className="text-gray-500">No activity yet.</p>}
          {logs.map((l, i) => (
            <p key={i} className={l.includes("❌") ? "text-red-400" : l.includes("✅") ? "text-green-400" : ""}>• {l}</p>
          ))}
        </div>
      </div>
    </div>
  );
}

export default App;
