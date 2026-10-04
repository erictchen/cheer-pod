"""
CheerPod Server - Cheer Stunt Group Web Application
Lightweight HTTP Server with REST API & SQLite Database
Zero external dependencies required.
"""
import http.server
import json
import os
import socket
import sys
import urllib.parse
from typing import Dict, Any

import database
import stunt_optimizer

PORT = 8000
STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")

class CheerAppRequestHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=STATIC_DIR, **kwargs)

    def _send_json(self, data: Any, status: int = 200):
        body = json.dumps(data, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
        self.wfile.write(body)

    def _read_json_body(self) -> Dict[str, Any]:
        content_length = int(self.headers.get("Content-Length", 0))
        if content_length > 0:
            raw = self.rfile.read(content_length).decode("utf-8")
            return json.loads(raw)
        return {}

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        # API Endpoints
        if path == "/api/athletes":
            athletes = database.get_all_athletes()
            self._send_json({"success": True, "athletes": athletes})
            return
            
        if path.startswith("/api/athletes/"):
            parts = path.strip("/").split("/")
            if len(parts) == 3 and parts[2].isdigit():
                ath_id = int(parts[2])
                ath = database.get_athlete(ath_id)
                if ath:
                    self._send_json({"success": True, "athlete": ath})
                else:
                    self._send_json({"success": False, "error": "Athlete not found"}, 404)
                return

        # Fallback to serving static files (index.html, style.css, app.js, etc.)
        if path == "/" or not os.path.exists(os.path.join(STATIC_DIR, path.lstrip("/"))):
            self.path = "/index.html"
        return super().do_GET()

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        if path == "/api/athletes":
            try:
                data = self._read_json_body()
                athlete = database.add_athlete(data)
                self._send_json({"success": True, "athlete": athlete}, 201)
            except Exception as e:
                self._send_json({"success": False, "error": str(e)}, 400)
            return

        if path == "/api/generate":
            try:
                data = self._read_json_body()
                mode = data.get("mode", "balanced")
                size_strategy = data.get("size_strategy", "auto")
                athlete_ids = set(data.get("athlete_ids", []))
                
                all_athletes = database.get_all_athletes()
                # Mark is_checked
                for a in all_athletes:
                    a["is_checked"] = (a["id"] in athlete_ids) if athlete_ids else bool(a.get("is_active", 1))
                
                result = stunt_optimizer.optimize_stunt_groups(
                    all_athletes,
                    mode=mode,
                    size_strategy=size_strategy
                )
                self._send_json({"success": True, **result})
            except Exception as e:
                self._send_json({"success": False, "error": str(e)}, 500)
            return

        if path == "/api/reset-demo":
            try:
                database.init_db(force_reset=True)
                athletes = database.get_all_athletes()
                self._send_json({"success": True, "message": "Demo data reset successfully", "athletes": athletes})
            except Exception as e:
                self._send_json({"success": False, "error": str(e)}, 500)
            return

        self._send_json({"success": False, "error": "Endpoint not found"}, 404)

    def do_PUT(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        if path.startswith("/api/athletes/"):
            parts = path.strip("/").split("/")
            if len(parts) == 3 and parts[2].isdigit():
                ath_id = int(parts[2])
                try:
                    data = self._read_json_body()
                    updated = database.update_athlete(ath_id, data)
                    if updated:
                        self._send_json({"success": True, "athlete": updated})
                    else:
                        self._send_json({"success": False, "error": "Athlete not found"}, 404)
                except Exception as e:
                    self._send_json({"success": False, "error": str(e)}, 400)
                return

        self._send_json({"success": False, "error": "Endpoint not found"}, 404)

    def do_DELETE(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        if path.startswith("/api/athletes/"):
            parts = path.strip("/").split("/")
            if len(parts) == 3 and parts[2].isdigit():
                ath_id = int(parts[2])
                try:
                    success = database.delete_athlete(ath_id)
                    if success:
                        self._send_json({"success": True, "message": "Athlete deleted"})
                    else:
                        self._send_json({"success": False, "error": "Athlete not found"}, 404)
                except Exception as e:
                    self._send_json({"success": False, "error": str(e)}, 400)
                return

        self._send_json({"success": False, "error": "Endpoint not found"}, 404)

def get_network_ip():
    try:
        import subprocess
        for iface in ["en0", "en1"]:
            out = subprocess.getoutput(f"ipconfig getifaddr {iface}").strip()
            if out and not out.startswith("ipconfig:") and "." in out:
                return out
    except Exception:
        pass
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"

def run(port=PORT):
    database.init_db(force_reset=False)
    server_address = ("0.0.0.0", port)
    httpd = http.server.ThreadingHTTPServer(server_address, CheerAppRequestHandler)
    net_ip = get_network_ip()
    print("=" * 60)
    print(f"🚀 CheerPod Server running and accessible at:")
    print(f"   💻 This Mac:          http://localhost:{port}/")
    print(f"   📱 Phone / iPad:      http://{net_ip}:{port}/")
    print(f"   🍏 Apple Device name: http://Erics-MacBook-Pro-2.local:{port}/")
    print(f"   (Ensure Phone/iPad are on the same Wi-Fi network)")
    print("=" * 60)
    print(f"📁 Serving static files from {STATIC_DIR}")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down server...")
        httpd.server_close()

if __name__ == "__main__":
    env_port = os.environ.get("PORT")
    if env_port and env_port.isdigit():
        port = int(env_port)
    elif len(sys.argv) > 1 and sys.argv[1].isdigit():
        port = int(sys.argv[1])
    else:
        port = PORT
    run(port)
