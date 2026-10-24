import requests, json

# Check master
try:
    r = requests.get('http://127.0.0.1:5000/', timeout=3)
    print('Master /:', r.status_code, r.json())
except Exception as e:
    print('Master ERROR:', e)

# Check nodes via master /nodes
try:
    r = requests.get('http://127.0.0.1:5000/nodes', timeout=10)
    nodes = r.json()
    for n in nodes:
        print('  ' + n['name'] + ': ' + n['status'])
except Exception as e:
    print('Nodes ERROR:', e)

# Direct node checks
for port in [5001, 5002, 5003, 5004, 5005]:
    try:
        r = requests.get(f'http://127.0.0.1:{port}/status', timeout=2)
        print(f'Node port {port}: {r.status_code} {r.json()}')
    except Exception as e:
        print(f'Node port {port} ERROR: {e}')

