"""
ZeroTouch SRE — Screenshot Capture Script
Takes real screenshots of:
1. Local server (http://127.0.0.1:8080) — landing, scenario, docs
2. After firing a live alert — incident workbench result
3. Cloud Run (the actual deployed service)
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

LOCAL = "http://127.0.0.1:8080"
CLOUD = "https://zerotouch-sre-971465910048.us-central1.run.app"
OUT = Path(r"C:\Users\prati\Downloads\Projects\ZeroTouch SRE\assets\screenshots")
OUT.mkdir(parents=True, exist_ok=True)

def screenshot(page, path: str, name: str, wait_ms: int = 2000):
    full = OUT / path
    try:
        page.screenshot(path=str(full), full_page=True)
        print(f"  [OK] {name} → {path}")
    except Exception as exc:
        print(f"  [FAIL] {name}: {exc}")

def run():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(viewport={"width": 1440, "height": 900})

        print("\n=== LOCAL SERVER SCREENSHOTS ===")
        page = ctx.new_page()

        # 1. Landing page
        print("Capturing landing page...")
        page.goto(LOCAL, wait_until="networkidle", timeout=15000)
        page.wait_for_timeout(2000)
        screenshot(page, "local-01-landing.png", "Landing page")

        # 2. Click "Run checkout incident" if present
        print("Triggering checkout incident...")
        try:
            btn = page.locator("button:has-text('Run'), button:has-text('checkout'), #run-btn, [data-action='run']").first
            if btn.is_visible():
                btn.click()
                page.wait_for_timeout(8000)
                screenshot(page, "local-02-incident-result.png", "Incident result after run")
            else:
                # Try to find any prominent action button
                page.wait_for_timeout(1000)
                screenshot(page, "local-02-landing-full.png", "Landing full")
        except Exception as exc:
            print(f"  [WARN] Button click: {exc}")
            screenshot(page, "local-02-landing-full.png", "Landing fallback")

        # 3. Scenario page
        print("Capturing scenario page...")
        page.goto(f"{LOCAL}/scenario", wait_until="networkidle", timeout=30000)
        page.wait_for_timeout(3000)
        screenshot(page, "local-03-scenario.png", "Scenario page")

        # 4. Docs
        print("Capturing API docs...")
        page.goto(f"{LOCAL}/docs", wait_until="networkidle", timeout=15000)
        page.wait_for_timeout(2000)
        screenshot(page, "local-04-docs.png", "API docs")

        # 5. scenario.json
        print("Capturing scenario JSON...")
        page.goto(f"{LOCAL}/scenario.json", wait_until="networkidle", timeout=30000)
        page.wait_for_timeout(2000)
        screenshot(page, "local-05-scenario-json.png", "Scenario JSON")

        print("\n=== CLOUD RUN SCREENSHOTS ===")
        page2 = ctx.new_page()

        # 6. Cloud Run landing
        print("Capturing Cloud Run landing...")
        try:
            page2.goto(CLOUD, wait_until="networkidle", timeout=30000)
            page2.wait_for_timeout(3000)
            screenshot(page2, "cloud-01-landing.png", "Cloud Run landing")

            # 7. Trigger incident on Cloud Run
            print("Triggering incident on Cloud Run...")
            try:
                btn2 = page2.locator("button:has-text('Run'), button:has-text('checkout'), button:has-text('Incident')").first
                if btn2.is_visible():
                    btn2.click()
                    page2.wait_for_timeout(12000)
                    screenshot(page2, "cloud-02-incident-result.png", "Cloud Run incident result")
            except Exception as e:
                print(f"  [WARN] Cloud button: {e}")

            # 8. Cloud Run scenario page
            page2.goto(f"{CLOUD}/scenario", wait_until="networkidle", timeout=45000)
            page2.wait_for_timeout(4000)
            screenshot(page2, "cloud-03-scenario.png", "Cloud Run scenario")

        except PlaywrightTimeout:
            print("  [WARN] Cloud Run timed out — skipping cloud screenshots")
        except Exception as exc:
            print(f"  [WARN] Cloud Run: {exc}")

        browser.close()

    print(f"\nScreenshots saved to: {OUT}")
    saved = list(OUT.glob("*.png"))
    print(f"Total screenshots: {len(saved)}")
    for f in sorted(saved):
        print(f"  {f.name} ({f.stat().st_size // 1024}KB)")

if __name__ == "__main__":
    run()
