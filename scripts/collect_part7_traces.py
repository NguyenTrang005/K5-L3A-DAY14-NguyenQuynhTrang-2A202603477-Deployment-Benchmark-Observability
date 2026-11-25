"""Save original OTLP trace responses and matching JSON application logs."""
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import subprocess
import urllib.parse
import urllib.request

root = Path(__file__).resolve().parents[1]
prod = root / "06-lab-complete/benchmark-observability/production"
output = subprocess.check_output(["docker", "compose", "-p", "k5-day14-observability", "logs", "--no-color", "agent"],
                                 cwd=prod, encoding="utf-8", errors="replace")
logs = []
for line in output.splitlines():
    start = line.find("{")
    if start >= 0:
        try:
            entry = json.loads(line[start:])
            if entry.get("trace_id"):
                logs.append(entry)
        except ValueError:
            pass
now = datetime.now(timezone.utc)
params = urllib.parse.urlencode({"query.serviceName": "observable-agent",
    "query.startTimeMin": (now - timedelta(minutes=30)).isoformat(),
    "query.startTimeMax": now.isoformat(), "query.searchDepth": 1000})
summaries = json.load(urllib.request.urlopen("http://localhost:16686/api/v3/trace-summaries?" + params))["summaries"]
available = {entry["trace_id"] for entry in logs}
slow = max((s for s in summaries if s["traceId"] in available), key=lambda s: int(s["maxEndTimeUnixNano"]) - int(s["minStartTimeUnixNano"]))
error_log = next(entry for entry in reversed(logs) if entry.get("event") == "llm_error")
metadata = {}
for name, trace_id in (("slow", slow["traceId"]), ("error", error_log["trace_id"])):
    trace = json.load(urllib.request.urlopen("http://localhost:16686/api/v3/traces/" + trace_id))
    spans = [span for rs in trace["result"]["resourceSpans"] for scope in rs["scopeSpans"] for span in scope["spans"]]
    root_span = next(s for s in spans if s["name"] == "POST /ask")
    llm = next(s for s in spans if s["name"].startswith("chat "))
    duration = lambda s: (int(s["endTimeUnixNano"]) - int(s["startTimeUnixNano"])) / 1e6
    matching = [entry for entry in logs if entry["trace_id"] == trace_id]
    (root / f"evidence/{name}-trace.json").write_text(json.dumps(trace, indent=2, ensure_ascii=False), encoding="utf-8")
    metadata[name] = {"trace_id": trace_id, "total_ms": duration(root_span), "llm_ms": duration(llm),
        "llm_percent": duration(llm) / duration(root_span) * 100, "llm_span": llm["name"], "logs": matching,
        "exception_events": llm.get("events", [])}
(root / "evidence/part7-trace-analysis.json").write_text(json.dumps(metadata, indent=2, ensure_ascii=False), encoding="utf-8")
print(json.dumps({name: {k:v for k,v in value.items() if k not in ("logs","exception_events")} for name,value in metadata.items()}, indent=2))
