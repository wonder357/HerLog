# -*- coding: utf-8 -*-
import asyncio
from pathlib import Path
from playwright.async_api import async_playwright

BASE = Path(r"C:\Users\kunlunmeta\my-first-project\豆包\业务全量稿")


async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(channel="msedge", headless=True)
        pg = await b.new_page(viewport={"width": 390, "height": 900}, device_scale_factor=2)
        await pg.goto((BASE / "skin.html").as_uri(), wait_until="load")
        await pg.wait_for_timeout(300)
        await pg.locator(".screen").screenshot(path=str(BASE / "shots" / "skin.png"))
        h = await pg.locator(".screen").evaluate("e => e.getBoundingClientRect().height")
        print("skin height", int(h))
        await b.close()

asyncio.run(main())
