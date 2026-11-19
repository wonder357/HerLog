# -*- coding: utf-8 -*-
"""生成四套渐变主题（结构复用 前端样式/pages，只叠加 theme.css 与配色）"""
import shutil
from pathlib import Path

ROOT = Path(r"C:\Users\kunlunmeta\my-first-project\豆包")
BASE = ROOT / "前端样式"
OUT = ROOT / "风格方案"

THEMES = {
    "peach": dict(
        dir="01-蜜桃奶油", name="蜜桃奶油", en="Peach Cream",
        desc="奶油橘粉渐变，日常温柔，长时间看不刺激。",
        page="#FDF6F1", page2="#FCF2EA", surface="#FFFFFF",
        accent="#C0566B", deep="#9C3B50", soft="#FBE2E6", soft2="#FFF0F2", pink="#F2B4BC",
        ink="#3B2A2D", ink2="#7B6367", line="#F4E5E1", outline="#9C8285", error="#A32638",
        hero="radial-gradient(120% 95% at 84% 0%, #FFD8C0 0%, rgba(255,216,192,0) 58%), radial-gradient(85% 70% at 6% 12%, #FFE4EC 0%, rgba(255,228,236,0) 62%), linear-gradient(168deg, #FFE7D2 0%, #F7CDDC 52%, #FDF6F1 100%)",
        card1="#FFFFFF", card2="#FFF9F6", cardline="#F6E6E2",
        cardshadow="0 12px 28px -14px rgba(192,86,107,.28)",
        btn1="#D6788B", btn2="#BD5266", btnshadow="rgba(192,86,107,.40)",
        tab1="#FDE7EA", tab2="#FADDE8",
        segbg="#FBEDEA", ghost2="#FFF7F8", ghostline="#EFD3D8", chip2="#FFF8F6",
        input2="#FFFCFA", readonly="#F8EFEC",
        avatar="linear-gradient(140deg,#FCE3E6,#FBE7DC)",
        photo="radial-gradient(120% 120% at 30% 20%,#F8DED4,#EFCBBF)",
        glow="rgba(255,236,224,.85)", hair="rgba(192,86,107,.24)", icshadow="rgba(192,86,107,.35)",
        dark_hero=False,
    ),
    "dusk": dict(
        dir="02-暮光玫瑰", name="暮光玫瑰", en="Dusk Rose",
        desc="深莓到玫瑰的暮色渐变，金色点缀，晚间仪式感强。",
        page="#FBF6F9", page2="#F9F1F5", surface="#FFFFFF",
        accent="#8E2B52", deep="#6C1E3E", soft="#F6DDE7", soft2="#FCEEF3", pink="#DCA7BC",
        ink="#2B2027", ink2="#6B5865", line="#EBDFE6", outline="#8D7B86", error="#A32638",
        hero="radial-gradient(80% 70% at 16% -8%, rgba(201,160,99,.52) 0%, rgba(201,160,99,0) 62%), radial-gradient(70% 60% at 96% 12%, rgba(255,214,228,.34) 0%, rgba(255,214,228,0) 60%), linear-gradient(152deg, #451730 0%, #752142 40%, #A85C7D 74%, #D0A3B8 100%)",
        card1="#FFFFFF", card2="#FFFAFD", cardline="#F1E2EB",
        cardshadow="0 14px 30px -16px rgba(96,26,54,.40)",
        btn1="#A83B63", btn2="#75203E", btnshadow="rgba(94,24,50,.45)",
        tab1="#F8DEE9", tab2="#F1CFE1",
        segbg="#F7ECF2", ghost2="#FFF7FA", ghostline="#ECD3DF", chip2="#FFF8FB",
        input2="#FFFBFD", readonly="#F7EFF3",
        avatar="linear-gradient(140deg,#6E2342,#A85C7D)",
        photo="radial-gradient(120% 120% at 30% 20%,#E8D2DA,#C9A3B2)",
        glow="rgba(201,160,99,.55)", hair="rgba(201,160,99,.55)", icshadow="rgba(120,32,62,.40)",
        dark_hero=True,
    ),
    "apricot": dict(
        dir="03-杏桃霞光", name="杏桃霞光", en="Apricot Glow",
        desc="杏橘与珊瑚粉的暖光渐变，日光感强，适合白天记录。",
        page="#FDF7F0", page2="#FDF3E8", surface="#FFFDF9",
        accent="#A5583A", deep="#83402A", soft="#FBE5D5", soft2="#FFF1E6", pink="#EFBE9C",
        ink="#392A24", ink2="#7C6459", line="#F2E2D4", outline="#9C8376", error="#A32638",
        hero="radial-gradient(110% 90% at 86% 0%, #FFDCAE 0%, rgba(255,220,174,0) 58%), radial-gradient(80% 70% at 4% 10%, #FFE9EC 0%, rgba(255,233,236,0) 60%), linear-gradient(166deg, #FFE4BE 0%, #FFCEC2 55%, #FDF7F0 100%)",
        card1="#FFFDFA", card2="#FFFAF2", cardline="#F5E6D7",
        cardshadow="0 12px 28px -14px rgba(166,88,58,.28)",
        btn1="#CA7A57", btn2="#A45739", btnshadow="rgba(166,88,58,.40)",
        tab1="#FCE9DB", tab2="#F8E0D2",
        segbg="#FAEFE5", ghost2="#FFF8F1", ghostline="#EFD8C6", chip2="#FFFAF4",
        input2="#FFFCF7", readonly="#F9F0E7",
        avatar="linear-gradient(140deg,#FBE3D6,#F7DCE0)",
        photo="radial-gradient(120% 120% at 30% 20%,#F7E0CB,#EBC9AE)",
        glow="rgba(255,232,200,.85)", hair="rgba(166,88,58,.24)", icshadow="rgba(166,88,58,.35)",
        dark_hero=False,
    ),
    "mauve": dict(
        dir="04-雾紫珍珠", name="雾紫珍珠", en="Misty Pearl",
        desc="薰衣草与珍珠粉的冷调渐变，安静精致，偏理性。",
        page="#FAF7FB", page2="#F8F1FA", surface="#FFFFFF",
        accent="#6E4B7E", deep="#553A64", soft="#EFE3F3", soft2="#F9F1FB", pink="#D6BDE0",
        ink="#2E2632", ink2="#6D6273", line="#EAE1EE", outline="#8E8194", error="#A32638",
        hero="radial-gradient(90% 80% at 18% 0%, #FBE0F1 0%, rgba(251,224,241,0) 60%), radial-gradient(80% 70% at 92% 8%, #E4D6F6 0%, rgba(228,214,246,0) 62%), linear-gradient(166deg, #F4E0FA 0%, #F7DCEA 55%, #FAF7FB 100%)",
        card1="#FFFFFF", card2="#FCFAFD", cardline="#EDE4F1",
        cardshadow="0 12px 28px -14px rgba(110,75,126,.26)",
        btn1="#8A5F9C", btn2="#6A4779", btnshadow="rgba(110,75,126,.38)",
        tab1="#F2E5F6", tab2="#EDDFF2",
        segbg="#F5EFF8", ghost2="#FDF9FE", ghostline="#E2D3E9", chip2="#FCF9FD",
        input2="#FDFBFE", readonly="#F6F0F8",
        avatar="linear-gradient(140deg,#EEE2F5,#FBE7EF)",
        photo="radial-gradient(120% 120% at 30% 20%,#EFE3EA,#DCC5DA)",
        glow="rgba(240,226,250,.90)", hair="rgba(110,75,126,.22)", icshadow="rgba(110,75,126,.32)",
        dark_hero=False,
    ),
}

THEME_CSS = """@charset "UTF-8";
/* ============================================================
   @@NAME@@ · 渐变主题皮肤
   在 ../../前端样式/styles.css 之上叠加：只覆盖视觉，不改结构
   ============================================================ */
:root{
  --page: @@PAGE@@;
  --surface: @@SURFACE@@;
  --berry: @@ACCENT@@;
  --berry-deep: @@DEEP@@;
  --berry-soft: @@SOFT@@;
  --berry-pink: @@PINK@@;
  --ink: @@INK@@;
  --ink-2: @@INK2@@;
  --line: @@LINE@@;
  --outline: @@OUTLINE@@;
  --error: @@ERROR@@;
  --hero-grad: @@HERO@@;
  --radius-card: 12px;

  --page-grad: linear-gradient(180deg, @@PAGE@@ 0%, @@PAGE2@@ 100%);
  --card-grad: linear-gradient(180deg, @@CARD1@@ 0%, @@CARD2@@ 100%);
  --card-line: @@CARDLINE@@;
  --card-shadow: @@CARDSHADOW@@;
  --btn-grad: linear-gradient(135deg, @@BTN1@@ 0%, @@BTN2@@ 100%);
  --btn-shadow: @@BTNSHADOW@@;
  --tabon-grad: linear-gradient(135deg, @@TAB1@@ 0%, @@TAB2@@ 100%);
  --soft-grad: linear-gradient(135deg, @@SOFT@@ 0%, @@SOFT2@@ 100%);
  --soft-2: @@SOFT2@@;
  --segbg: @@SEGBG@@;
  --ghost-2: @@GHOST2@@;
  --ghost-line: @@GHOSTLINE@@;
  --chip-2: @@CHIP2@@;
  --input-2: @@INPUT2@@;
  --readonly: @@READONLY@@;
  --avatar-grad: @@AVATAR@@;
  --photo-grad: @@PHOTO@@;
  --glow: @@GLOW@@;
  --hair: @@HAIR@@;
  --ic-shadow: @@ICSHADOW@@;
}

body{background:var(--page);}
.screen{background:var(--page-grad);}

/* ---------- 页首 ---------- */
.hero{position:relative;overflow:hidden;background:linear-gradient(180deg, rgba(255,255,255,0) 56%, var(--page) 100%), var(--hero-grad);}
.hero::before{
  content:"";position:absolute;right:-80px;top:-110px;width:260px;height:260px;border-radius:50%;
  background:radial-gradient(circle at 50% 50%, var(--glow) 0%, rgba(255,255,255,0) 70%);
  pointer-events:none;
}
.hero::after{
  content:"";position:absolute;left:18px;right:18px;bottom:0;height:1px;
  background:linear-gradient(90deg, rgba(255,255,255,0), color-mix(in srgb, var(--hair) 62%, transparent) 26%, color-mix(in srgb, var(--hair) 62%, transparent) 74%, rgba(255,255,255,0));
  pointer-events:none;
}
.hero > *{position:relative;z-index:1;}
.hero h1{letter-spacing:1px;}

/* ---------- 卡片 ---------- */
.card,.quick-item,.rowlink{
  background:var(--card-grad);
  border:1px solid var(--card-line);
  box-shadow:inset 0 1px 0 rgba(255,255,255,.90), var(--card-shadow);
}
.card.flat{box-shadow:none;}

/* ---------- 按钮 ---------- */
.btn{
  background:var(--btn-grad);
  box-shadow:0 12px 24px -10px var(--btn-shadow), inset 0 1px 0 rgba(255,255,255,.30);
}
.btn:active{background:var(--btn-grad);filter:brightness(.94);}
.btn.ghost{
  background:linear-gradient(180deg,#FFFFFF 0%, var(--ghost-2) 100%);
  color:var(--berry);
  border:1px solid var(--ghost-line);
  box-shadow:0 6px 16px -12px var(--btn-shadow);
}
.btn.soft{
  background:var(--soft-grad);
  color:var(--berry-deep);
  border:1px solid transparent;
  box-shadow:0 6px 14px -12px var(--btn-shadow);
}

/* ---------- 标签 / chip ---------- */
.tag{background:var(--soft-grad);color:var(--berry-deep);}
.tag.plain{background:var(--soft-grad);color:var(--ink-2);}
.tag.outline{border-color:var(--berry);color:var(--berry);background:rgba(255,255,255,.55);}
.chip{background:linear-gradient(180deg,#FFFFFF 0%, var(--chip-2) 100%);border-color:var(--card-line);}
.chip.on{background:var(--soft-grad);border-color:transparent;color:var(--berry-deep);}

/* ---------- 快捷入口 ---------- */
.quick-item{position:relative;overflow:hidden;}
.quick-item::after{
  content:"";position:absolute;left:0;right:0;top:-30%;height:90%;
  background:radial-gradient(60% 60% at 50% 50%, var(--glow) 0%, rgba(255,255,255,0) 70%);
  opacity:.5;pointer-events:none;
}
.quick-item > *{position:relative;z-index:1;}
.quick-item .qi-ic{filter:drop-shadow(0 6px 10px var(--ic-shadow));}

/* ---------- 标题与数字 ---------- */
.h2{position:relative;padding-left:11px;}
.h2::before{
  content:"";position:absolute;left:0;top:5px;width:4px;height:16px;border-radius:2px;
  background:linear-gradient(180deg, var(--berry) 0%, var(--berry-pink) 100%);
}
.status-main,.last-weight .num{
  background:linear-gradient(120deg, var(--berry-deep) 0%, var(--berry) 52%, var(--berry-pink) 100%);
  -webkit-background-clip:text;background-clip:text;color:transparent;
}

/* ---------- 分段器 ---------- */
.segmented{background:var(--segbg);border:1px solid var(--card-line);box-shadow:none;}
.segmented button.on{background:#FFFFFF;color:var(--berry);box-shadow:0 4px 10px -6px var(--btn-shadow);}

/* ---------- iframe 预览：底栏固定在手机视口底部 ---------- */
.embed .tabbar{position:fixed;left:0;right:0;bottom:0;z-index:9;margin-top:0;}

/* ---------- 日历 ---------- */
.day.period{background:var(--berry-soft);}
.day.selected{box-shadow:inset 0 0 0 1.5px var(--berry);}

/* ---------- 对话 ---------- */
.bubble.me{background:linear-gradient(135deg, var(--berry-soft) 0%, var(--soft-2) 100%);}

/* ---------- 底栏 ---------- */
.tabbar{
  background:rgba(255,255,255,.84);
  -webkit-backdrop-filter:blur(16px) saturate(1.6);
  backdrop-filter:blur(16px) saturate(1.6);
  border-top:1px solid var(--line);
  box-shadow:0 -12px 30px -18px var(--btn-shadow);
}
.tab.on .tab-ic{background:var(--tabon-grad);box-shadow:0 8px 16px -8px var(--btn-shadow);}

/* ---------- 表单 ---------- */
.field .control{background:linear-gradient(180deg,#FFFFFF 0%, var(--input-2) 100%);border-color:var(--card-line);}
.field .control.readonly{background:var(--readonly);border-color:transparent;color:var(--ink-2);}

/* ---------- 其他 ---------- */
.advice .ad-ic{background:var(--soft-grad);}
.legend .sw.period{background:var(--soft-grad);}
.avatar{background:var(--avatar-grad);color:var(--berry-deep);}
.photo{background:var(--photo-grad);}
"""

DARK_HERO_CSS = """
/* ---------- 深色页首文字 ---------- */
.hero{background:var(--hero-grad);}
.hero-date,.hero-sub{color:rgba(255,247,250,.80);}
.hero h1{color:#FFF9FB;}
.hero .tag.outline{color:#FFF9FB;border-color:rgba(255,249,251,.55);background:rgba(255,255,255,.12);}
.hero .status-main{
  background:linear-gradient(120deg,#FFF8FB 0%,#F3D9C2 55%,#E9B9CB 100%);
  -webkit-background-clip:text;background-clip:text;color:transparent;
}
.hero .profile .name{color:#FFF9FB;}
.hero .profile .user{color:rgba(255,247,250,.72);}
.hero .avatar{background:rgba(255,255,255,.16);color:#FFF9FB;border:1px solid rgba(255,255,255,.30);}
.hero::before{background:radial-gradient(circle at 50% 50%, rgba(201,160,99,.55) 0%, rgba(255,255,255,0) 70%);}
.hero::after{background:linear-gradient(90deg, rgba(255,255,255,0), rgba(232,196,143,.72) 30%, rgba(255,243,228,.40) 80%, rgba(255,255,255,0));}
"""

PAGES = [("home", "首页", "快捷入口 + 只读问答"),
         ("period", "经期", "状态 → 月历 → 当天记录 → 历史"),
         ("weight", "体重", "最近体重 + 趋势 + 一条建议"),
         ("skin", "皮肤", "拍照分析 + 最近观察"),
         ("me", "我的", "资料表单 + 退出登录")]

THEME_GALLERY = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>@@NAME@@ · 五页样式</title>
<link rel="stylesheet" href="../../前端样式/styles.css">
<link rel="stylesheet" href="theme.css">
<style>
  body { background: #EFEBF0; padding: 28px 30px 46px; }
  .g-head { max-width: 1300px; margin: 0 auto 18px; }
  .g-head h1 { margin: 0; font-size: 24px; letter-spacing: .6px; }
  .g-head h1 span { font-size: 12px; color: var(--ink-2); letter-spacing: 1.5px; margin-left: 8px; font-weight: 500; }
  .g-head p { margin: 6px 0 0; font-size: 13px; color: var(--ink-2); }
  .gallery { display: flex; flex-wrap: wrap; gap: 22px; justify-content: center; max-width: 1320px; margin: 0 auto; }
  .frame { display: flex; flex-direction: column; gap: 10px; }
  .frame .cap { font-size: 12px; color: var(--ink-2); padding-left: 4px; }
  .frame .cap b { color: var(--ink); font-weight: 600; }
  iframe { width: 390px; height: 844px; border: 0; border-radius: 18px; background: #FFFFFF; box-shadow: 0 8px 26px rgba(45,36,48,.12); }
</style>
</head>
<body>
  <div class="g-head">
    <h1>@@NAME@@<span>@@EN@@</span></h1>
    <p>@@DESC@@</p>
  </div>
  <div class="gallery">
@@FRAMES@@
  </div>
</body>
</html>
"""

FRAME = """    <div class="frame">
      <iframe src="@@PAGE@@.html" title="@@CN@@"></iframe>
      <div class="cap"><b>@@CN@@</b>　@@CAP@@</div>
    </div>"""

TOP_INDEX = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>她记 HerLog · 渐变主题提案</title>
<link rel="stylesheet" href="../前端样式/styles.css">
<style>
  body { background: #F1EDF2; padding: 34px 40px 52px; }
  .head { max-width: 1780px; margin: 0 auto 22px; }
  .head h1 { margin: 0; font-size: 26px; letter-spacing: .5px; }
  .head p { margin: 8px 0 0; font-size: 13px; color: #655966; }
  .grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 20px; max-width: 1780px; margin: 0 auto; }
  .style-card { background: #FFFFFF; border-radius: 18px; padding: 18px 18px 16px; box-shadow: 0 10px 30px rgba(45,36,48,.08); }
  .style-card .name { font-size: 19px; font-weight: 600; letter-spacing: .5px; }
  .style-card .en { font-size: 11px; letter-spacing: 1.8px; color: #8B7988; margin-top: 3px; text-transform: uppercase; }
  .style-card .desc { font-size: 12px; line-height: 19px; color: #655966; margin: 8px 0 12px; min-height: 38px; }
  .grad { height: 58px; border-radius: 12px; margin-bottom: 12px; border: 1px solid rgba(45,36,48,.06); }
  .palette { display: flex; gap: 6px; margin-bottom: 14px; }
  .sw { flex: 1; height: 22px; border-radius: 6px; }
  iframe { width: 100%; height: 844px; border: 0; border-radius: 14px; background: #FFFFFF; }
  .go { display: inline-block; margin-top: 12px; font-size: 13px; color: #A82760; text-decoration: none; }
</style>
</head>
<body>
  <div class="head">
    <h1>她记 HerLog · 渐变主题提案</h1>
    <p>四套方案共用同一套结构与文案，只替换颜色、渐变与材质；每套都含完整五页。点开任一套可看全部页面。</p>
  </div>
  <div class="grid">
@@CARDS@@
  </div>
</body>
</html>
"""

TOP_CARD = """    <div class="style-card">
      <div class="name">@@NAME@@</div>
      <div class="en">@@EN@@</div>
      <div class="desc">@@DESC@@</div>
      <div class="grad" style="background:@@HERO@@"></div>
      <div class="palette">
        <div class="sw" style="background:@@C1@@"></div>
        <div class="sw" style="background:@@C2@@"></div>
        <div class="sw" style="background:@@C3@@"></div>
        <div class="sw" style="background:@@C4@@"></div>
        <div class="sw" style="background:@@C5@@"></div>
      </div>
      <iframe src="@@DIR@@/home.html" title="@@NAME@@"></iframe>
      <a class="go" href="@@DIR@@/index.html" style="color:@@ACCENT@@">查看五页 →</a>
    </div>"""


def fill(t, tpl):
    for k, v in t.items():
        tpl = tpl.replace("@@" + k.upper() + "@@", str(v))
    return tpl


def main():
    OUT.mkdir(exist_ok=True)
    for key, t in THEMES.items():
        d = OUT / t["dir"]
        (d / "icons").mkdir(parents=True, exist_ok=True)

        css = fill(t, THEME_CSS) + (DARK_HERO_CSS if t["dark_hero"] else "")
        (d / "theme.css").write_text(css, encoding="utf-8")

        for name, cn, cap in PAGES:
            src = (BASE / "pages" / (name + ".html")).read_text(encoding="utf-8")
            src = src.replace('<link rel="stylesheet" href="../styles.css">',
                              '<link rel="stylesheet" href="../../前端样式/styles.css">\n'
                              '<link rel="stylesheet" href="theme.css">')
            src = src.replace("../assets/icons/", "icons/")
            src = src.replace("#A82760", t["accent"]).replace("#F7DFEA", t["soft"])
            src = src.replace("</head>",
                              "<script>if(self!==top){document.documentElement.className+=' embed';}</script></head>")
            (d / (name + ".html")).write_text(src, encoding="utf-8")

        for svg in (BASE / "assets" / "icons").glob("*.svg"):
            txt = svg.read_text(encoding="utf-8")
            txt = txt.replace("#8B7988", t["outline"]).replace("#A82760", t["accent"])
            (d / "icons" / svg.name).write_text(txt, encoding="utf-8")

        frames = "\n".join(
            FRAME.replace("@@PAGE@@", n).replace("@@CN@@", cn).replace("@@CAP@@", cap)
            for n, cn, cap in PAGES
        )
        (d / "index.html").write_text(fill(t, THEME_GALLERY.replace("@@FRAMES@@", frames)), encoding="utf-8")
        print("built", t["dir"])

    cards = []
    for t in THEMES.values():
        c = (TOP_CARD.replace("@@NAME@@", t["name"]).replace("@@EN@@", t["en"])
             .replace("@@DESC@@", t["desc"]).replace("@@HERO@@", t["hero"])
             .replace("@@ACCENT@@", t["accent"]).replace("@@DIR@@", t["dir"]))
        for i, k in enumerate(["accent", "soft", "pink", "card2", "page"], 1):
            c = c.replace(f"@@C{i}@@", t[k])
        cards.append(c)
    (OUT / "index.html").write_text(TOP_INDEX.replace("@@CARDS@@", "\n".join(cards)), encoding="utf-8")
    print("top index built")


if __name__ == "__main__":
    main()
