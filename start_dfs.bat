@echo off
echo ============================================
echo   🚀 Distributed File System - Launcher
echo ============================================
echo.

set DFS_ROOT=%~dp0

echo [1/6] Starting Node 1 on port 5001...
start "DFS-Node1" cmd /k "cd /d %DFS_ROOT% && venv\Scripts\python.exe node1\server.py"

echo [2/6] Starting Node 2 on port 5002...
start "DFS-Node2" cmd /k "cd /d %DFS_ROOT% && venv\Scripts\python.exe node2\server.py"

echo [3/6] Starting Node 3 on port 5003...
start "DFS-Node3" cmd /k "cd /d %DFS_ROOT% && venv\Scripts\python.exe node3\server.py"

echo [4/6] Starting Node 4 on port 5004...
start "DFS-Node4" cmd /k "cd /d %DFS_ROOT% && venv\Scripts\python.exe node4\server.py"

echo [5/6] Starting Node 5 on port 5005...
start "DFS-Node5" cmd /k "cd /d %DFS_ROOT% && venv\Scripts\python.exe node5\server.py"

echo.
echo Waiting 2 seconds for nodes to start...
timeout /t 2 /nobreak >nul

echo [6/6] Starting Master Node on port 5000...
start "DFS-Master" cmd /k "cd /d %DFS_ROOT% && venv\Scripts\python.exe master\master.py"

echo.
echo ============================================
echo   ✅ All 6 services started!
echo   Master:  http://127.0.0.1:5000
echo   Node 1:  http://127.0.0.1:5001
echo   Node 2:  http://127.0.0.1:5002
echo   Node 3:  http://127.0.0.1:5003
echo   Node 4:  http://127.0.0.1:5004
echo   Node 5:  http://127.0.0.1:5005
echo ============================================
echo.
echo Now open a new terminal and run:
echo   cd dfs-ui
echo   npm run dev
echo.
echo Or open http://localhost:5173 if dev server is already running.
echo.
pause

