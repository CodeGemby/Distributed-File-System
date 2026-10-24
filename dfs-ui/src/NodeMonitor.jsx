 import React, { useEffect, useState } from "react";

const NodeMonitor = () => {
  const [nodes, setNodes] = useState([]);
  const [logs, setLogs] = useState([]);

  // ✅ Fetch node data from Flask master
  const fetchNodes = async () => {
    try {
      const res = await fetch("http://127.0.0.1:5000/nodes");
      const data = await res.json();
      setNodes(data);
    } catch (err) {
      console.error("Error fetching nodes:", err);
    }
  };

  // 🔁 Auto refresh every 5 seconds
  useEffect(() => {
    fetchNodes();
    const interval = setInterval(fetchNodes, 5000);
    return () => clearInterval(interval);
  }, []);

  // ⚙️ Toggle node status (simulation)
  const toggleNode = (nodeName) => {
    setNodes((prev) =>
      prev.map((n) => {
        if (n.name === nodeName) {
          const newStatus = n.status === "active" ? "down" : "active";
          setLogs((l) => [
            ...l,
            `🔄 ${nodeName} changed to ${newStatus.toUpperCase()}`,
          ]);
          return { ...n, status: newStatus };
        }
        return n;
      })
    );
  };

  return (
    <div className="p-6 text-white">
      <h1 className="text-3xl font-bold mb-6 text-blue-400 text-center">
        ⚙️ Node Monitoring Panel
      </h1>

      {/* 🧩 Node Grid */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {nodes.map((node) => (
          <div
            key={node.name}
            className={`p-4 rounded-xl shadow-md transition-all duration-300 ${
              node.status === "active"
                ? "bg-green-700/40 border border-green-400"
                : "bg-red-800/40 border border-red-500"
            }`}
          >
            <h2 className="text-xl font-semibold">{node.name}</h2>
            <p className="text-sm text-gray-300">{node.url}</p>
            <p className="mt-2">
              Status:{" "}
              <span
                className={
                  node.status === "active" ? "text-green-400" : "text-red-400"
                }
              >
                {node.status.toUpperCase()}
              </span>
            </p>
            <button
              onClick={() => toggleNode(node.name)}
              className={`mt-4 px-4 py-2 rounded-lg font-semibold ${
                node.status === "active"
                  ? "bg-red-500 hover:bg-red-600"
                  : "bg-green-500 hover:bg-green-600"
              }`}
            >
              {node.status === "active" ? "Set Down" : "Recover Node"}
            </button>
          </div>
        ))}
      </div>

      {/* 🧾 System Logs */}
      <div className="mt-8 p-4 bg-gray-800 rounded-lg shadow-lg">
        <h2 className="text-xl font-semibold text-blue-400 mb-2">🧾 System Logs</h2>
        {logs.length === 0 ? (
          <p className="text-gray-400 italic">No events yet…</p>
        ) : (
          <ul className="max-h-64 overflow-y-auto space-y-1 text-sm">
            {logs.map((log, i) => (
              <li key={i} className="text-gray-200">
                {log}
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
};

export default NodeMonitor;
