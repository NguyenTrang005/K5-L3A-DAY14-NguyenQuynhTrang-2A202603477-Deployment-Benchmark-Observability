"""Exercise 5.1/5.2: real HTTP and SIGTERM; run on Linux."""
import concurrent.futures
import json
import os
from pathlib import Path
import signal
import socket
import subprocess
import sys
import time
import urllib.request

assert os.name == "posix", "Run this verification in Linux/WSL"
root = Path(__file__).resolve().parents[1]
with socket.socket() as sock:
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
base = f"http://127.0.0.1:{port}"
evidence = root / "evidence"
evidence.mkdir(exist_ok=True)
with (evidence / "part5-shutdown-server.txt").open("w", encoding="utf-8") as log:
    server = subprocess.Popen([sys.executable, "-m", "uvicorn", "app:app", "--host", "127.0.0.1", "--port", str(port)],
                              cwd=root / "05-scaling-reliability" / "develop", stdout=log, stderr=log)
    try:
        for _ in range(100):
            try:
                with urllib.request.urlopen(base + "/ready", timeout=1) as response:
                    assert response.status == 200
                break
            except OSError:
                time.sleep(.1)
        else:
            raise RuntimeError("Server failed to start")
        with urllib.request.urlopen(base + "/health") as response:
            assert response.status == 200
        def request():
            req = urllib.request.Request(base + "/ask?question=Hello", method="POST")
            with urllib.request.urlopen(req, timeout=15) as response:
                return response.status
        # The supplied mock sleeps ~0.1s; signal during that interval.
        with concurrent.futures.ThreadPoolExecutor() as pool:
            pending = pool.submit(request)
            time.sleep(.05)
            server.send_signal(signal.SIGTERM)
            status = pending.result(timeout=20)
        code = server.wait(timeout=20)
        # Uvicorn 0.30 re-raises SIGTERM after successful cleanup on POSIX.
        assert status == 200 and code in (0, -signal.SIGTERM), (status, code)
        assert "Application shutdown complete" in (evidence / "part5-shutdown-server.txt").read_text(encoding="utf-8")
        result = {"health": 200, "ready": 200, "request_during_sigterm": status,
                  "exit_code": code, "environment": "Linux container", "signal_delay_seconds": .05}
        (evidence / "part5-shutdown.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
        print(json.dumps(result, indent=2))
    finally:
        if server.poll() is None:
            server.kill()
            server.wait()
