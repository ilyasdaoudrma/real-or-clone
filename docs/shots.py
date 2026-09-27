"""Screenshots of the app for the slides: python docs/shots.py (app running on localhost:8010)."""
import json
import os
from pathlib import Path

from playwright.sync_api import sync_playwright

OUT = Path(__file__).parent / "shots"
OUT.mkdir(exist_ok=True)
MOCK = json.loads((Path(__file__).parent.parent / "web" / "mock_response.json").read_text(encoding="utf-8"))
MOCK.update({"model_label": "Fine-tuned · ours", "saved_id": "demo"})
UNLOCK = "document.getElementById('panel').classList.remove('locked'); document.getElementById('gate').hidden = true;"

with sync_playwright() as p:
    b = p.chromium.launch(channel="chrome")
    pg = b.new_page(viewport={"width": 1440, "height": 900}, device_scale_factor=1.5)
    pg.goto(os.environ.get("APP_URL", "http://localhost:8010/"), wait_until="networkidle")
    pg.wait_for_timeout(2500)
    pg.screenshot(path=str(OUT / "1_home.png"))
    pg.evaluate(UNLOCK + f"render({json.dumps(MOCK)}, false); window.scrollTo(0, 0);")
    pg.wait_for_timeout(1500)
    pg.screenshot(path=str(OUT / "2_result.png"), full_page=True)
    pg.evaluate("setLang('ar')")
    pg.wait_for_timeout(800)
    pg.screenshot(path=str(OUT / "3_result_ar.png"), full_page=True)
    pg.evaluate("setLang('en'); showView('dash')")
    pg.wait_for_timeout(1500)
    pg.screenshot(path=str(OUT / "4_dashboard.png"), full_page=True)
    mob = b.new_page(viewport={"width": 390, "height": 844}, device_scale_factor=2)
    mob.goto(os.environ.get("APP_URL", "http://localhost:8010/"), wait_until="networkidle")
    mob.wait_for_timeout(2000)
    mob.evaluate(UNLOCK + f"render({json.dumps(MOCK)}, false); document.getElementById('result').scrollIntoView();")
    mob.wait_for_timeout(1200)
    mob.screenshot(path=str(OUT / "5_mobile.png"))
    b.close()
print("ok")
