from __future__ import annotations

import functools
import http.server
import threading
from pathlib import Path

import pytest

DEMO_APP_DIR = Path(__file__).parent / "fixtures" / "demo_app"


@pytest.fixture(scope="session")
def demo_app_url() -> str:
    """Serves tests/fixtures/demo_app over real HTTP — storage-state (localStorage/cookies)
    persistence only works for http(s) origins, not file:// pages."""
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(DEMO_APP_DIR))
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    port = server.server_address[1]
    try:
        yield f"http://127.0.0.1:{port}/index.html"
    finally:
        server.shutdown()
        thread.join()
