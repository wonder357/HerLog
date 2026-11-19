# -*- coding: utf-8 -*-
"""生成 16 个二级页 + 3 个半屏表单"""
from pathlib import Path

OUT = Path(r"C:\Users\kunlunmeta\my-first-project\豆包\业务全量稿")
from build_business_base import shell, chev  # noqa


def write(name, html):
    (OUT / (name + ".html")).write_text(html, encoding="utf-8")
    print("wrote", name)


# =====================================================================
# 经期
# =====================================================================
period_history = """
    <section class="section" style="margin-top:8px">
      <div class="chips">
        <span class="chip on">全部 3 段</span>
        <span class="chip">2026 年</span>
        <span class="chip">2025 年</span>
      </div>
    </section>

    <section class="section">
      <div class="card">
        <div class="cycle">
          <div class="d"><div class="dd">17</div><div class="dm">11 月 · 2026</div></div>
          <div class="body">
            <div class="t">11 月 17 日开始 <span class="tag">进行中</span></div>
            <div class="s">未记录结束 · 已记录 3 天</div>
          </div>
          <div class="r">持续 3 天（至今）<br>距上次开始 25 天</div>
        </div>
        <div class="cycle">
          <div class="d"><div class="dd">23</div><div class="dm">10 月 · 2026</div></div>
          <div class="body">
            <div class="t">10 月 23 日 – 10 月 27 日</div>
            <div class="s">已记录结束日</div>
          </div>
          <div class="r">持续 5 天<br>距上次开始 24 天</div>
        </div>
        <div class="cycle">
          <div class="d"><div class="dd">29</div><div class="dm">9 月 · 2026</div></div>
          <div class="body">
            <div class="t">9 月 29 日 – 10 月 3 日</div>
            <div class="s">首次记录</div>
          </div>
          <div class="r">持续 5 天<br>无上一次</div>
        </div>
      </div>

      <div class="note" style="margin-top:12px">
        持续天数包含开始日和最后一天；周期长度按相邻两次开始日计算。结束日期可以事后补记。
      </div>
    </section>

    <section class="section">
      <div class="hintbox">
        历史只展示已保存的经期与感受。记录感受不会新建一段经期；删除经期也不会连带删除当天的感受。
      </div>
    </section>
"""

period_prediction = """
    <section class="section" style="margin-top:8px">
      <div class="card">
        <div class="meta">预计下次开始</div>
        <div class="pred">12 月 12 日</div>
        <div style="display:flex;gap:6px;margin-top:8px;flex-wrap:wrap">
          <span class="tag">按最近 3 次记录估算</span>
          <span class="tag plain">估算周期 25 天</span>
        </div>
        <div class="note" style="margin-top:10px">
          根据历史记录估算，实际日期可能不同，不作为避孕依据。
        </div>
      </div>
    </section>

    <section class="section">
      <div class="section-head"><h2 class="h2">怎么算的</h2><span class="meta">最近 3 次开始</span></div>
      <div class="card">
        <div class="drow"><span class="lab">9 月 29 日 → 10 月 23 日</span><span class="val">24 天</span></div>
        <div class="drow"><span class="lab">10 月 23 日 → 11 月 17 日</span><span class="val">25 天</span></div>
        <div class="drow"><span class="lab">两个周期取平均（24.5）</span><span class="val">25 天</span></div>
        <div class="drow"><span class="lab">11 月 17 日 + 25 天</span><span class="val">12 月 12 日</span></div>
      </div>
      <div class="note" style="margin-top:10px">
        当前只有 2 个完整周期，按平均值四舍五入；若有 3 个周期，则取中间值。
      </div>
    </section>

    <section class="section">
      <div class="section-head"><h2 class="h2">预测规则</h2></div>
      <div class="card">
        <div class="rule"><span class="n">1</span><div><b>至少 3 次开始记录</b>才显示预计日期；不足时不猜。</div></div>
        <div class="rule"><span class="n">2</span><div>取最近最多 <b>4 次</b>开始记录，计算 2–3 个周期。</div></div>
        <div class="rule"><span class="n">3</span><div>最长与最短周期相差 <b>超过 7 天</b>时不显示预测。</div></div>
        <div class="rule"><span class="n">4</span><div>只有<b>开始日期变化</b>才重新计算；补记结束日不影响预测。</div></div>
      </div>
    </section>

    <section class="section">
      <div class="section-head"><h2 class="h2">其他状态</h2></div>
      <div class="card">
        <div class="lrow"><div><div class="t">记录不足</div><div class="s">开始记录少于 3 次</div></div><span class="tag plain">不显示日期</span></div>
        <div class="lrow"><div><div class="t">波动过大</div><div class="s">最长与最短相差超过 7 天</div></div><span class="tag plain">不显示日期</span></div>
        <div class="lrow"><div><div class="t">已过预计日</div><div class="s">今天已超过预计开始日</div></div><span class="tag">提示已过</span></div>
      </div>
      <div class="note" style="margin-top:10px">预计日不会被视作实际经期，日历上只画虚线描边。</div>
    </section>
"""
write("period-history", shell("历史回顾", "经期 / RECORDS", "历史回顾",
                              "按开始日期倒序 · 共 3 段", period_history, "period.html"))
write("period-prediction", shell("预测说明", "经期 / PREDICTION", "预测说明",
                                "预计下次开始 12 月 12 日 · 按近 3 次记录估算",
                                period_prediction, "period.html"))


# =====================================================================
# 体重
# =====================================================================
weight_detail = """
    <section class="section" style="margin-top:8px">
      <div class="chips">
        <span class="chip on">全部 8 笔</span>
        <span class="chip">近 30 天</span>
        <span class="chip">近 7 天</span>
      </div>
    </section>

    <section class="section">
      <div class="card">
        <div class="lrow"><div><div class="t">58.2 kg</div><div class="s">11 月 19 日 07:20 · 晨起空腹</div></div><div class="r"><a class="link" href="#">编辑</a></div></div>
        <div class="lrow"><div><div class="t">58.4 kg</div><div class="s">11 月 17 日 07:10 · 晨起空腹</div></div><div class="r"><a class="link" href="#">编辑</a></div></div>
        <div class="lrow"><div><div class="t">58.5 kg</div><div class="s">11 月 16 日 07:05</div></div><div class="r"><a class="link" href="#">编辑</a></div></div>
        <div class="lrow"><div><div class="t">58.4 kg</div><div class="s">11 月 11 日 07:20 · 晨起空腹</div></div><div class="r"><a class="link" href="#">编辑</a></div></div>
        <div class="lrow"><div><div class="t">58.9 kg</div><div class="s">11 月 4 日 21:10 · 餐后</div></div><div class="r"><a class="link" href="#">编辑</a></div></div>
        <div class="lrow"><div><div class="t">58.6 kg</div><div class="s">10 月 28 日 07:30</div></div><div class="r"><a class="link" href="#">编辑</a></div></div>
      </div>
      <div class="note" style="margin-top:10px">只展示最近 6 笔，共 8 笔。同日多笔全部保留。</div>
    </section>

    <section class="section">
      <div class="hintbox">
        编辑会改动这一笔的数值、时间与标签；删除只移除当前一笔。趋势与统计按“每天最后一次测量”重新计算。
      </div>
    </section>
"""

weight_trend = """
    <section class="section" style="margin-top:8px">
      <div class="section-head">
        <h2 class="h2">近 30 天</h2>
        <div class="segmented"><button>7 天</button><button class="on">30 天</button><button>90 天</button></div>
      </div>

      <div class="card">
        <div class="chart">
          <svg viewBox="0 0 326 170" role="img" aria-label="近 30 天体重趋势，选中 11 月 11 日">
            <defs>
              <linearGradient id="area2" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0" stop-color="#FBE2E6" stop-opacity="0.92"/>
                <stop offset="1" stop-color="#FBE2E6" stop-opacity="0"/>
              </linearGradient>
            </defs>
            <line x1="0" y1="20" x2="326" y2="20" stroke="#F2EAF1" stroke-width="1"/>
            <line x1="0" y1="73" x2="326" y2="73" stroke="#F2EAF1" stroke-width="1"/>
            <line x1="0" y1="126" x2="326" y2="126" stroke="#F2EAF1" stroke-width="1"/>

            <path d="M20 60 L50.8 72 L91.6 49 L142.6 86 L193.6 98 L234.4 72 L285.4 96 L316 108 L316 170 L20 170 Z" fill="url(#area2)"/>
            <path d="M20 60 L50.8 72 L91.6 49 L142.6 86 L193.6 98 L234.4 72 L285.4 96 L316 108"
                  fill="none" stroke="#C0566B" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>

            <circle cx="20" cy="60" r="3" fill="#FFFFFF" stroke="#C0566B" stroke-width="1.6"/>
            <circle cx="50.8" cy="72" r="3" fill="#FFFFFF" stroke="#C0566B" stroke-width="1.6"/>
            <circle cx="91.6" cy="49" r="3" fill="#FFFFFF" stroke="#C0566B" stroke-width="1.6"/>
            <circle cx="142.6" cy="86" r="3" fill="#FFFFFF" stroke="#C0566B" stroke-width="1.6"/>
            <circle cx="193.6" cy="98" r="3" fill="#FFFFFF" stroke="#C0566B" stroke-width="1.6"/>
            <circle cx="234.4" cy="72" r="3" fill="#FFFFFF" stroke="#C0566B" stroke-width="1.6"/>

            <line x1="285.4" y1="16" x2="285.4" y2="108" stroke="#C0566B" stroke-width="1" stroke-dasharray="3 4" opacity=".55"/>
            <circle cx="285.4" cy="96" r="6" fill="#C0566B"/>
            <circle cx="285.4" cy="96" r="2.4" fill="#FFFFFF"/>

            <circle cx="316" cy="108" r="3" fill="#FFFFFF" stroke="#C0566B" stroke-width="1.6"/>
          </svg>
          <div class="axis">
            <span>10/21</span><span>10/28</span><span>11/4</span><span>11/11</span><span>11/19</span>
          </div>
        </div>

        <div class="card flat tight" style="margin-top:10px">
          <div class="lrow" style="padding:2px 0">
            <div><div class="t">11 月 11 日 · 58.4 kg</div><div class="s">07:20 · 晨起空腹</div></div>
            <span class="tag">已选数据点</span>
          </div>
        </div>

        <div class="stat3">
          <div class="it"><div class="n">8</div><div class="k">记录次数</div></div>
          <div class="it"><div class="n">−0.4</div><div class="k">首尾变化 kg</div></div>
          <div class="it"><div class="n">8</div><div class="k">数据点</div></div>
        </div>

        <div class="chart-foot" style="margin-top:10px">
          <span class="chart-note">10/21 – 11/19</span>
          <span class="chart-note">每天取最后一次测量</span>
        </div>
      </div>
    </section>

    <section class="section">
      <div class="card advice">
        <span class="ad-ic">
          <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="#C0566B" stroke-width="1.7" stroke-linecap="round">
            <circle cx="8" cy="8" r="6.2"/><path d="M8 7.2v4"/><circle cx="8" cy="4.9" r="0.8" fill="#C0566B" stroke="none"/>
          </svg>
        </span>
        <p>如果想比较长期变化，尽量在相近的时间和条件下称重；单次波动不代表趋势。</p>
      </div>
      <div class="note" style="margin-top:10px">缺测日期不补 0、不虚构数据点；不对单次涨跌评好坏。</div>
    </section>
"""
write("weight-detail", shell("记录明细", "体重 / DETAIL", "记录明细",
                             "共 8 笔 · 同日多笔全部保留", weight_detail, "weight.html"))
write("weight-trend", shell("趋势详情", "体重 / TREND", "趋势详情",
                            "近 30 天 · 点击数据点查看单次测量", weight_trend, "weight.html"))


# =====================================================================
# 皮肤
# =====================================================================
skin_capture = """
    <section class="section" style="margin-top:8px">
      <div class="steps"><span class="step on"></span><span class="step"></span><span class="step"></span></div>
      <div class="meta" style="margin-top:8px">第 1 步，共 3 步 · 选择部位 → 拍照 → 确认发送</div>
    </section>

    <section class="section">
      <div class="section-head"><h2 class="h2">选择部位</h2><span class="meta">一次只观察一个部位</span></div>
      <div class="card">
        <div class="chips" style="margin-top:0">
          <span class="chip on">面部 · 左颊</span>
          <span class="chip">面部 · 右颊</span>
          <span class="chip">额头</span>
          <span class="chip">下巴</span>
          <span class="chip">颈部</span>
          <span class="chip">手部</span>
          <span class="chip">其他</span>
        </div>
        <div class="note" style="margin-top:10px">之后对比两次观察时，只能选择同一部位的记录。</div>
      </div>
    </section>

    <section class="section">
      <div class="section-head"><h2 class="h2">拍摄提示</h2></div>
      <div class="card">
        <div class="rule"><span class="n">1</span><div><b>自然光</b>，不要开闪光灯或暖色台灯。</div></div>
        <div class="rule"><span class="n">2</span><div><b>同一角度</b>，手机与部位保持约 20 厘米。</div></div>
        <div class="rule"><span class="n">3</span><div><b>关闭美颜与滤镜</b>，不要裁剪或涂抹。</div></div>
      </div>
    </section>

    <section class="section">
      <div class="mock camera">
        <svg width="44" height="44" viewBox="0 0 24 24" fill="none" stroke="rgba(122,78,88,.45)" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">
          <rect x="3.2" y="6.2" width="17.6" height="13.6" rx="3"/>
          <circle cx="12" cy="13" r="3.9"/>
          <path d="M8.4 6.2 9.6 4.2h4.8l1.2 2"/>
        </svg>
        <span class="big" style="position:absolute;bottom:14px">拍照或从相册选择</span>
      </div>
      <div class="note" style="margin-top:10px">
        照片会在你确认后发送至模型服务，仅用于本次观察；不保存或重拍不会新增记录。
      </div>
    </section>

    <section class="section">
      <a class="btn block" href="skin-result.html">拍照</a>
      <a class="btn ghost block" href="skin-result.html" style="margin-top:10px">从相册选择</a>
    </section>
"""

skin_result = """
    <section class="section" style="margin-top:8px">
      <div class="mock photo16">
        <svg width="42" height="42" viewBox="0 0 24 24" fill="none" stroke="rgba(122,78,88,.42)" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">
          <rect x="3.2" y="6.2" width="17.6" height="13.6" rx="3"/>
          <circle cx="12" cy="13" r="3.9"/>
          <path d="M8.4 6.2 9.6 4.2h4.8l1.2 2"/>
        </svg>
        <span class="lbl">示例照片 · 面部左颊</span>
      </div>
      <div style="display:flex;gap:6px;margin-top:10px;flex-wrap:wrap">
        <span class="tag">AI 观察</span>
        <span class="tag plain">未保存</span>
        <span class="meta">11 月 16 日 21:04</span>
      </div>
    </section>

    <section class="section">
      <div class="card">
        <div class="obs-sections" style="margin-top:0">
          <div class="obs-block">
            <div class="k">照片中可见</div>
            <div class="v">左颊有一处淡红色区域，边界较柔和，附近皮肤平整。</div>
          </div>
          <div class="obs-block">
            <div class="k">看不清的地方</div>
            <div class="v">拍摄时光线偏暗，毛孔与细纹的细节不容易分辨。</div>
          </div>
          <div class="obs-block">
            <div class="k">下次可留意</div>
            <div class="v">在自然光下、同一角度再拍一张，方便和这次对照。</div>
          </div>
        </div>

        <div class="chips">
          <span class="chip">淡红色区域</span>
          <span class="chip">边界柔和</span>
          <span class="chip">光线偏暗</span>
        </div>

        <div class="note" style="margin-top:12px">
          以上为模型生成的观察文字，不构成诊断；不显示病名、严重度或改善百分比。
        </div>
      </div>
    </section>

    <section class="section">
      <a class="btn block" href="skin-history.html">保存到历史</a>
      <div style="display:flex;gap:8px;margin-top:10px">
        <a class="btn ghost" href="skin.html" style="flex:1">不保存</a>
        <a class="btn soft" href="skin-capture.html" style="flex:1">重拍</a>
      </div>
      <div class="note" style="margin-top:10px;text-align:center">只有点「保存」才会写入历史；其余两项不新增记录。</div>
    </section>
"""

skin_history = """
    <section class="section" style="margin-top:8px">
      <div style="display:flex;align-items:center;justify-content:space-between;gap:10px">
        <span class="meta">共 6 次 · 面部左颊 4 次</span>
        <a class="btn soft sm" href="skin-compare.html">选择两次对比</a>
      </div>
    </section>

    <section class="section">
      <div class="card" style="padding-top:4px;padding-bottom:4px">
        <div class="lrow" style="align-items:flex-start">
          <div style="display:flex;gap:10px;min-width:0">
            <div class="mock thumb"><span class="lbl">11/16</span></div>
            <div style="min-width:0">
              <div class="t">11 月 16 日 · 面部左颊</div>
              <div class="s">左颊淡红色区域，边界较柔和…</div>
              <span class="tag" style="margin-top:6px">AI 观察</span>
            </div>
          </div>
          <div class="r">21:04 {chev}</div>
        </div>
        <div class="lrow" style="align-items:flex-start">
          <div style="display:flex;gap:10px;min-width:0">
            <div class="mock thumb"><span class="lbl">10/28</span></div>
            <div style="min-width:0">
              <div class="t">10 月 28 日 · 面部左颊</div>
              <div class="s">肤色整体均匀，颊部有一处浅色…</div>
              <span class="tag" style="margin-top:6px">AI 观察</span>
            </div>
          </div>
          <div class="r">19:40 {chev}</div>
        </div>
        <div class="lrow" style="align-items:flex-start">
          <div style="display:flex;gap:10px;min-width:0">
            <div class="mock thumb"><span class="lbl">10/12</span></div>
            <div style="min-width:0">
              <div class="t">10 月 12 日 · 面部左颊</div>
              <div class="s">光线偏暗，毛孔细节不易分辨…</div>
              <span class="tag" style="margin-top:6px">AI 观察</span>
            </div>
          </div>
          <div class="r">20:15 {chev}</div>
        </div>
      </div>
      <div class="note" style="margin-top:10px">
        照片仅本人可见。对比只使用已保存的文字观察，不会重新发送照片。
      </div>
    </section>

    <section class="section">
      <a class="btn block" href="skin-capture.html">再拍一次</a>
    </section>
"""

skin_compare = """
    <section class="section" style="margin-top:8px">
      <div class="cmp">
        <div>
          <div class="mock"><span class="lbl">11/16</span></div>
          <div class="cmp-date">11 月 16 日 21:04</div>
        </div>
        <div>
          <div class="mock"><span class="lbl">10/28</span></div>
          <div class="cmp-date">10 月 28 日 19:40</div>
        </div>
      </div>
      <div style="text-align:center;margin-top:10px"><span class="tag">面部 · 左颊 · 同一部位</span></div>
    </section>

    <section class="section">
      <div class="card">
        <div class="meta">11 月 16 日的观察</div>
        <div class="obs-block" style="margin-top:8px">
          <div class="v">左颊有一处淡红色区域，边界较柔和，附近皮肤平整；光线偏暗，毛孔细节看不清。</div>
        </div>
      </div>
      <div class="card">
        <div class="meta">10 月 28 日的观察</div>
        <div class="obs-block" style="margin-top:8px">
          <div class="v">肤色整体均匀，颊部有一处浅色区域，未提及明显泛红；拍摄光线较充足。</div>
        </div>
      </div>
    </section>

    <section class="section">
      <div class="card">
        <div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap">
          <span class="tag">基于两次文字观察</span>
          <span class="meta">未重新分析照片</span>
        </div>
        <div class="obs-block" style="margin-top:10px">
          <div class="k">两次都提到的</div>
          <div class="v">左颊同一位置有浅色或淡红色区域，边界都较柔和。</div>
        </div>
        <div class="obs-block">
          <div class="k">只有一次提到的</div>
          <div class="v">10 月 28 日未提到泛红，11 月 16 日提到淡红色；光线条件也不同。</div>
        </div>
        <div class="note" style="margin-top:10px">
          对比只依据两次已保存的文字，某次未提及一种现象，不代表它不存在；不构成诊断。
        </div>
      </div>
    </section>

    <section class="section">
      <a class="btn ghost block" href="skin-history.html">重新选择</a>
    </section>
"""

write("skin-capture", shell("拍照分析", "皮肤 / CAPTURE", "拍照分析",
                            "选择部位 → 拍照 → 确认发送", skin_capture, "skin.html"))
write("skin-result", shell("分析结果", "皮肤 / RESULT", "分析结果",
                           "11 月 16 日 21:04 · 面部左颊", skin_result, "skin.html"))
write("skin-history", shell("历史观察", "皮肤 / HISTORY", "历史观察",
                            "共 6 次 · 同一部位可对比", skin_history.replace("{chev}", chev()), "skin.html"))
write("skin-compare", shell("两次对比", "皮肤 / COMPARE", "两次对比",
                            "面部 · 左颊 · 11 月 16 日 / 10 月 28 日", skin_compare, "skin-history.html"))


# =====================================================================
# 我的 / 设置
# =====================================================================
settings = """
    <section class="section" style="margin-top:8px">
      <div class="section-head"><h2 class="h2">账号</h2></div>
      <div class="card" style="padding-top:4px;padding-bottom:4px">
        <div class="lrow"><div><div class="t">用户名</div><div class="s">注册后不可修改，用于登录</div></div><div class="r">lin_xiaoyu</div></div>
        <a class="set-row" href="me.html"><span class="t">个人资料</span><span class="r">生日、身高、电话 ›</span></a>
        <div class="lrow"><div><div class="t">登录状态</div><div class="s">当前设备已登录</div></div><span class="tag">已登录</span></div>
      </div>
    </section>

    <section class="section">
      <div class="section-head"><h2 class="h2">数据与隐私</h2></div>
      <div class="card" style="padding-top:4px;padding-bottom:4px">
        <a class="set-row" href="privacy.html"><span class="t">数据与隐私</span><span class="r">记录归属、照片与 AI ›</span></a>
      </div>
    </section>

    <section class="section">
      <div class="section-head"><h2 class="h2">关于</h2></div>
      <div class="card" style="padding-top:4px;padding-bottom:4px">
        <a class="set-row" href="about.html"><span class="t">关于她记</span><span class="r">版本 1.0.0 ›</span></a>
      </div>
    </section>

    <section class="section">
      <a class="btn ghost block" href="login.html">退出登录</a>
      <div class="note" style="margin-top:10px;text-align:center">退出后账号与健康记录仍保留，重新登录即可查看。</div>
    </section>
"""

privacy = """
    <section class="section" style="margin-top:8px">
      <div class="card">
        <div class="obs-sections" style="margin-top:0">
          <div class="obs-block">
            <div class="k">记录属于你</div>
            <div class="v">经期、体重、皮肤记录按账号隔离；退出登录不会删除，其他账号不能读取。</div>
          </div>
          <div class="obs-block">
            <div class="k">照片与 AI</div>
            <div class="v">皮肤照片只在你确认后发送给模型服务，用于本次观察；只有点保存才写入历史。</div>
          </div>
          <div class="obs-block">
            <div class="k">首页问答</div>
            <div class="v">只读取与问题相关的已保存记录；不发送皮肤原图，不发送电话，不替你填写或修改记录。</div>
          </div>
          <div class="obs-block">
            <div class="k">账号注销</div>
            <div class="v">本版不提供永久注销入口；如需删除账号，请通过后续正式版本提供的渠道处理。</div>
          </div>
        </div>
      </div>
    </section>

    <section class="section">
      <div class="hintbox">
        一句话边界：记录用来看趋势，照片用来做参考观察；两者都不替代医生的诊断与建议。
      </div>
    </section>

    <section class="section">
      <div class="section-head"><h2 class="h2">你可以随时</h2></div>
      <div class="card" style="padding-top:4px;padding-bottom:4px">
        <div class="lrow"><div class="t">退出登录</div><div class="r">记录保留</div></div>
        <div class="lrow"><div class="t">删除某一天的感受</div><div class="r">不影响经期日期</div></div>
        <div class="lrow"><div class="t">删除某一段经期</div><div class="r">不影响当天感受</div></div>
        <div class="lrow"><div class="t">删除某一笔体重</div><div class="r">趋势重新计算</div></div>
        <div class="lrow"><div class="t">删除某次皮肤观察</div><div class="r">照片一并移除</div></div>
      </div>
      <div class="note" style="margin-top:10px">以上删除均需二次确认；本版不做批量导出。</div>
    </section>
"""

about = """
    <section class="section" style="margin-top:14px">
      <div style="text-align:center">
        <img src="assets/app-icon.svg" alt="她记图标" style="width:74px;height:74px;margin:0 auto 12px">
        <div style="font-size:20px;font-weight:600;letter-spacing:1px">她记 HerLog</div>
        <div class="meta" style="margin-top:4px">版本 1.0.0 · 2026 年 11 月</div>
      </div>
    </section>

    <section class="section">
      <div class="card">
        <div class="obs-block">
          <div class="k">她记是什么</div>
          <div class="v">一本私人的健康记录：记经期、记体重、拍一张皮肤照片做参考观察，再用自己的记录回答问题。</div>
        </div>
      </div>
      <div class="card">
        <div class="obs-block">
          <div class="k">不做什么</div>
          <div class="v">不提供诊断、病名、严重度或改善百分比；不推荐药物；不把预计日期当作避孕依据。</div>
        </div>
      </div>
    </section>

    <section class="section">
      <div class="card">
        <div class="h2" style="font-size:16px;margin-bottom:8px">免责声明</div>
        <div class="rule"><span class="n">·</span><div>本应用不是医疗器械，所有内容仅供个人记录与参考。</div></div>
        <div class="rule"><span class="n">·</span><div>经期预测为历史估算，实际日期可能不同，不作为避孕依据。</div></div>
        <div class="rule"><span class="n">·</span><div>皮肤观察为模型生成的文字描述，不构成诊断；如有不适请就医。</div></div>
      </div>
      <div class="note" style="margin-top:10px">
        演示用插画来自公开素材平台，仅用于本次界面演示；正式上线前会替换为有授权的品牌素材。
      </div>
    </section>
"""

write("settings", shell("设置", "我的 / SETTINGS", "设置", "账号、数据与关于", settings, "me.html"))
write("privacy", shell("数据与隐私", "我的 / PRIVACY", "数据与隐私", "记录、照片与 AI 的边界", privacy, "settings.html"))
write("about", shell("关于她记", "我的 / ABOUT", "关于她记", "私人健康记录，不做诊断", about, "settings.html"))


# =====================================================================
# 登录 / 注册
# =====================================================================
def auth_page(title, heading, sub, fields, btn, foot, note):
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
<body class="auth">
<div class="screen">
  <header class="hero auth-hero">
    <img class="auth-logo" src="assets/app-icon.svg" alt="她记">
    <div class="auth-title">{heading}</div>
    <div class="auth-sub">{sub}</div>
  </header>

  <main class="main">
    <div class="card auth-card">
      {fields}
      <button class="btn block" style="margin-top:20px">{btn}</button>
      {note}
    </div>
    <div class="auth-foot">{foot}</div>
  </main>
</div>
</body>
</html>
"""


login = auth_page(
    "登录", "欢迎回来", "用账号继续记录今天",
    """<div class="field" style="margin-top:0">
          <label>用户名</label>
          <div class="control">lin_xiaoyu</div>
        </div>
        <div class="field">
          <label>密码</label>
          <div class="control" style="justify-content:space-between">
            <span>••••••••</span>
            <span style="font-size:12px;color:#C0566B">显示</span>
          </div>
        </div>""",
    "登录",
    "还没有账号？<a href=\"register.html\">注册</a>",
    """<div class="auth-note">登录后才能查看你的记录；退出登录不会删除数据。</div>"""
)

register = auth_page(
    "注册", "创建账号", "记录只属于这个账号",
    """<div class="field" style="margin-top:0">
          <label>用户名</label>
          <div class="control">lin_xiaoyu</div>
          <div class="hint">4–20 位字母、数字或下划线；注册后不可修改。</div>
        </div>
        <div class="field">
          <label>密码</label>
          <div class="control">••••••••</div>
        </div>
        <div class="field">
          <label>确认密码</label>
          <div class="control">••••••••</div>
          <div class="hint">两次输入需一致。</div>
        </div>""",
    "注册",
    "已有账号？<a href=\"login.html\">登录</a>",
    """<div class="auth-note">注册成功后将返回登录页，不会自动登录。</div>"""
)

write("login", login)
write("register", register)


# =====================================================================
# 半屏表单（叠在一级页上）
# =====================================================================
def overlay(base, out, sheet, cls):
    s = (OUT / (base + ".html")).read_text(encoding="utf-8")
    s = s.replace('<body class="p-%s">' % base, '<body class="p-%s %s">' % (base, cls))
    s = s.replace('<div class="screen">', '<div class="screen fixed">', 1)
    s = s.replace("\n</div>\n</body>", "\n" + sheet + "\n</div>\n</body>")
    (OUT / (out + ".html")).write_text(s, encoding="utf-8")
    print("wrote", out)


period_record_sheet = """
<div class="scrim"></div>
<section class="sheet">
  <div class="grab"></div>
  <div class="sheet-head">
    <div><div class="sheet-title">记录经期</div><div class="sheet-sub">11 月 19 日 · 星期四</div></div>
    <button class="sheet-x" aria-label="关闭">✕</button>
  </div>
  <div class="sheet-body">
    <div class="segmented" style="display:flex;width:100%">
      <button style="flex:1">经期开始</button>
      <button class="on" style="flex:1">经期最后一天</button>
    </div>

    <div class="drow" style="margin-top:8px"><span class="lab">开始日期</span><span class="val">11 月 17 日</span></div>
    <div class="drow"><span class="lab">最后一天</span><span class="val">11 月 19 日</span></div>
    <div class="drow"><span class="lab">持续天数</span><span class="val">3 天</span></div>

    <div class="hintbox">
      11 月 19 日已在 11 月 17 日开始的一段经期内。选择「经期开始」会与已有记录重叠，App 会提示检查，不会自动覆盖。
    </div>
    <div class="note" style="margin-top:10px">持续天数包含开始日和最后一天；结束日期可以事后补记。</div>
    <a class="danger-link" href="#">删除本段经期</a>
  </div>
  <div class="sheet-foot"><button class="btn block">保存</button></div>
</section>
"""

period_feel_sheet = """
<div class="scrim"></div>
<section class="sheet">
  <div class="grab"></div>
  <div class="sheet-head">
    <div><div class="sheet-title">记录感受</div><div class="sheet-sub">11 月 19 日 · 经期第 3 天</div></div>
    <button class="sheet-x" aria-label="关闭">✕</button>
  </div>
  <div class="sheet-body">
    <div class="slabel" style="margin-top:4px">经量</div>
    <div class="chips"><span class="chip">少</span><span class="chip on">中</span><span class="chip">多</span></div>

    <div class="slabel">腹痛</div>
    <div class="chips"><span class="chip">无</span><span class="chip on">轻微</span><span class="chip">明显</span></div>

    <div class="slabel">其他不适</div>
    <div class="chips"><span class="chip">腹胀</span><span class="chip">头痛</span><span class="chip on">疲惫</span><span class="chip">腰酸</span></div>

    <div class="slabel">情绪变化（选填）</div>
    <div class="chips"><span class="chip">平稳</span><span class="chip">烦躁</span><span class="chip">低落</span><span class="chip">波动</span></div>

    <div class="slabel">生活影响（选填）</div>
    <div class="chips"><span class="chip on">无</span><span class="chip">影响工作</span><span class="chip">影响睡眠</span></div>

    <div class="slabel">备注</div>
    <div class="ta">下午开始腰酸，睡了 20 分钟。</div>

    <div class="note" style="margin-top:10px">只填一项也能保存。感受与经期日期分开，单独记录感受不会新建一段经期。</div>
  </div>
  <div class="sheet-foot"><button class="btn block">保存感受</button></div>
</section>
"""

weight_record_sheet = """
<div class="scrim"></div>
<section class="sheet">
  <div class="grab"></div>
  <div class="sheet-head">
    <div><div class="sheet-title">记体重</div><div class="sheet-sub">11 月 19 日 · 星期四</div></div>
    <button class="sheet-x" aria-label="关闭">✕</button>
  </div>
  <div class="sheet-body">
    <div class="wval"><span class="n">58.2</span><span class="u">kg</span></div>
    <div class="drow" style="padding-top:0"><span class="lab">测量时间</span><span class="val">今天 07:20 <span style="font-weight:400;color:#655966;font-size:12px">修改</span></span></div>

    <div class="slabel">标签（选填）</div>
    <div class="chips"><span class="chip on">晨起空腹</span><span class="chip">餐前</span><span class="chip">餐后</span><span class="chip">运动后</span></div>

    <div class="keypad">
      <button class="key">1</button><button class="key">2</button><button class="key">3</button>
      <button class="key">4</button><button class="key">5</button><button class="key">6</button>
      <button class="key">7</button><button class="key">8</button><button class="key">9</button>
      <button class="key fn">.</button><button class="key">0</button><button class="key fn">⌫</button>
    </div>

    <div class="note" style="margin-top:8px">单位固定 kg；同日多笔全部保留，趋势只取每天最后一次。</div>
  </div>
  <div class="sheet-foot"><button class="btn block">保存</button></div>
</section>
"""

overlay("period", "period-record", period_record_sheet, "sheet-page")
overlay("period", "period-feelings", period_feel_sheet, "sheet-page")
overlay("weight", "weight-record", weight_record_sheet, "sheet-page")

print("all secondary pages done")
