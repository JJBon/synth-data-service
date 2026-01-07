
import http.server
import socketserver
import os
import sys

PORT = 8000

print("DEBUG: STDLIB SERVER STARTING...", flush=True)
sys.stderr.write("DEBUG: STDLIB SERVER STARTING (STDERR)...\n")
sys.stderr.flush()

class Handler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        print(f"DEBUG: Received GET request: {self.path}", flush=True)
        self.send_response(200)
        self.send_header('Content-type', 'text/plain')
        self.end_headers()
        self.wfile.write(b"Hello from Stdlib Server")

try:
    with socketserver.TCPServer(("0.0.0.0", PORT), Handler) as httpd:
        print(f"DEBUG: Serving at port {PORT}", flush=True)
        httpd.serve_forever()
except Exception as e:
    print(f"CRITICAL: Server crashed: {e}", flush=True)
    sys.exit(1)
