"""Screenshots of the app for the slides and README: python docs/shots.py
(APP_URL defaults to the API on localhost:8010; a static server on web/ works too, e.g. APP_URL=http://localhost:8020/)."""
import json
import os
from pathlib import Path

from playwright.sync_api import sync_playwright

OUT = Path(__file__).parent / "shots"
OUT.mkdir(exist_ok=True)
URL = os.environ.get("APP_URL", "http://localhost:8010/")
MOCK = json.loads((Path(__file__).parent.parent / "web" / "mock_response.json").read_text(encoding="utf-8"))
MOCK.update({"model_label": "Fine-tuned · ours", "saved_id": "demo"})
# same labels as MODEL_LABELS in api/main.py, so the before/after switch shows even without the API
UNLOCK = """document.getElementById('panel').classList.remove('locked'); document.getElementById('gate').hidden = true;
const box = document.getElementById('modelBtns'); box.replaceChildren(...[['XLS-R 300M · before fine-tuning', false], ['Fine-tuned · ours', true]]
  .map(([t, on]) => { const b = document.createElement('button'); b.textContent = t; b.setAttribute('aria-pressed', on); return b; }));
document.getElementById('models').hidden = false;"""
# freeze the background loop on the same frame every run (2.3 s: both bursts high, no glitch)
FREEZE = """async () => { const v = document.getElementById('bgVideo');
  if (!v.getAttribute('src')) v.src = innerWidth <= 900 ? 'bg/waveform-loop-720.mp4' : 'bg/waveform-loop.mp4';
  await v.play().catch(() => {}); v.pause(); v.currentTime = 2.3;
  await new Promise((r) => v.addEventListener('seeked', r, { once: true })); v.classList.add('ready'); }"""
TO_TOOL = "document.getElementById('check').scrollIntoView({ behavior: 'instant', block: 'start' });"


def open_page(browser, width, height, scale):
    pg = browser.new_page(viewport={"width": width, "height": height}, device_scale_factor=scale)
    pg.goto(URL, wait_until="networkidle")
    pg.evaluate(FREEZE)
    pg.wait_for_timeout(2800)  # entrance animation + video fade-in
    return pg


with sync_playwright() as p:
    b = p.chromium.launch(channel="chrome")
    pg = open_page(b, 1440, 900, 1.5)
    pg.screenshot(path=str(OUT / "1_home.png"))

    tool = open_page(b, 1440, 1200, 1.5)
    tool.evaluate(UNLOCK + f"render({json.dumps(MOCK)}, false);" + TO_TOOL)
    tool.wait_for_timeout(1500)
    tool.screenshot(path=str(OUT / "2_result.png"))
    tool.evaluate("setLang('ar');" + TO_TOOL)
    tool.wait_for_timeout(1000)
    tool.screenshot(path=str(OUT / "3_result_ar.png"))
    tool.evaluate("setLang('en'); showView('dash')")
    tool.wait_for_timeout(1500)
    tool.screenshot(path=str(OUT / "4_dashboard.png"), full_page=True)

    mob = open_page(b, 390, 844, 2)
    mob.screenshot(path=str(OUT / "5_mobile.png"))
    mob.evaluate(UNLOCK + f"render({json.dumps(MOCK)}, false); setLang('ar');"
                 "document.getElementById('result').scrollIntoView({ behavior: 'instant', block: 'start' });")
    mob.wait_for_timeout(1200)
    mob.screenshot(path=str(OUT / "6_mobile_ar.png"))
    b.close()
print("ok")
