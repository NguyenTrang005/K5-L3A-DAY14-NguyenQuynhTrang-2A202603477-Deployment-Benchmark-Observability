"""Benchmark exact replica counts; --no-deps prevents Compose resetting scale."""
import json
import os
from pathlib import Path
import subprocess
import time

ROOT = Path(__file__).resolve().parents[1]
PROD = ROOT / "06-lab-complete/benchmark-observability/production"
COMPOSE = ["docker", "compose", "-p", "k5-day14-observability"]
env = {**os.environ, "AGENT_VERSION": "v2", "LLM_MODEL": "mock-llm-small",
       "MOCK_ERROR_RATE": "0.01", "MOCK_SLOW_RATE": "0.03", "MOCK_LATENCY_MS": "120",
       "AGENT_API_KEY": "day14-lab-key"}
for replicas in (1, 3):
    subprocess.run(COMPOSE + ["up", "-d", "--no-build", "--scale", f"agent={replicas}"], cwd=PROD, env=env, check=True)
    time.sleep(15)
    ids = subprocess.check_output(COMPOSE + ["ps", "-q", "agent"], cwd=PROD, env=env, text=True).split()
    assert len(ids) == replicas, ids
    (ROOT / f"evidence/scale_{replicas}_instances.json").write_text(json.dumps({"replicas": replicas, "container_ids": ids,
        "mock_error_rate": .01, "mock_slow_rate": .03, "model": "mock-llm-small", "agent_version": "v2", "seconds": 120}, indent=2), encoding="utf-8")
    with (ROOT / f"evidence/part7-scale-{replicas}.txt").open("w", encoding="utf-8") as output:
        result = subprocess.run(COMPOSE + ["run", "--rm", "--no-deps", "locust", "-f", "/mnt/locust/locustfile.py",
            "--host", "http://nginx", "--headless", "-u", "100", "-r", "10", "-t", "2m", "--csv", f"/mnt/results/scale_{replicas}"],
            cwd=PROD, env=env, stdout=output, stderr=subprocess.STDOUT)
    assert result.returncode in (0, 1)
    print(f"scale {replicas}: complete (exit {result.returncode})", flush=True)
