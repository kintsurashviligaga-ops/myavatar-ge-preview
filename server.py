from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
import json

UPSTREAM = "https://myavatar.ge/api/chat/gemini"

class Handler(SimpleHTTPRequestHandler):
    def do_POST(self):
        if self.path != "/api/agent-g":
            self.send_error(404)
            return
        length = int(self.headers.get("Content-Length", "0"))
        if length <= 0 or length > 1_000_000:
            self.send_error(400, "Invalid request body")
            return
        body = self.rfile.read(length)
        try:
            payload = json.loads(body)
            messages = payload.get("messages")
            if not isinstance(messages, list) or not messages:
                raise ValueError("messages array is required")
            upstream_body = json.dumps({
                "messages": messages[-20:],
                "language": payload.get("language", "ka"),
                "tier": "free",
            }).encode()
            req = Request(UPSTREAM, data=upstream_body, headers={"Content-Type": "application/json"}, method="POST")
            with urlopen(req, timeout=60) as response:
                self.send_response(response.status)
                self.send_header("Content-Type", "text/event-stream; charset=utf-8")
                self.send_header("Cache-Control", "no-cache")
                self.send_header("Connection", "keep-alive")
                self.end_headers()
                while True:
                    chunk = response.read(4096)
                    if not chunk:
                        break
                    self.wfile.write(chunk)
                    self.wfile.flush()
        except (HTTPError, URLError, TimeoutError) as exc:
            self.send_response(502)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"error": "Agent G upstream unavailable", "detail": str(exc)}).encode())
        except (ValueError, json.JSONDecodeError) as exc:
            self.send_error(400, str(exc))
        except Exception as exc:
            self.send_response(500)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"error": "Agent G proxy error", "detail": str(exc)}).encode())

    def log_message(self, fmt, *args):
        print("[preview]", fmt % args, flush=True)

if __name__ == "__main__":
    ThreadingHTTPServer(("0.0.0.0", 4173), Handler).serve_forever()
