# -*- coding: utf-8 -*-
"""她记 · 业务全量稿生成器（蜜桃奶油素材版视觉）"""
import re
import shutil
from pathlib import Path

ROOT = Path(r"C:\Users\kunlunmeta\my-first-project\豆包")
SRC = ROOT / "风格方案" / "01b-蜜桃奶油·素材版"
OUT = ROOT / "业务全量稿"

BUSINESS_CSS = """@charset "UTF-8";
/* ============================================================
   业务全量稿 · 二级页与半屏表单
   沿用蜜桃奶油素材版的变量与材质，只补二级页组件
   ============================================================ */

/* ---------- 二级页页首 ---------- */
.sub-hero { padding: 16px var(--pad) 18px; }
.sub-bar { display: flex; align-items: center; gap: 10px; margin-bottom: 10px; }
.back {
  width: 40px; height: 40px; border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  background: rgba(255,255,255,.62);
  border: 1px solid rgba(244,229,225,.95);
  color: var(--ink); text-decoration: none;
  box-shadow: 0 8px 18px -12px rgba(156,59,80,.45);
  flex: 0 0 auto;
}
.sub-kicker { font-size: 11px; letter-spacing: 2px; color: var(--ink-2); }
.sub-title { margin: 0; font-size: 24px; line-height: 32px; font-weight: 600; letter-spacing: .5px; }
.sub-sub { margin-top: 4px; font-size: 13px; line-height: 20px; color: var(--ink-2); }
.sub-hero .chips { margin-top: 10px; }

/* ---------- 二级页正文 ---------- */
.sub-main { flex: 1 1 auto; padding-bottom: 30px; }
.sub-main .section:first-child { margin-top: 12px; }

/* ---------- 列表行 ---------- */
.lrow { display: flex; align-items: center; justify-content: space-between; gap: 10px; padding: 13px 0; border-bottom: 1px solid var(--card-line); }
.lrow:last-child { border-bottom: 0; padding-bottom: 2px; }
.lrow:first-child { padding-top: 2px; }
.lrow .t { font-size: 15px; font-weight: 500; }
.lrow .s { font-size: 12px; line-height: 18px; color: var(--ink-2); margin-top: 2px; }
.lrow .r { font-size: 13px; color: var(--ink-2); text-align: right; display: flex; align-items: center; gap: 6px; white-space: nowrap; }
.lrow .r .on { color: var(--berry); font-weight: 600; }

/* ---------- 周期列表 ---------- */
.cycle { display: flex; gap: 12px; padding: 14px 0; border-bottom: 1px solid var(--card-line); }
.cycle:first-child { padding-top: 2px; }
.cycle:last-child { border-bottom: 0; padding-bottom: 2px; }
.cycle .d { width: 58px; flex: 0 0 auto; }
.cycle .dd { font-size: 19px; line-height: 24px; font-weight: 600; font-variant-numeric: tabular-nums; }
.cycle .dm { font-size: 11px; color: var(--ink-2); margin-top: 1px; }
.cycle .body { flex: 1; min-width: 0; }
.cycle .t { font-size: 14px; font-weight: 500; display: flex; align-items: center; gap: 6px; flex-wrap: wrap; }
.cycle .s { font-size: 12px; line-height: 18px; color: var(--ink-2); margin-top: 3px; }
.cycle .r { font-size: 12px; color: var(--ink-2); text-align: right; line-height: 19px; }

/* ---------- 数据行 / 大数字 ---------- */
.drow { display: flex; align-items: center; justify-content: space-between; padding: 12px 0; border-bottom: 1px dashed var(--card-line); }
.drow:last-child { border-bottom: 0; padding-bottom: 0; }
.drow .lab { font-size: 13px; color: var(--ink-2); }
.drow .val { font-size: 15px; font-weight: 600; font-variant-numeric: tabular-nums; }
.pred {
  font-size: 34px; line-height: 44px; font-weight: 600; letter-spacing: -.5px;
  font-variant-numeric: tabular-nums;
}
.stat3 { display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px; margin-top: 12px; }
.stat3 .it { background: var(--chip-grad, #FFF8F6); border: 1px solid var(--card-line); border-radius: 10px; padding: 10px 8px; text-align: center; }
.stat3 .n { font-size: 18px; font-weight: 600; font-variant-numeric: tabular-nums; }
.stat3 .k { font-size: 11px; color: var(--ink-2); margin-top: 2px; }

/* ---------- 说明块 ---------- */
.hintbox {
  margin-top: 12px; padding: 10px 12px; border-radius: 10px;
  background: linear-gradient(135deg, rgba(251,226,230,.75), rgba(255,240,242,.9));
  border: 1px solid rgba(240,205,214,.8);
  font-size: 13px; line-height: 20px; color: #7A4A55;
}
.rule { display: flex; gap: 8px; padding: 8px 0; font-size: 13px; line-height: 20px; color: var(--ink-2); }
.rule b { color: var(--ink); font-weight: 600; }
.rule .n { width: 18px; height: 18px; border-radius: 50%; background: var(--berry-soft); color: var(--berry-deep); font-size: 11px; display: flex; align-items: center; justify-content: center; flex: 0 0 auto; margin-top: 1px; }

/* ---------- 表单 ---------- */
.slabel { font-size: 12px; color: var(--ink-2); margin-top: 14px; }
.chips { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 8px; }
.chips .chip { height: 30px; }
.ta {
  margin-top: 8px; min-height: 64px; border-radius: 10px;
  border: 1px solid var(--card-line); background: var(--input-grad, #FFFCFA);
  padding: 10px 12px; font-size: 14px; line-height: 22px; color: var(--ink-2);
}

/* ---------- 半屏表单 ---------- */
.screen.fixed { height: 844px; min-height: 844px; overflow: hidden; }
.scrim { position: absolute; inset: 0; z-index: 20; background: rgba(59,42,45,.30); backdrop-filter: blur(2px); }
.sheet {
  position: absolute; left: 0; right: 0; bottom: 0; z-index: 21;
  display: flex; flex-direction: column;
  max-height: 93%;
  padding: 8px 16px 22px;
  border-radius: 24px 24px 0 0;
  background: linear-gradient(180deg, #FFFDFC 0%, #FFF7F5 100%);
  box-shadow: 0 -24px 60px rgba(59,42,45,.30);
  border-top: 1px solid rgba(255,255,255,.9);
}
.grab { width: 38px; height: 4px; border-radius: 2px; background: #EBD9DD; margin: 2px auto 8px; flex: 0 0 auto; }
.sheet-head { display: flex; align-items: flex-start; justify-content: space-between; gap: 8px; }
.sheet-title { font-size: 18px; line-height: 24px; font-weight: 600; }
.sheet-sub { font-size: 12px; line-height: 18px; color: var(--ink-2); margin-top: 2px; }
.sheet-x {
  width: 34px; height: 34px; border-radius: 50%; border: 1px solid var(--line);
  background: #FFFFFF; color: var(--ink-2); font-size: 15px; line-height: 1;
  display: flex; align-items: center; justify-content: center; flex: 0 0 auto;
}
.sheet-body { overflow: auto; padding-top: 10px; }
.sheet-foot { margin-top: 12px; flex: 0 0 auto; }
.danger-link { display: inline-block; margin-top: 14px; font-size: 12px; color: var(--error); text-decoration: none; }

/* ---------- 体重键盘 ---------- */
.wval { display: flex; align-items: flex-end; justify-content: center; gap: 6px; padding: 2px 0 4px; }
.wval .n { font-size: 40px; line-height: 46px; font-weight: 600; letter-spacing: -.5px; font-variant-numeric: tabular-nums; }
.wval .u { font-size: 15px; color: var(--ink-2); padding-bottom: 6px; }
.keypad { display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px; margin-top: 10px; }
.key {
  height: 44px; border-radius: 12px; border: 1px solid var(--card-line);
  background: linear-gradient(180deg, #FFFFFF, #FFF8F5);
  font-size: 18px; font-weight: 600; color: var(--ink);
  display: flex; align-items: center; justify-content: center;
}
.key.fn { font-size: 13px; font-weight: 500; color: var(--ink-2); }

/* ---------- 照片占位 ---------- */
.mock {
  position: relative; border-radius: 12px; overflow: hidden;
  background: radial-gradient(120% 120% at 30% 20%, #F8DED4 0%, #EFCBBF 55%, #E6C2BE 100%);
  display: flex; align-items: center; justify-content: center;
}
.mock .lbl { position: absolute; left: 8px; bottom: 6px; font-size: 11px; color: rgba(84,52,44,.85); background: rgba(255,255,255,.74); padding: 1px 6px; border-radius: 4px; }
.mock .big { font-size: 12px; color: rgba(122,78,88,.55); letter-spacing: 1px; }
.mock.camera { height: 196px; border: 1.5px dashed #E7CDD6; background: linear-gradient(160deg, #FFF8F4, #FFF1EE); }
.mock.photo16 { height: 214px; }
.mock.thumb { width: 74px; height: 74px; flex: 0 0 auto; }
.cmp { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
.cmp .mock { height: 168px; }

/* ---------- 设置 ---------- */
.rowlink + .rowlink { margin-top: 8px; }
.set-row { display: flex; align-items: center; justify-content: space-between; padding: 14px 0; border-bottom: 1px solid var(--card-line); text-decoration: none; color: var(--ink); }
.set-row:last-child { border-bottom: 0; }
.set-row .t { font-size: 15px; }
.set-row .r { display: flex; align-items: center; gap: 6px; font-size: 13px; color: var(--ink-2); }

/* ---------- 登录 / 注册 ---------- */
.auth .screen { min-height: 844px; }
.auth-hero { padding: 40px var(--pad) 30px; text-align: center; }
.auth-logo { width: 66px; height: 66px; margin: 0 auto 12px; }
.auth-title { font-size: 26px; font-weight: 600; letter-spacing: 1px; }
.auth-sub { margin-top: 6px; font-size: 13px; color: var(--ink-2); }
.auth-card { margin: 0 var(--pad); }
.auth-foot { margin: 18px var(--pad) 0; text-align: center; font-size: 13px; color: var(--ink-2); }
.auth-foot a { color: var(--berry); text-decoration: none; font-weight: 600; }
.auth-note { margin-top: 14px; font-size: 12px; line-height: 18px; color: var(--ink-2); text-align: center; }

/* ---------- 对比 ---------- */
.cmp-card { margin-top: 10px; }
.cmp-date { font-size: 12px; color: var(--ink-2); text-align: center; margin-top: 6px; }
"""


def svg_back():
    return ('<svg width="18" height="18" viewBox="0 0 18 18" fill="none" stroke="currentColor" '
            'stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"><path d="M10.6 4 5.6 9l5 5"/></svg>')


def chev():
    return ('<svg width="13" height="13" viewBox="0 0 16 16" fill="none" stroke="#655966" stroke-width="1.6" '
            'stroke-linecap="round" stroke-linejoin="round"><path d="M6 3.5 10.5 8 6 12.5"/></svg>')


def shell(title, kicker, heading, sub, body, back, cls=""):
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>她记 · {title}</title>
<link rel="stylesheet" href="../前端样式/styles.css">
<link rel="stylesheet" href="theme.css">
<link rel="stylesheet" href="business.css">
<script>if(self!==top){{document.documentElement.className+=' embed';}}</script>
</head>
<body class="subpage {cls}">
<div class="screen">
  <header class="hero sub-hero">
    <div class="sub-bar">
      <a class="back" href="{back}" aria-label="返回">{svg_back()}</a>
      <span class="sub-kicker">{kicker}</span>
    </div>
    <h1 class="sub-title">{heading}</h1>
    <div class="sub-sub">{sub}</div>
  </header>
  <main class="main sub-main">
{body}
  </main>
</div>
</body>
</html>
"""


def build_static():
    OUT.mkdir(exist_ok=True)
    for d in ["icons", "assets"]:
        if (OUT / d).exists():
            shutil.rmtree(OUT / d)
        shutil.copytree(SRC / d, OUT / d)
    shutil.copy2(SRC / "theme.css", OUT / "theme.css")
    shutil.copy2(SRC / "assets.css", OUT / "assets.css")
    shutil.copy2(ROOT / "app-icon" / "app-icon.svg", OUT / "assets" / "app-icon.svg")
    (OUT / "business.css").write_text(BUSINESS_CSS, encoding="utf-8")


def build_primary():
    for name in ["home", "period", "weight", "skin", "me"]:
        s = (SRC / (name + ".html")).read_text(encoding="utf-8")
        s = s.replace("../../前端样式/styles.css", "../前端样式/styles.css")
        s = s.replace('<link rel="stylesheet" href="assets.css">',
                      '<link rel="stylesheet" href="assets.css">\n<link rel="stylesheet" href="business.css">')
        (OUT / (name + ".html")).write_text(s, encoding="utf-8")


if __name__ == "__main__":
    build_static()
    build_primary()
    print("static + primary ready")
