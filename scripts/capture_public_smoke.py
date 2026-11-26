"""Verify public probes and missing-key rejection; does not request secrets."""
import json
from pathlib import Path
import urllib.error
import urllib.request
from playwright.sync_api import sync_playwright

root = Path(__file__).resolve().parents[1]
base = "https://day14-agent-8reb.onrender.com"
results = {}
for route in ("health", "ready"):
    with urllib.request.urlopen(base + "/" + route, timeout=90) as response:
        results[route] = {"status": response.status, "body": json.load(response)}
request = urllib.request.Request(base + "/ask", data=b'{"question":"Hello"}', headers={"Content-Type":"application/json"})
try:
    urllib.request.urlopen(request, timeout=30)
    raise AssertionError("Missing key unexpectedly accepted")
except urllib.error.HTTPError as response:
    assert response.code == 401
    results["ask_without_key"] = {"status": response.code, "body": json.load(response)}
(root / "evidence/public-deployment-smoke.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
with sync_playwright() as p:
    browser = p.chromium.launch(executable_path=r"C:\Program Files\Google\Chrome\Application\chrome.exe", headless=True)
    page = browser.new_page(viewport={"width": 1450, "height": 1100})
    page.goto(base + "/docs", wait_until="networkidle", timeout=90000)
    operation = page.locator("#operations-default-ask_ask_post")
    if not operation.count():
        operation = page.locator(".opblock-post").first
    operation.locator(".opblock-summary").click()
    operation.get_by_role("button", name="Try it out").click()
    operation.locator("textarea").fill('{"question":"Hello"}')
    operation.get_by_role("button", name="Execute", exact=True).click()
    operation.locator(".responses-wrapper .response-col_status", has_text="401").first.wait_for(timeout=60000)
    operation.locator(".responses-wrapper").screenshot(path=str(root / "screenshots/test.png"))
    browser.close()
print(json.dumps(results, indent=2))
