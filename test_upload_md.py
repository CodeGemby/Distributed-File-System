import requests
import json
import sys
import io

# Force UTF-8 output
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

MASTER = 'http://127.0.0.1:5000'

print("=" * 55)
print("  DFS Full Integration Test - .md File Upload")
print("=" * 55)

# 1. Master health
print("\n[1] Master health...")
r = requests.get(f'{MASTER}/', timeout=3)
print(f"   Status: {r.status_code}  Nodes: {r.json().get('nodes')}")

# 2. Node statuses
print("\n[2] Node statuses via /nodes...")
r = requests.get(f'{MASTER}/nodes', timeout=10)
nodes = r.json()
for n in nodes:
    print(f"   {n['name']}: {n['status']}")

# 3. Upload test .md file
md_content = b"""# Test Distributed File System

This is a sample Markdown file uploaded from the Desktop
to verify the DFS upload, replication, list, and download.

## Features Verified
- File upload with 3x replication
- Stream not reused (F-02 fix)
- Secure filename sanitization (F-08 fix)
- Absolute storage paths (F-05 fix)

## Status
PASS - File uploaded and replicated successfully.
"""

print("\n[3] Uploading test_from_desktop.md ...")
files = {'file': ('test_from_desktop.md', md_content, 'text/markdown')}
r = requests.post(f'{MASTER}/upload', files=files, timeout=15)
print(f"   HTTP {r.status_code}")
upload_result = r.json()
msg = upload_result.get('message', upload_result.get('error', str(upload_result)))
print(f"   Message: {msg}")
replicated = upload_result.get('replicated_nodes', [])
print(f"   Replicated to {len(replicated)} node(s): {replicated}")

assert r.status_code == 200, f"Upload should succeed, got: {upload_result}"
assert len(replicated) >= 1, "Should replicate to at least 1 node"

# 4. List files
print("\n[4] Listing files via /list ...")
r = requests.get(f'{MASTER}/list', timeout=5)
files_data = r.json()
for node, flist in files_data.items():
    if isinstance(flist, list):
        tag = " <-- FOUND" if 'test_from_desktop.md' in flist else ""
        print(f"   {node}: {flist}{tag}")
    else:
        print(f"   {node}: {flist}")

found_on = [n for n, fl in files_data.items()
            if isinstance(fl, list) and 'test_from_desktop.md' in fl]
print(f"\n   'test_from_desktop.md' found on: {found_on}")
assert len(found_on) >= 1, "File should appear on at least 1 node"

# 5. Download lookup
print("\n[5] Download lookup via /download/test_from_desktop.md ...")
r = requests.get(f'{MASTER}/download/test_from_desktop.md', timeout=5)
dl_data = r.json()
print(f"   HTTP {r.status_code}  node_msg: {dl_data.get('message', dl_data.get('error'))}")
assert r.status_code == 200, f"Download lookup should succeed, got: {dl_data}"

download_url = dl_data['download_url']
r2 = requests.get(download_url, timeout=5)
print(f"   Direct download from node: HTTP {r2.status_code}, bytes={len(r2.content)}")
assert r2.status_code == 200
assert len(r2.content) >= len(md_content) * 0.9, f"Size mismatch too large: {len(r2.content)} vs {len(md_content)}"
# Normalise line endings before comparing content
orig_normalized = md_content.replace(b'\r\n', b'\n')
recv_normalized = r2.content.replace(b'\r\n', b'\n')
assert orig_normalized == recv_normalized, "Content mismatch after line-ending normalisation"
print("   Content MATCHES original (line-ending normalised)!")

# 6. Delete file
print("\n[6] Deleting test_from_desktop.md via /delete ...")
r = requests.post(f'{MASTER}/delete',
                  json={'filename': 'test_from_desktop.md'},
                  timeout=10)
del_result = r.json()
print(f"   HTTP {r.status_code}  deleted_from: {del_result.get('deleted_from', del_result.get('error'))}")
assert r.status_code == 200, f"Delete should succeed, got: {del_result}"

r = requests.get(f'{MASTER}/list', timeout=5)
files_after = r.json()
still_on = [n for n, fl in files_after.items()
            if isinstance(fl, list) and 'test_from_desktop.md' in fl]
print(f"   After delete, still on: {still_on}")
assert len(still_on) == 0, "File should be deleted from all nodes"

print("\n" + "=" * 55)
print("  ALL TESTS PASSED!")
print("=" * 55)
