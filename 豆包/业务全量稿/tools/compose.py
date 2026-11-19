# -*- coding: utf-8 -*-
"""拼模块总览图（整页缩放，不裁切）"""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

BASE = Path(r"C:\Users\kunlunmeta\my-first-project\豆包\业务全量稿")
SHOTS = BASE / "shots"
FONT = r"C:\Windows\Fonts\msyh.ttc"
FONT_B = r"C:\Windows\Fonts\msyhbd.ttc"

PAGES = [
    ("home", "首页 · 今天", "一级"),
    ("period", "经期", "一级"),
    ("period-record", "记录经期 · 半屏", "二级"),
    ("period-feelings", "记录感受 · 半屏", "二级"),
    ("period-history", "历史回顾", "二级"),
    ("period-prediction", "预测说明", "二级"),
    ("weight", "体重", "一级"),
    ("weight-record", "记体重 · 半屏", "二级"),
    ("weight-detail", "记录明细", "二级"),
    ("weight-trend", "趋势详情", "二级"),
    ("skin", "皮肤", "一级"),
    ("skin-capture", "拍照分析", "二级"),
    ("skin-result", "分析结果", "二级"),
    ("skin-history", "历史观察", "二级"),
    ("skin-compare", "两次对比", "二级"),
    ("me", "我的", "一级"),
    ("settings", "设置", "二级"),
    ("privacy", "数据与隐私", "二级"),
    ("about", "关于她记", "二级"),
    ("login", "登录", "二级"),
    ("register", "注册", "二级"),
]


def font(size, bold=False):
    return ImageFont.truetype(FONT_B if bold else FONT, size)


def fit(path, w, h):
    im = Image.open(path).convert("RGB")
    scale = min(w / im.width, h / im.height)
    im = im.resize((int(im.width * scale), int(im.height * scale)), Image.LANCZOS)
    canvas = Image.new("RGB", (w, h), "#FFF8F4")
    canvas.paste(im, ((w - im.width) // 2, 0))
    return canvas


def sheet(items, cols, out, title, width=390):
    pad, label_h, header_h = 18, 54, 76
    img_h = int(width * 844 / 390)
    rows = (len(items) + cols - 1) // cols
    W = pad + cols * (width + pad)
    H = header_h + rows * (img_h + label_h + pad) + pad
    c = Image.new("RGB", (W, H), "#FDF4EF")
    d = ImageDraw.Draw(c)
    d.text((pad + 6, 22), title, font=font(24, True), fill="#5A3A42")
    for i, (name, label) in enumerate(items):
        r, col = divmod(i, cols)
        x = pad + col * (width + pad)
        y = header_h + r * (img_h + label_h + pad)
        c.paste(fit(SHOTS / (name + ".png"), width, img_h), (x, y))
        d.rectangle([x, y, x + width - 1, y + img_h - 1], outline="#EBD6D3", width=1)
        d.text((x + 4, y + img_h + 10), label, font=font(13, True), fill="#5A3A42")
    c.save(out)
    print(out.name, c.size)


def overview():
    cols, width, pad = 6, 310, 16
    img_h = int(width * 844 / 390)
    label_h, header_h = 44, 96
    rows = (len(PAGES) + cols - 1) // cols
    W = pad + cols * (width + pad)
    H = header_h + rows * (img_h + label_h + pad) + pad
    c = Image.new("RGB", (W, H), "#FDF4EF")
    d = ImageDraw.Draw(c)
    d.text((pad + 8, 24), "她记 HerLog · 业务全量稿", font=font(30, True), fill="#5A3A42")
    d.text((pad + 8, 64), "5 个一级页 + 16 个二级页 / 蜜桃奶油 · 素材版", font=font(15), fill="#8A6B72")
    for i, (name, label, level) in enumerate(PAGES):
        r, col = divmod(i, cols)
        x = pad + col * (width + pad)
        y = header_h + r * (img_h + label_h + pad)
        c.paste(fit(SHOTS / (name + ".png"), width, img_h), (x, y))
        d.rectangle([x, y, x + width - 1, y + img_h - 1], outline="#EBD6D3", width=1)
        color = "#C0566B" if level == "一级" else "#8A7A86"
        d.text((x + 4, y + img_h + 8), label, font=font(12, True), fill="#4E333A")
        d.text((x + width - 34, y + img_h + 9), level, font=font(10), fill=color)
    c.save(SHOTS / "overview.png")
    print("overview", c.size)


sheet([("period", "经期 · 一级页"), ("period-record", "记录经期 · 半屏"), ("period-feelings", "记录感受 · 半屏"), ("period-history", "历史回顾")],
      2, SHOTS / "module-period.png", "经期 · 页面组（一级 + 3 个二级）")
sheet([("weight", "体重 · 一级页"), ("weight-record", "记体重 · 半屏"), ("weight-detail", "记录明细")],
      3, SHOTS / "module-weight.png", "体重 · 页面组（一级 + 2 个二级）", width=370)
sheet([("skin", "皮肤 · 一级页"), ("skin-capture", "拍照分析"), ("skin-result", "分析结果"), ("skin-history", "历史观察")],
      2, SHOTS / "module-skin.png", "皮肤 · 页面组（一级 + 3 个二级）")
sheet([("settings", "设置"), ("privacy", "数据与隐私"), ("about", "关于她记"), ("login", "登录"), ("register", "注册")],
      3, SHOTS / "module-account.png", "我的与账号 · 页面组（5 个二级）", width=370)
overview()
