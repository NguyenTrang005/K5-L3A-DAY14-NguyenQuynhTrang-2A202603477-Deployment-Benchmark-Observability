"""Run real fault experiments and preserve Prometheus observations and screenshots.

A+B are deliberately combined to capture two alerts simultaneously; their
effects are not claimed to be isolated single-variable measurements.
"""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
PROD = ROOT / "06-lab-complete/benchmark-observability/production"
COMPOSE = ["docker", "compose", "-p", "k5-day14-observability"]
DEFAULT = {**os.environ, "AGENT_API_KEY": "day14-lab-key", "AGENT_VERSION": "v2",
           "LLM_MODEL": "mock-llm-small", "MOCK_LATENCY_MS": "120",
           "MOCK_ERROR_RATE": "0.01", "MOCK_SLOW_RATE": "0.03"}
EVIDENCE = ROOT / "evidence"
OUTPUT = EVIDENCE / "chaos-experiments.json"

def compose(args, env=DEFAULT):
    subprocess.run(COMPOSE + args, cwd=PROD, env=env, check=True,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

def api(path):
    return json.load(urllib.request.urlopen("http://localhost:9090/api/v1/" + path, timeout=5))

def capture(url, filename):
    subprocess.run([sys.executable, "-X", "utf8", str(ROOT / "scripts/capture_lab_page.py"),
                    url, str(ROOT / "screenshots" / filename), "--wait", "3"], check=True)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--scenario", choices=["all", "A", "B", "AB", "C", "D", "E"], default="all")
    args = parser.parse_args()
    data = json.loads(OUTPUT.read_text(encoding="utf-8")) if OUTPUT.exists() else {}
    scenarios = {
        "A": ({"MOCK_ERROR_RATE": "0.2"}, {"AgentHighErrorRate"}, 160),
        "B": ({"MOCK_SLOW_RATE": "0.3"}, {"AgentHighLatencyP95"}, 225),
        "AB": ({"MOCK_ERROR_RATE": "0.2", "MOCK_SLOW_RATE": "0.3"}, {"AgentHighErrorRate", "AgentHighLatencyP95"}, 225),
        "C": ({"LLM_MODEL": "mock-llm-large"}, {"LLMCostBurnRateHigh"}, 225),
        "D": ({}, {"AgentInstanceDown"}, 110),
        "E": ({"AGENT_VERSION": "v1"}, set(), 65),
    }
    with (EVIDENCE / "part7-chaos-load.txt").open("a", encoding="utf-8") as log:
        log.write(f"\n=== Scenario {args.scenario} at {datetime.now(timezone.utc).isoformat()} ===\n")
        log.flush()
        load = subprocess.Popen(COMPOSE + ["run", "--rm", "--no-deps", "--name", "day14-chaos-load", "locust",
             "-f", "/mnt/locust/locustfile.py", "--host", "http://nginx", "--headless", "-u", "30", "-r", "5", "-t", "20m"],
             cwd=PROD, env=DEFAULT, stdout=log, stderr=subprocess.STDOUT)
        paused = None
        try:
            for name, (changes, expected, limit) in scenarios.items():
                if args.scenario not in ("all", name):
                    continue
                env = {**DEFAULT, **changes}
                started = time.monotonic()
                result = {"started_utc": datetime.now(timezone.utc).isoformat(), "changes": changes,
                          "users": 30, "replicas": 3, "expected_alerts": sorted(expected),
                          "first_firing_seconds": {}, "observations": []}
                # A fresh Prometheus data volume isolates each alert timing trial.
                compose(["up", "-d", "--no-build", "--no-deps", "--force-recreate", "--scale", "agent=3", "agent"], env)
                compose(["up", "-d", "--no-deps", "--force-recreate", "--renew-anon-volumes", "prometheus"], env)
                if name == "D":
                    ids = subprocess.check_output(COMPOSE + ["ps", "-q", "agent"], cwd=PROD, text=True).split()
                    paused = ids[0]
                    subprocess.run(["docker", "pause", paused], check=True, stdout=subprocess.DEVNULL)
                    result["paused_container"] = paused
                simultaneous = False
                while time.monotonic() - started < limit:
                    try:
                        alerts = api("alerts")["data"]["alerts"]
                        elapsed = round(time.monotonic() - started, 2)
                        firing = {a["labels"]["alertname"] for a in alerts if a["state"] == "firing"}
                        result["observations"].append({"elapsed_s": elapsed, "alerts": alerts})
                        for alert in firing:
                            result["first_firing_seconds"].setdefault(alert, elapsed)
                        if expected and expected <= firing:
                            simultaneous = True
                            capture("http://localhost:9090/alerts", "prometheus-alert-firing.png" if name == "AB" else f"alert-{name}.png")
                            break
                    except (OSError, ValueError):
                        pass
                    time.sleep(5)
                result["observation_seconds"] = round(time.monotonic() - started, 2)
                result["expected_observed"] = simultaneous if expected else True
                try:
                    result["targets"] = api("targets")
                    result["rules"] = api("rules")
                except OSError:
                    pass
                capture("http://localhost:3000/d/day14-agent-overview?from=now-5m&to=now&refresh=5s", f"grafana-{name}.png")
                if paused:
                    subprocess.run(["docker", "unpause", paused], check=True, stdout=subprocess.DEVNULL)
                    paused = None
                data[name] = result
                OUTPUT.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
                print(name, result["first_firing_seconds"], "expected_observed", result["expected_observed"], flush=True)
        finally:
            if paused:
                subprocess.run(["docker", "unpause", paused], stdout=subprocess.DEVNULL)
            subprocess.run(["docker", "stop", "day14-chaos-load"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            try:
                load.wait(timeout=20)
            except subprocess.TimeoutExpired:
                load.terminate()
            compose(["up", "-d", "--no-build", "--no-deps", "--scale", "agent=3", "agent"], DEFAULT)

if __name__ == "__main__":
    main()
