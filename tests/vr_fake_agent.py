"""A loopback HTTP server that plays the host helper: scripted body, delay and status code."""

import json
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


class FakeAgent:
    """Context manager; `url` is the /status address, `hits` counts requests received."""

    def __init__(self, body=None, delay=0.0, code=200, raw=None):
        self.body, self.delay, self.code, self.raw = body, delay, code, raw
        self.hits = 0
        agent = self

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                agent.hits += 1
                time.sleep(agent.delay)
                data = agent.raw if agent.raw is not None else json.dumps(agent.body).encode()
                try:
                    self.send_response(agent.code)
                    self.send_header("Content-Length", str(len(data)))
                    self.end_headers()
                    self.wfile.write(data)
                except OSError:
                    return  # the client gave up (a timeout): nothing to tell it

            def log_message(self, format, *args):
                return

        self._server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self._server.daemon_threads = True
        self.url = f"http://127.0.0.1:{self._server.server_address[1]}/status"

    def __enter__(self):
        threading.Thread(target=self._server.serve_forever, daemon=True).start()
        return self

    def __exit__(self, *exc):
        self._server.shutdown()
        self._server.server_close()
