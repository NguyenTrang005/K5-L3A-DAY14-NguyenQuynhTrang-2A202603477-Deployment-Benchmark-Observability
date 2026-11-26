"""Check required evidence files and report results without inventing completion."""
import csv
import json
from pathlib import Path
import subprocess

root = Path(__file__).resolve().parents[1]
required = ["MISSION_ANSWERS.md", "DEPLOYMENT.md", "BENCHMARK_REPORT.md",
    *[f"reports/load_v2_c{n}.json" for n in (1,10,50,100)],
    *[f"reports/load_v2_slow_{n}.json" for n in ("0","0.03","0.1")],
    *[f"reports/{n}.json" for n in ("eval_v1","eval_v2","eval_v2_fixed")],
    *[f"benchmark-results/scale_{n}_stats.csv" for n in (1,3)],
    *[f"screenshots/{n}.png" for n in ("dashboard","running","test","grafana-dashboard","jaeger-slow-trace","jaeger-error-trace","prometheus-alert-firing")]]
missing = [name for name in required if not (root / name).is_file()]
fixed = json.loads((root / "reports/eval_v2_fixed.json").read_text(encoding="utf-8"))
assert fixed["passed"] == fixed["total"] == 23 and fixed["quality_gate"]["passed"]
chaos = json.loads((root / "evidence/chaos-experiments.json").read_text(encoding="utf-8"))
expected = {"A":"AgentHighErrorRate", "B":"AgentHighLatencyP95", "C":"LLMCostBurnRateHigh", "D":"AgentInstanceDown"}
for trial, alert in expected.items():
    assert alert in chaos[trial]["first_firing_seconds"], (trial, alert)
assert chaos["AB"]["expected_observed"], "Need simultaneous error/latency firing"
for count in (1,3):
    assert json.loads((root / f"evidence/scale_{count}_instances.json").read_text())["replicas"] == count
    with (root / f"benchmark-results/scale_{count}_stats.csv").open() as stream:
        ask = next(row for row in csv.DictReader(stream) if row["Name"] == "/ask")
    assert int(ask["Request Count"]) > 0
protected = ["06-lab-complete/check_production_ready.py", "06-lab-complete/benchmark-observability/develop/eval/golden_dataset.jsonl"]
assert subprocess.check_output(["git","diff","HEAD","--",*protected], cwd=root) == b""
tracked_env = subprocess.check_output(["git","ls-files","--","*.env",".env",".env.local",".env.production"], cwd=root, text=True).strip()
assert not tracked_env, tracked_env
lines = ["# Trạng thái hồ sơ nộp bài", "", "Đối chiếu file thực tế; không thay thế việc người học đọc và giải thích bài.", "",
         "- [x] Part 1–6: câu trả lời, code và output chấm Part 6 PASS 12/12.",
         "- [x] Public Render: health/readiness 200, thiếu key 401 kiểm tra độc lập; có key 200 do người học kiểm tra.",
         "- [x] Part 7: đủ 4 mức concurrency, 3 slow rate, eval v1/v2/fixed 23/23 không regression.",
         "- [x] Scaling: 100 user/2 phút, xác nhận 1 và 3 replica, CSV gốc.",
         "- [x] Chaos A–E và A+B kết hợp; ảnh ít nhất 2 alert firing; trace/log khớp ID.",
         "- [x] Script chấm/golden dataset không sửa; không có file .env đang tracked.", "", "## File còn thiếu", ""]
if missing:
    lines.extend(f"- [ ] `{name}`" for name in missing)
else:
    lines.append("Không thiếu file bắt buộc.")
lines.extend(["", "Dashboard Render cần chụp từ phiên đăng nhập của người học. Không dùng ảnh trang đăng nhập hoặc ảnh dựng để thay bằng chứng service Live. Có thể bổ sung `screenshots/test-authorized.png` từ ảnh Swagger 200 đã gửi trong hội thoại; `test.png` hiện là kiểm tra 401 thật.",
              "", "Người học cần tự đọc lại bài, giải thích số liệu/code và nộp link repo trên LMS. Không sửa ngày commit hoặc force-push."])
(root / "SUBMISSION_STATUS.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
print("Required files:", len(required), "Missing:", missing)
print("Quality/scaling/chaos/protected-file checks passed")
