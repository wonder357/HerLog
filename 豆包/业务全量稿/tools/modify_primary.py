# -*- coding: utf-8 -*-
"""在一级页上打通二级页入口（只改业务全量稿副本）"""
import re
from pathlib import Path

OUT = Path(r"C:\Users\kunlunmeta\my-first-project\豆包\业务全量稿")


def edit(name, fn):
    p = OUT / (name + ".html")
    s = p.read_text(encoding="utf-8")
    s2 = fn(s)
    p.write_text(s2, encoding="utf-8")
    print(name, "changed" if s2 != s else "UNCHANGED")


def home(s):
    def wrap(m):
        block = m.group(0)
        if "period-berry" in block:
            href = "period-record.html"
        elif "weight-berry" in block:
            href = "weight-record.html"
        else:
            href = "skin-capture.html"
        return f'<a class="qlink" href="{href}">{block}</a>'
    return re.sub(r'<div class="quick-item">.*?</div>', wrap, s, flags=re.S)


def period(s):
    s = s.replace('<button class="btn soft">记录经期</button>',
                  '<a class="btn soft" href="period-record.html">记录经期</a>')
    s = s.replace('<button class="btn ghost">记录感受</button>',
                  '<a class="btn ghost" href="period-feelings.html">记录感受</a>')
    s = s.replace('<span class="meta">共 3 段</span>',
                  f'<a class="link" href="period-history.html">共 3 段 ›</a>')
    s = s.replace('<div class="hero-sub">预计下次开始：12 月 12 日 · 按近 3 次记录估算</div>',
                  '<div class="hero-sub">预计下次开始：12 月 12 日 · 按近 3 次记录估算'
                  '<a class="link" href="period-prediction.html" style="font-size:12px;margin-left:6px">怎么算的 ›</a></div>')
    return s


def weight(s):
    s = s.replace('<button class="btn block">记体重</button>',
                  '<a class="btn block" href="weight-record.html">记体重</a>')
    s = s.replace('<a class="rowlink" href="#">', '<a class="rowlink" href="weight-detail.html">')
    s = s.replace('''      <div style="margin-top:12px">
        <a class="rowlink" href="weight-detail.html">''',
                  '''      <div style="margin-top:12px">
        <a class="rowlink" href="weight-detail.html">''')
    # 趋势详情入口挂在趋势卡下方
    s = s.replace('''      </div>

      <div style="margin-top:12px">''', '''      </div>
      <div style="text-align:right;margin-top:2px"><a class="link" href="weight-trend.html">查看趋势详情 ›</a></div>

      <div style="margin-top:12px">''')
    return s


def skin(s):
    s = s.replace('<button class="btn block">拍照分析</button>',
                  '<a class="btn block" href="skin-capture.html">拍照分析</a>')
    s = s.replace('<a class="link" href="#">历史记录', '<a class="link" href="skin-history.html">历史记录')
    s = s.replace('''        <div class="note" style="margin-top:12px">
          以上为模型生成的观察文字''', '''        <div style="margin-top:12px"><a class="link" href="skin-result.html">查看完整结果 ›</a></div>
        <div class="note" style="margin-top:8px">
          以上为模型生成的观察文字''')
    return s


def me(s):
    s = s.replace('''      <div class="actions-stack">''', '''      <a class="rowlink" href="settings.html" style="margin-top:12px">
        <span>设置与隐私</span>
        <span style="display:flex;align-items:center;gap:6px;color:#655966;font-size:13px">账号、数据与关于
          <svg width="14" height="14" viewBox="0 0 16 16" fill="none" stroke="#655966" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><path d="M6 3.5 10.5 8 6 12.5"/></svg>
        </span>
      </a>

      <div class="actions-stack">''')
    s = s.replace('<button class="btn ghost block">退出登录</button>',
                  '<a class="btn ghost block" href="login.html">退出登录</a>')
    return s


edit("home", home)
edit("period", period)
edit("weight", weight)
edit("skin", skin)
edit("me", me)
