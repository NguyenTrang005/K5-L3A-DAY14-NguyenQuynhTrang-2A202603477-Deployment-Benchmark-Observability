"""Run original load/eval tools and retain their real outputs."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
DEVELOP = ROOT / "06-lab-complete/benchmark-observability/develop"
REPORTS = ROOT / "reports"
EVIDENCE = ROOT / "evidence"
REPORTS.mkdir(exist_ok=True)
EVIDENCE.mkdir(exist_ok=True)
ENV = {**os.environ, "PYTHONUTF8": "1", "PYTHONUNBUFFERED": "1"}
ENV.pop("AGENT_API_KEY", None)

def run_tool(name, arguments):
    with (EVIDENCE / (name + ".txt")).open("w", encoding="utf-8") as output:
        result = subprocess.run([sys.executable, "-X", "utf8", *arguments], cwd=DEVELOP,
                                env=ENV, stdout=output, stderr=subprocess.STDOUT)
    print(f"{name}: exit {result.returncode}", flush=True)
    if result.returncode not in (0, 1):
        raise RuntimeError(name)
    return result.returncode

class Agent:
    def __init__(self, version, port, slow=.03, error=.01):
        self.port = port
        self.log = (EVIDENCE / f"part7-{version}-{port}-slow-{slow}.txt").open("a", encoding="utf-8")
        env = {**ENV, "PORT": str(port), "AGENT_VERSION": version,
               "MOCK_SLOW_RATE": str(slow), "MOCK_ERROR_RATE": str(error),
               "LLM_MODEL": "mock-llm-small"}
        self.process = subprocess.Popen([sys.executable, "app.py"], cwd=DEVELOP, env=env,
                                        stdout=self.log, stderr=subprocess.STDOUT,
                                        creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
        for _ in range(100):
            try:
                with urllib.request.urlopen(f"http://localhost:{port}/health", timeout=1) as response:
                    if json.load(response)["agent_version"] == version:
                        return
            except OSError:
                time.sleep(.1)
        self.stop()
        raise RuntimeError("Agent did not start")

    def stop(self):
        if self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait()
        self.log.close()

def evaluate(name, port, baseline=None, minimum=.8):
    args = ["eval/run_eval.py", "--url", f"http://localhost:{port}", "--out",
            str(REPORTS / (name + ".json")), "--min-accuracy", str(minimum)]
    if baseline:
        args.extend(["--baseline", str(REPORTS / (baseline + ".json"))])
    return run_tool(name, args)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("phase", choices=["baseline", "fixed"])
    args = parser.parse_args()
    if args.phase == "fixed":
        agent = Agent("v2", 8002)
        try:
            assert evaluate("eval_v2_fixed", 8002, "eval_v2", 1.0) == 0
        finally:
            agent.stop()
        return
    v1 = Agent("v1", 8001)
    v2 = Agent("v2", 8002)
    try:
        evaluate("eval_v1", 8001)
        evaluate("eval_v2", 8002, "eval_v1")
        code = evaluate("eval_v1_regression", 8001, "eval_v2")
        assert code == 1, "Regression should fail the quality gate"
        for concurrency in (1, 10, 50, 100):
            name = f"load_v2_c{concurrency}"
            run_tool(name, ["load_test.py", "--url", "http://localhost:8002", "--requests", "300",
                            "--concurrency", str(concurrency), "--out", str(REPORTS / (name + ".json"))])
    finally:
        v1.stop()
        v2.stop()
    for slow in (0, .03, .1):
        agent = Agent("v2", 8002, slow=slow)
        try:
            name = f"load_v2_slow_{slow}"
            run_tool(name, ["load_test.py", "--url", "http://localhost:8002", "--requests", "300",
                            "--concurrency", "20", "--out", str(REPORTS / (name + ".json"))])
        finally:
            agent.stop()

if __name__ == "__main__":
    main()
