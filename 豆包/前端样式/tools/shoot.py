"""她记 · 五页样式截图脚本（Playwright + 本机 Edge，无需下载 Chromium）

用法：python tools/shoot.py
输出：shots/home.png、period.png、weight.png、skin.png、me.png、gallery.png（@2x）
"""
from pathlib import Path
from PIL import Image
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "shots"
OUT.mkdir(exist_ok=True)
PAGES = ["home", "period", "weight", "skin", "me"]

with sync_playwright() as p:
    browser = p.chromium.launch(channel="msedge", headless=True)
    ctx = browser.new_context(viewport={"width": 390, "height": 900}, device_scale_factor=2)

    for name in PAGES:
        page = ctx.new_page()
        page.goto((ROOT / "pages" / (name + ".html")).as_uri())
        page.wait_for_timeout(400)
        el = page.locator(".screen")
        h = el.evaluate("e => Math.round(e.getBoundingClientRect().height)")
        el.screenshot(path=str(OUT / (name + ".png")))
        print(name, "height", h)
        page.close()

    page = ctx.new_page()
    page.set_viewport_size({"width": 1440, "height": 1980})
    page.goto((ROOT / "index.html").as_uri())
    page.wait_for_timeout(1500)
    bottom = page.evaluate(
        "() => Math.max(...[...document.querySelectorAll('.frame')]"
        ".map(f => f.getBoundingClientRect().bottom + window.scrollY))"
    )
    shot = OUT / "gallery.png"
    page.screenshot(path=str(shot))
    im = Image.open(shot)
    im.crop((0, 0, im.size[0], min(im.size[1], int((bottom + 40) * 2)))).save(shot)
    print("gallery done")
    browser.close()
