# -*- coding: utf-8 -*-
from pathlib import Path

BASE = Path(r"C:\Users\kunlunmeta\my-first-project\豆包\业务全量稿")

GROUPS = [
    ("首页", "每天打开的第一屏，只回答“今天怎么样、要记什么”。", [
        ("home", "首页 · 今天", "一级", "日期与经期/体重摘要、三个快捷入口、只读问答。", "首页不承载趋势、历史、建议，避免和四个业务页抢入口。"),
    ]),
    ("经期", "一条主线：先看状态与日历，再补当天记录，最后回看历史与预测。", [
        ("period", "经期", "一级", "状态行、月历（实际实色/预计虚线/感受点）、当天记录、历史入口。", "只显示“今天该做什么”，完整周期列表与预测解释拆到二级页。"),
        ("period-record", "记录经期", "二级 · 半屏", "开始 / 最后一天切换，日期、持续天数、重叠提示、删除本段。", "高频录入不跳页；半屏保留日历上下文，选完即回。"),
        ("period-feelings", "记录感受", "二级 · 半屏", "经量、腹痛、其他不适、情绪、生活影响、备注。", "与经期日期分开保存；只填一项也能存，不新建经期。"),
        ("period-history", "历史回顾", "二级", "按开始日倒序的周期列表，含持续天数与距上次间隔。", "列表变长后不挤占一级页；历史只读，编辑回半屏。"),
        ("period-prediction", "预测说明", "二级", "预计日期、参与计算的周期、四条规则、三种异常状态。", "预测需要解释口径与不确定性，独立成页才能讲清楚。"),
    ]),
    ("体重", "只记录与呈现，不评价单次涨跌。", [
        ("weight", "体重", "一级", "最近一次测量、30 天趋势、记录明细入口、一条与记录情况相关的建议。", "首屏给“现在多少”，趋势细节与逐笔数据拆到二级。"),
        ("weight-record", "记体重", "二级 · 半屏", "大数字、测量时间、标签、数字键盘。", "单手可完成；不跳页，保存后直接回到体重页。"),
        ("weight-detail", "记录明细", "二级", "时间倒序、全部/近30天/近7天筛选、逐笔编辑与删除。", "同日多笔全部保留，需要独立列表承载。"),
        ("weight-trend", "趋势详情", "二级", "可选数据点、统计三项、口径说明。", "一级页只放缩略趋势；点选与统计需要更大画布。"),
    ]),
    ("皮肤", "一条“拍—看—存—比”的链路，任何一步都可退出且不产生记录。", [
        ("skin", "皮肤", "一级", "顶部双按钮（拍照分析 / 历史记录）+ 最近一次照片与 AI 观察。", "首屏只给最近一次，避免历史照片堆叠。"),
        ("skin-capture", "拍照分析", "二级", "选部位、拍摄提示、相机/相册入口、发送说明。", "拍摄需要明确的部位与光线约束，独立成页降低废片率。"),
        ("skin-result", "分析结果", "二级", "照片、三段观察、观察标签、免责声明、保存/不保存/重拍。", "保存是唯一入库动作，必须有独立确认页。"),
        ("skin-history", "历史观察", "二级", "按时间倒序的观察卡、同部位筛选、对比入口。", "多次观察需要列表与对比入口。"),
        ("skin-compare", "两次对比", "二级", "两张照片、两段已保存文字、共性与差异。", "对比只用已保存文字，不重新发照片，需明确标注口径。"),
    ]),
    ("我的", "账号资料与边界说明，不放业务数据。", [
        ("me", "我的", "一级", "只读用户名、生日/身高/电话选填、保存、设置入口、退出。", "资料与账号动作集中在最后一屏。"),
        ("settings", "设置", "二级", "账号、数据与隐私、关于、退出登录。", "把低频设置从“我的”表单里拆出，避免首屏过长。"),
        ("privacy", "数据与隐私", "二级", "记录归属、照片与 AI、首页问答、账号注销、可删除项。", "隐私边界需要完整文字，不能只靠一行提示。"),
        ("about", "关于她记", "二级", "产品定位、不做什么、免责声明、素材版权。", "合规与免责内容集中放置，便于版本审查。"),
    ]),
    ("账号", "进入应用前的两道门，注册成功回登录。", [
        ("login", "登录", "二级", "用户名、密码、登录、注册入口。", "未登录访问业务页时回到此页。"),
        ("register", "注册", "二级", "用户名、密码、确认密码、注册说明。", "注册不自动登录，成功后回登录页。"),
    ]),
]


def badge(level):
    cls = "l1" if level == "一级" else "l2"
    return f'<span class="badge {cls}">{level}</span>'


cards_html = ""
for gname, gdesc, items in GROUPS:
    inner = ""
    for name, title, level, func, why in items:
        src = name + "-preview" if name == "period-record" else name
        inner += f"""
        <article class="pcard">
          <a class="thumb" href="{name}.html"><img src="shots/{src}.png" alt="{title}"></a>
          <div class="pbody">
            <div class="ptop"><h3>{title}</h3>{badge(level)}</div>
            <p class="pfunc">{func}</p>
            <p class="pwhy">{why}</p>
            <div class="plink"><a href="{name}.html">打开页面</a><span>{name}.html</span></div>
          </div>
        </article>"""
    cards_html += f"""
    <section class="group">
      <div class="ghead"><h2>{gname}</h2><p>{gdesc}</p><span class="count">{len(items)} 屏</span></div>
      <div class="grid">{inner}</div>
    </section>"""

INDEX = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>她记 HerLog · 业务全量稿</title>
<style>
* {{ box-sizing: border-box; }}
body {{ margin: 0; background: #FBF1EC; color: #4E333A;
  font-family: "PingFang SC","Microsoft YaHei","Hiragino Sans GB",system-ui,sans-serif; }}
.page {{ max-width: 1320px; margin: 0 auto; padding: 56px 40px 80px; }}
header.top {{ display: flex; align-items: flex-end; justify-content: space-between; gap: 24px; flex-wrap: wrap; }}
.brand {{ font-size: 12px; letter-spacing: 4px; color: #A98A92; }}
h1 {{ margin: 10px 0 8px; font-size: 40px; letter-spacing: 1px; }}
.lead {{ margin: 0; color: #7A6068; font-size: 15px; line-height: 1.7; max-width: 720px; }}
.metrics {{ display: flex; gap: 10px; flex-wrap: wrap; }}
.metric {{ background: linear-gradient(150deg,#FFFDFC,#FFF2F0); border: 1px solid #F2DEDA; border-radius: 14px;
  padding: 12px 18px; min-width: 104px; text-align: center; box-shadow: 0 12px 26px -22px rgba(156,59,80,.5); }}
.metric b {{ display: block; font-size: 26px; color: #C0566B; font-variant-numeric: tabular-nums; }}
.metric span {{ font-size: 11px; color: #8A7178; }}

.legend {{ display: flex; gap: 18px; margin: 28px 0 8px; font-size: 12px; color: #7A6068; flex-wrap: wrap; }}
.legend i {{ display: inline-block; width: 8px; height: 8px; border-radius: 50%; margin-right: 6px; vertical-align: 1px; }}

.group {{ margin-top: 46px; }}
.ghead {{ display: flex; align-items: baseline; gap: 14px; flex-wrap: wrap; padding-bottom: 12px; border-bottom: 1px solid #EDD8D2; }}
.ghead h2 {{ margin: 0; font-size: 22px; letter-spacing: 1px; }}
.ghead p {{ margin: 0; font-size: 13px; color: #8A7178; }}
.ghead .count {{ margin-left: auto; font-size: 12px; color: #A98A92; }}
.grid {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 24px; margin-top: 22px; }}
.pcard {{ background: #FFFCFA; border: 1px solid #F1DFDA; border-radius: 18px; overflow: hidden;
  box-shadow: 0 22px 40px -34px rgba(156,59,80,.55); display: flex; flex-direction: column; }}
.thumb {{ display: block; height: 360px; overflow: hidden; background: #FFF4F0; border-bottom: 1px solid #F5E6E1; position: relative; }}
.thumb img {{ width: 100%; display: block; }}
.thumb:after {{ content: ""; position: absolute; inset: 0; background: linear-gradient(180deg, rgba(255,255,255,0) 62%, rgba(255,252,250,.95)); }}
.pbody {{ padding: 16px 18px 18px; }}
.ptop {{ display: flex; align-items: center; gap: 8px; }}
.ptop h3 {{ margin: 0; font-size: 17px; }}
.badge {{ font-size: 10px; padding: 2px 7px; border-radius: 20px; border: 1px solid; letter-spacing: .5px; }}
.badge.l1 {{ color: #A82760; border-color: #E7B9C6; background: #FFF0F4; }}
.badge.l2 {{ color: #7B6B78; border-color: #E3D8E1; background: #F8F3F7; }}
.pfunc {{ margin: 10px 0 0; font-size: 13px; line-height: 1.65; color: #5C444B; }}
.pwhy {{ margin: 8px 0 0; font-size: 12px; line-height: 1.7; color: #96777F; }}
.plink {{ margin-top: 14px; display: flex; align-items: center; justify-content: space-between; font-size: 11px; color: #B09AA0; }}
.plink a {{ color: #C0566B; text-decoration: none; font-size: 12px; font-weight: 600; }}

.rules {{ margin-top: 56px; background: linear-gradient(150deg,#FFFDFB,#FFF3F1); border: 1px solid #F1DCD6;
  border-radius: 20px; padding: 26px 28px; }}
.rules h2 {{ margin: 0 0 14px; font-size: 20px; }}
.rules ol {{ margin: 0; padding-left: 20px; color: #6B525A; font-size: 13px; line-height: 2; }}
.rules b {{ color: #4E333A; }}
footer {{ margin-top: 34px; font-size: 11px; color: #A98A92; display: flex; justify-content: space-between; flex-wrap: wrap; gap: 10px; }}

@media (max-width: 1100px) {{ .grid {{ grid-template-columns: repeat(2,1fr); }} }}
@media (max-width: 720px) {{ .grid {{ grid-template-columns: 1fr; }} .page {{ padding: 32px 18px 60px; }} h1 {{ font-size: 28px; }} }}
</style>
</head>
<body>
<div class="page">
  <header class="top">
    <div>
      <div class="brand">HERLOG / BUSINESS SYSTEM / V1.0</div>
      <h1>她记 · 业务全量稿</h1>
      <p class="lead">以业务为起点的页面拆分：一级页只负责“看今天”和“给入口”，录入用半屏不跳页，历史 / 明细 / 解释 / 设置各自独立成页。视觉沿用蜜桃奶油素材版，保留渐变、纸感卡片与插画头像。</p>
    </div>
    <div class="metrics">
      <div class="metric"><b>5</b><span>一级页面</span></div>
      <div class="metric"><b>16</b><span>二级页面</span></div>
      <div class="metric"><b>21</b><span>屏幕总数</span></div>
      <div class="metric"><b>3</b><span>半屏表单</span></div>
    </div>
  </header>

  <div class="legend">
    <span><i style="background:#C0566B"></i>一级页 · 常驻底栏</span>
    <span><i style="background:#8A7A86"></i>二级页 · 只保留返回</span>
    <span>底部半屏用于经期 / 体重的即时录入</span>
    <span>素材仅用于演示，上线前替换授权版本</span>
  </div>

{cards_html}

  <section class="rules">
    <h2>交互与数据口径（与需求 V0.8 对齐）</h2>
    <ol>
      <li><b>录入不跳页。</b>“记录经期 / 记录感受 / 记体重”都在当前页弹半屏，保存后原页刷新；半屏可下滑关闭，等同取消。</li>
      <li><b>二级页不显示五栏底栏。</b>统一“返回圆钮 + 模块小标 + 标题”，返回目标写死上级页，避免栈里绕圈。</li>
      <li><b>皮肤只有“保存”入库。</b>不保存、重拍、直接返回都不新增记录；照片仅本人可见。</li>
      <li><b>经期预测只在开始日期变化时重算。</b>至少 3 次开始记录、最多取 4 次、2–3 个周期；极差 &gt; 7 天不显示；附“不作为避孕依据”。</li>
      <li><b>体重每天只取最后一次进入趋势。</b>明细保留同日多笔；缺测不补值；不对单次涨跌评价。</li>
      <li><b>首页问答只读。</b>不改记录、不生成草稿、不发送皮肤原图与电话。</li>
      <li><b>退出登录保留数据。</b>重新登录可见；“我的”中用户名只读。</li>
    </ol>
  </section>

  <footer>
    <span>她记 HerLog · 业务全量稿 · 2026-11-19</span>
    <span>蜜桃奶油 · 素材版 / 390 × 844 基准 / 截图 @2x</span>
  </footer>
</div>
</body>
</html>
"""

(BASE / "index.html").write_text(INDEX, encoding="utf-8")
print("index.html", len(INDEX))
