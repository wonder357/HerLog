# -*- coding: utf-8 -*-
from pathlib import Path
from PIL import Image
from playwright.sync_api import sync_playwright

OUT = Path(r"C:\Users\kunlunmeta\my-first-project\豆包\风格方案")
D = OUT / "01b-蜜桃奶油·素材版"
SHOTS = OUT / "shots" / "peach-assets"
SHOTS.mkdir(parents=True, exist_ok=True)
PAGES = ["home", "period", "weight", "skin", "me"]

with sync_playwright() as p:
    b = p.chromium.launch(channel="msedge", headless=True)
    ctx = b.new_context(viewport={"width": 390, "height": 900}, device_scale_factor=2)
    for name in PAGES:
        page = ctx.new_page()
        page.goto((D / (name + ".html")).as_uri())
        page.wait_for_timeout(400)
        el = page.locator(".screen")
        h = el.evaluate("e => Math.round(e.getBoundingClientRect().height)")
        el.screenshot(path=str(SHOTS / (name + ".png")))
        print(name, h)
        page.close()

    page = ctx.new_page()
    page.set_viewport_size({"width": 1440, "height": 1980})
    page.goto((D / "index.html").as_uri())
    page.wait_for_timeout(1200)
    bottom = page.evaluate(
        "() => Math.max(...[...document.querySelectorAll('.frame')]"
        ".map(f => f.getBoundingClientRect().bottom + window.scrollY))"
    )
    shot = SHOTS / "gallery.png"
    page.screenshot(path=str(shot))
    im = Image.open(shot)
    im.crop((0, 0, im.width, min(im.height, int((bottom + 40) * 2)))).save(shot)
    print("gallery", bottom)
    b.close()
