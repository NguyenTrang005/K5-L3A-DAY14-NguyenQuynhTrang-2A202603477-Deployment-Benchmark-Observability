"""Run Part 4 examples in isolated Python processes; never print JWTs/keys."""
import os
from pathlib import Path
import secrets
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
CASES = {
    "develop": '''
from fastapi.testclient import TestClient
from app import app
import os
with TestClient(app) as client:
    for label, headers, expected in [
        ("missing key", {}, 401),
        ("wrong key (original Part 4 example)", {"X-API-Key": "invalid"}, 403),
        ("valid key", {"X-API-Key": os.environ["AGENT_API_KEY"]}, 200),
    ]:
        response = client.post("/ask", json={"question": "Hello"}, headers=headers)
        print(f"{label}: HTTP {response.status_code}")
        assert response.status_code == expected
''',
    "production": '''
from fastapi.testclient import TestClient
from app import app
from cost_guard import cost_guard
with TestClient(app) as client:
    assert client.post("/ask", json={"question":"Hello"}).status_code == 401
    print("JWT missing: HTTP 401")
    response = client.post("/auth/token", json={"username":"student","password":"demo123"})
    assert response.status_code == 200
    print("JWT login: HTTP 200 (token redacted)")
    headers = {"Authorization": "Bearer " + response.json()["access_token"]}
    codes = [client.post("/ask", json={"question":"Hello"}, headers=headers).status_code for _ in range(20)]
    print("20 requests:", codes)
    assert codes == [200] * 10 + [429] * 10
    assert client.get("/admin/stats", headers=headers).status_code == 403
    print("Student admin endpoint: HTTP 403")
    admin = client.post("/auth/token", json={"username":"teacher","password":"teach456"}).json()["access_token"]
    admin_headers = {"Authorization":"Bearer " + admin}
    assert client.get("/admin/stats", headers=admin_headers).status_code == 200
    cost_guard.daily_budget_usd = 0
    assert client.post("/ask", json={"question":"Hello"}, headers=admin_headers).status_code == 402
    print("Daily cost guard (budget=0): HTTP 402")
''',
}

lines = ["Part 4 verification using FastAPI TestClient (not a deployed service)"]
for folder, code in CASES.items():
    env = {**os.environ, "AGENT_API_KEY": secrets.token_urlsafe(24),
           "JWT_SECRET": secrets.token_urlsafe(32), "PYTHONUTF8": "1"}
    result = subprocess.run([sys.executable, "-X", "utf8", "-c", code],
                            cwd=ROOT / "04-api-gateway" / folder, env=env,
                            capture_output=True, text=True, encoding="utf-8")
    lines.extend([f"\n{folder}:", result.stdout])
    if result.returncode:
        print(result.stderr)
        raise SystemExit(result.returncode)
output = "\n".join(lines)
(ROOT / "evidence").mkdir(exist_ok=True)
(ROOT / "evidence" / "part4-check.txt").write_text(output, encoding="utf-8")
print(output)
