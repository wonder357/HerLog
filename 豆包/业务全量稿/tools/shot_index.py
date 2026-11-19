# -*- coding: utf-8 -*-
import asyncio
from pathlib import Path
from playwright.async_api import async_playwright

BASE = Path(r"C:\Users\kunlunmeta\my-first-project\豆包\业务全量稿")


async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(channel="msedge", headless=True)
        pg = await b.new_page(viewport={"width": 1440, "height": 1400}, device_scale_factor=1)
        await pg.goto((BASE / "index.html").as_uri(), wait_until="load")
        await pg.wait_for_timeout(400)
        await pg.screenshot(path=str(BASE / "shots" / "index-top.png"))
        h = await pg.evaluate("document.body.scrollHeight")
        print("height", h)
        await b.close()

asyncio.run(main())
