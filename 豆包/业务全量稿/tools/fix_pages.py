# -*- coding: utf-8 -*-
from pathlib import Path

OUT = Path(r"C:\Users\kunlunmeta\my-first-project\豆包\业务全量稿")


def edit(name, pairs):
    p = OUT / (name + ".html")
    s = p.read_text(encoding="utf-8")
    for a, b in pairs:
        if a not in s:
            print("  MISS:", name, a[:40])
        s = s.replace(a, b)
    p.write_text(s, encoding="utf-8")
    print("fixed", name)


edit("period-history", [
    ("10 月 23 日 – 10 月 27 日", "10 月 23 日 – 27 日"),
    ("9 月 29 日 – 10 月 3 日", "9 月 29 日 – 10 月 3 日"),
])

edit("skin-capture", [
    ('<div class="meta" style="margin-top:8px">第 1 步，共 3 步 · 选择部位 → 拍照 → 确认发送</div>',
     '<div class="meta" style="margin-top:8px">第 1 步，共 3 步 · 先选部位，再拍一张清楚的照片</div>'),
])

edit("skin-history", [
    ('<span class="meta">共 6 次 · 面部左颊 4 次</span>',
     '<span class="meta">面部左颊 4 次 · 按时间倒序</span>'),
])

edit("weight-record", [
    ('<button class="key fn">⌫</button>', '<button class="key fn">退格</button>'),
])

edit("weight-detail", [
])
p = OUT / "weight-detail.html"
s = p.read_text(encoding="utf-8")
s = s.replace('<div class="r"><a class="link" href="#">编辑</a></div>',
              '<div class="r"><a class="link" href="#">编辑</a><span style="color:#A2939B">删除</span></div>')
p.write_text(s, encoding="utf-8")
print("fixed weight-detail")

for name in ["login", "register"]:
    p = OUT / (name + ".html")
    s = p.read_text(encoding="utf-8")
    if name == "register":
        s = s.replace('<body class="auth">', '<body class="auth register">')
    if 'class="auth-art"' not in s:
        s = s.replace("</main>\n</div>", '</main>\n  <img class="auth-art" src="assets/bloom.png" alt="">\n</div>')
    p.write_text(s, encoding="utf-8")
    print("fixed", name)
