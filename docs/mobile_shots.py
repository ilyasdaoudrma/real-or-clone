"""Mobile screenshots of every view: python docs/mobile_shots.py (app on localhost:8010)."""
import json
from pathlib import Path

from playwright.sync_api import sync_playwright

OUT = Path(__file__).parent / "shots" / "mobile"
OUT.mkdir(parents=True, exist_ok=True)
MOCK = json.loads((Path(__file__).parent.parent / "web" / "mock_response.json").read_text(encoding="utf-8"))
MOCK.update({"model_label": "Fine-tuned · ours", "saved_id": "demo"})
UNLOCK = "document.getElementById('panel').classList.remove('locked'); document.getElementById('gate').hidden = true;"

with sync_playwright() as p:
    b = p.chromium.launch(channel="chrome")
    pg = b.new_page(viewport={"width": 390, "height": 844}, device_scale_factor=2, is_mobile=True, has_touch=True)
    pg.goto("http://localhost:8010/", wait_until="networkidle")
    pg.wait_for_timeout(2500)
    pg.screenshot(path=str(OUT / "a_gate.png"), full_page=True)
    pg.evaluate(UNLOCK + f"render({json.dumps(MOCK)}, false); window.scrollTo(0, 0);")
    pg.wait_for_timeout(1200)
    pg.screenshot(path=str(OUT / "b_result.png"), full_page=True)
    pg.evaluate("setLang('ar')")
    pg.wait_for_timeout(600)
    pg.screenshot(path=str(OUT / "c_result_ar.png"), full_page=True)
    pg.evaluate("setLang('en'); showView('dash')")
    pg.wait_for_timeout(1200)
    pg.screenshot(path=str(OUT / "d_dash.png"), full_page=True)
    over = pg.evaluate("document.documentElement.scrollWidth > innerWidth")
    print("horizontal overflow:", over)
    b.close()
