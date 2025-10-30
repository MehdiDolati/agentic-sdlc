import subprocess
import time
import urllib.request
import threading

# Start the server
server = subprocess.Popen([
    'uvicorn', 'test_app:app', 
    '--host', '127.0.0.1', 
    '--port', '8006', 
    '--log-level', 'debug'
], cwd=r'c:\Users\Mehdi\Projects\agentic\agentic-sdlc', stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)

# Wait for server to start
time.sleep(2)

def read_output():
    for line in server.stdout:
        print(f'SERVER: {line.strip()}')

# Start reading output in a thread
output_thread = threading.Thread(target=read_output)
output_thread.start()

try:
    # Make a request with urllib
    # nosemgrep: python.lang.security.audit.insecure-transport.urllib.insecure-urlopen.insecure-urlopen
    with urllib.request.urlopen('http://127.0.0.1:8006/') as response:
        print(f'Status: {response.status}')
        print(f'Content: {response.read().decode()}')
except Exception as e:
    print(f'Error: {e}')

# Wait a bit for output
time.sleep(1)

# Kill the server
server.terminate()
server.wait()