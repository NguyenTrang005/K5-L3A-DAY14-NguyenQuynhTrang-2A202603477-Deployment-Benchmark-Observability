"""Capture actual browser-rendered evidence with a fresh headless profile."""
import argparse
from pathlib import Path
from playwright.sync_api import sync_playwright

parser = argparse.ArgumentParser()
parser.add_argument("url")
parser.add_argument("output")
parser.add_argument("--wait", type=float, default=6)
parser.add_argument("--trace", action="store_true")
args = parser.parse_args()
Path(args.output).parent.mkdir(parents=True, exist_ok=True)
with sync_playwright() as p:
    browser = p.chromium.launch(executable_path=r"C:\Program Files\Google\Chrome\Application\chrome.exe", headless=True)
    page = browser.new_page(viewport={"width": 1600, "height": 1100}, device_scale_factor=1)
    page.goto(args.url, wait_until="domcontentloaded", timeout=90000)
    page.wait_for_timeout(args.wait * 1000)
    if args.trace:
        for text in ("agent.run", "chat mock-llm-small", "chat mock-llm-large"):
            target = page.get_by_text(text, exact=True)
            if target.count():
                try:
                    target.first.click(timeout=2000)
                except Exception:
                    pass
    page.screenshot(path=args.output, full_page=True)
    print(page.title(), args.output)
    browser.close()
