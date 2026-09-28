"""Render the README banner and the GitHub social preview from banner.html: python docs/assets/render_banner.py"""
from pathlib import Path

from playwright.sync_api import sync_playwright

D = Path(__file__).parent

with sync_playwright() as p:
    b = p.chromium.launch(channel="chrome")
    for name, w, h in (("banner.jpg", 1280, 480), ("social-preview.jpg", 1280, 640)):
        pg = b.new_page(viewport={"width": w, "height": h}, device_scale_factor=2)
        pg.goto((D / "banner.html").as_uri(), wait_until="networkidle")
        pg.evaluate("document.fonts.ready")
        pg.wait_for_timeout(300)
        pg.screenshot(path=str(D / name), type="jpeg", quality=90)
    b.close()
print("ok")
