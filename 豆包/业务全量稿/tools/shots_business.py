# -*- coding: utf-8 -*-
"""全量稿截图 + 模块总览拼图"""
import asyncio
from pathlib import Path
from playwright.async_api import async_playwright

BASE = Path(r"C:\Users\kunlunmeta\my-first-project\豆包\业务全量稿")
SHOTS = BASE / "shots"
SHOTS.mkdir(exist_ok=True)

PAGES = [
    "home", "period", "period-record", "period-feelings", "period-history", "period-prediction",
    "weight", "weight-record", "weight-detail", "weight-trend",
    "skin", "skin-capture", "skin-result", "skin-history", "skin-compare",
    "me", "settings", "privacy", "about", "login", "register",
]


async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(channel="msedge", headless=True)
        page = await browser.new_page(viewport={"width": 390, "height": 900}, device_scale_factor=2)
        for name in PAGES:
            url = (BASE / (name + ".html")).as_uri()
            await page.goto(url, wait_until="load")
            await page.wait_for_timeout(260)
            el = page.locator(".screen")
            await el.screenshot(path=str(SHOTS / (name + ".png")))
            h = await el.evaluate("e => e.getBoundingClientRect().height")
            print(name, int(h))
        await browser.close()

asyncio.run(main())
print("shots done")
