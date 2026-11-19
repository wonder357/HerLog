# -*- coding: utf-8 -*-
"""四套主题的截图：每套五页 + 每套画廊 + 顶部对比页"""
from pathlib import Path
from PIL import Image
from playwright.sync_api import sync_playwright

OUT = Path(r"C:\Users\kunlunmeta\my-first-project\豆包\风格方案")
SHOTS = OUT / "shots"
SHOTS.mkdir(exist_ok=True)

THEMES = {"peach": "01-蜜桃奶油", "dusk": "02-暮光玫瑰", "apricot": "03-杏桃霞光", "mauve": "04-雾紫珍珠"}
PAGES = ["home", "period", "weight", "skin", "me"]


def crop_bottom(path, css_bottom):
    im = Image.open(path)
    im.crop((0, 0, im.size[0], min(im.size[1], int(css_bottom * 2)))).save(path)


with sync_playwright() as p:
    browser = p.chromium.launch(channel="msedge", headless=True)
    ctx = browser.new_context(viewport={"width": 390, "height": 900}, device_scale_factor=2)

    for key, folder in THEMES.items():
        d = OUT / folder
        (SHOTS / key).mkdir(parents=True, exist_ok=True)
        for name in PAGES:
            page = ctx.new_page()
            page.goto((d / (name + ".html")).as_uri())
            page.wait_for_timeout(400)
            el = page.locator(".screen")
            h = el.evaluate("e => Math.round(e.getBoundingClientRect().height)")
            el.screenshot(path=str(SHOTS / key / (name + ".png")))
            print(key, name, h)
            page.close()

        page = ctx.new_page()
        page.set_viewport_size({"width": 1440, "height": 1980})
        page.goto((d / "index.html").as_uri())
        page.wait_for_timeout(1300)
        bottom = page.evaluate(
            "() => Math.max(...[...document.querySelectorAll('.frame')]"
            ".map(f => f.getBoundingClientRect().bottom + window.scrollY))"
        )
        shot = SHOTS / key / "gallery.png"
        page.screenshot(path=str(shot))
        crop_bottom(shot, bottom + 40)
        print(key, "gallery", bottom)
        page.close()

    page = ctx.new_page()
    page.set_viewport_size({"width": 1920, "height": 1300})
    page.goto((OUT / "index.html").as_uri())
    page.wait_for_timeout(1500)
    h = page.evaluate("() => document.body.scrollHeight")
    shot = SHOTS / "overview.png"
    page.screenshot(path=str(shot))
    crop_bottom(shot, h + 24)
    print("overview", h)
    browser.close()
