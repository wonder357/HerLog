# -*- coding: utf-8 -*-
import re
import os
from pathlib import Path

os.chdir(Path(__file__).resolve().parent.parent)
files = sorted(Path(".").glob("*.html"))
missing_html = []
missing_assets = []
for f in files:
    s = f.read_text(encoding="utf-8")
    for h in re.findall(r'href="([^"]+\.html)"', s):
        if not Path(h).exists():
            missing_html.append((f.name, h))
    for src in re.findall(r'src="(assets/[^"]+|icons/[^"]+)"', s):
        if not Path(src).exists():
            missing_assets.append((f.name, src))

print("missing html:", missing_html)
print("missing assets:", missing_assets)
print("pages:", len(files))
