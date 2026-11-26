"""During chaos E, demonstrate the quality regression on the real stack."""
import json
from pathlib import Path
import subprocess
import sys
import time
import urllib.request

root = Path(__file__).resolve().parents[1]
for _ in range(90):
    try:
        with urllib.request.urlopen("http://localhost:8080/health", timeout=2) as response:
            if json.load(response).get("agent_version") == "v1":
                break
    except OSError:
        pass
    time.sleep(4)
else:
    raise RuntimeError("Did not observe chaos E version v1")
with (root / "evidence/eval_production_v1.txt").open("w", encoding="utf-8") as log:
    result = subprocess.run([sys.executable, "-X", "utf8", "eval/run_eval.py",
        "--url", "http://localhost:8080", "--api-key", "day14-lab-key",
        "--baseline", str(root / "reports/eval_v2_fixed.json"),
        "--out", str(root / "reports/eval_production_v1.json")],
        cwd=root / "06-lab-complete/benchmark-observability/develop", stdout=log, stderr=subprocess.STDOUT)
assert result.returncode == 1, "Version v1 should fail quality gate against fixed v2"
print("Production v1 regression detected: quality gate exit 1")
