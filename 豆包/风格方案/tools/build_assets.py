# -*- coding: utf-8 -*-
"""蜜桃奶油·素材版：在 01-蜜桃奶油 基础上叠加插画素材（头像 + 页首点缀）"""
import shutil
from pathlib import Path
from PIL import Image

ROOT = Path(r"C:\Users\kunlunmeta\my-first-project\豆包\风格方案")
BASE = ROOT / "01-蜜桃奶油"
OUT = ROOT / "01b-蜜桃奶油·素材版"
SRC = Path(r"C:\Users\kunlunmeta\my-first-project\assets\背景素材")

PAGES = ["home", "period", "weight", "skin", "me"]

ASSET_CSS = """@charset "UTF-8";
/* ============================================================
   素材版：只加插画点缀，不改配色、不改结构、不改文案
   ============================================================ */

.hero .hero-art{
  position:absolute; z-index:0; pointer-events:none;
  background-repeat:no-repeat;
}

/* 首页：整块页首铺金粉侧影，左浅右深，正文区保持干净 */
.p-home .hero-art{
  inset:0; width:auto; height:auto;
  background-image:url("assets/portrait.png");
  background-size:cover; background-position:74% 22%;
  opacity:.36; mix-blend-mode:multiply;
  -webkit-mask-image:linear-gradient(92deg, rgba(0,0,0,0) 34%, #000 92%),
                     linear-gradient(180deg, #000 64%, rgba(0,0,0,0) 100%);
  mask-image:linear-gradient(92deg, rgba(0,0,0,0) 34%, #000 92%),
              linear-gradient(180deg, #000 64%, rgba(0,0,0,0) 100%);
  -webkit-mask-composite:source-in;
  mask-composite:intersect;
}

/* 经期：不叠素材，留白给日历 */

/* 皮肤：花中侧影（右上小面积点缀） */
.p-skin .hero-art{
  right:-6px; top:-18px; width:126px; height:126px;
  background-image:url("assets/bloom.png");
  background-size:contain; background-position:right top;
  opacity:.28;
  -webkit-mask-image:linear-gradient(205deg, #000 40%, rgba(0,0,0,0) 86%);
  mask-image:linear-gradient(205deg, #000 40%, rgba(0,0,0,0) 86%);
}

/* 我的：金粉侧影（右侧半身，向文字方向渐隐） */
.p-me .hero-art{
  right:-34px; top:-46px; width:272px; height:430px;
  background-image:url("assets/portrait.png");
  background-size:cover; background-position:62% 12%;
  opacity:.50;
  -webkit-mask-image:linear-gradient(90deg, rgba(0,0,0,0) 6%, #000 46%),
                     linear-gradient(180deg, #000 62%, rgba(0,0,0,0) 96%);
  mask-image:linear-gradient(90deg, rgba(0,0,0,0) 6%, #000 46%),
              linear-gradient(180deg, #000 62%, rgba(0,0,0,0) 96%);
  -webkit-mask-composite:source-in;
  mask-composite:intersect;
}

/* 头像：插画裁成圆形，保持白描边与投影 */
.avatar-photo{
  width:64px; height:64px; border-radius:50%;
  object-fit:cover; object-position:50% 22%;
  background:#FFFFFF;
  border:2px solid rgba(255,255,255,.92);
  box-shadow:0 10px 22px -10px rgba(156,59,80,.50), inset 0 0 0 1px rgba(244,229,225,.9);
}
"""


def prep_assets():
    d = OUT / "assets"
    d.mkdir(parents=True, exist_ok=True)

    def save(src_name, dst, width=None, crop=None):
        im = Image.open(SRC / src_name).convert("RGBA")
        if crop:
            im = im.crop(crop)
        if width:
            r = width / im.width
            im = im.resize((width, round(im.height * r)), Image.LANCZOS)
        im.save(d / dst, optimize=True)
        print(dst, im.size, (d / dst).stat().st_size // 1024, "KB")

    # 头像：戴发箍的女孩，裁到头肩
    save("huaban-6736632886.webp", "avatar.png", 256, (140, 18, 618, 496))
    # 页首素材
    save("huaban-7048921316.webp", "hat.png", 560)
    save("huaban-5352683748.webp", "crown.png", 480)
    save("huaban-6551828446.webp", "bloom.png", 560)
    save("huaban-7183705238.webp", "portrait.png", 720)


def build():
    if OUT.exists():
        shutil.rmtree(OUT)
    shutil.copytree(BASE, OUT)

    for name in PAGES:
        p = OUT / (name + ".html")
        s = p.read_text(encoding="utf-8")
        s = s.replace("<body>", f'<body class="p-{name}">')
        s = s.replace("</head>", '<link rel="stylesheet" href="assets.css">\n</head>')
        s = s.replace('<header class="hero">', '<header class="hero"><div class="hero-art"></div>')
        if name == "me":
            s = s.replace('<div class="avatar">语</div>',
                          '<img class="avatar avatar-photo" src="assets/avatar.png" alt="林小语">')
        p.write_text(s, encoding="utf-8")

    (OUT / "assets.css").write_text(ASSET_CSS, encoding="utf-8")

    idx = OUT / "index.html"
    s = idx.read_text(encoding="utf-8")
    s = s.replace("<h1>蜜桃奶油<span>Peach Cream</span></h1>",
                  "<h1>蜜桃奶油 · 素材版<span>Peach Cream · With Assets</span></h1>")
    s = s.replace("<p>奶油橘粉渐变，日常温柔，长时间看不刺激。</p>",
                  "<p>保留蜜桃奶油的配色与材质，只在页首与头像加入插画素材；结构、文案与间距完全不变。</p>")
    s = s.replace('<link rel="stylesheet" href="theme.css">',
                  '<link rel="stylesheet" href="theme.css">\n<link rel="stylesheet" href="assets.css">')
    idx.write_text(s, encoding="utf-8")
    print("built", OUT.name)


build()
prep_assets()
