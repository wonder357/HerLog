# -*- coding: utf-8 -*-
from pathlib import Path

OUT = Path(r"C:\Users\kunlunmeta\my-first-project\豆包\业务全量稿")
p = OUT / "period-history.html"
s = p.read_text(encoding="utf-8")
s = s.replace('''            <div class="t">11 月 17 日开始 <span class="tag">进行中</span></div>
            <div class="s">未记录结束 · 已记录 3 天</div>
          </div>
          <div class="r">持续 3 天（至今）<br>距上次开始 25 天</div>''',
              '''            <div class="t">11 月 17 日开始 <span class="tag">进行中</span></div>
            <div class="s">未记录结束 · 已记录 3 天</div>
            <div class="s">距上次开始 25 天</div>
          </div>
          <div class="r">持续 3 天<br>（至今）</div>''')
s = s.replace('''            <div class="t">10 月 23 日 – 27 日</div>
            <div class="s">已记录结束日</div>
          </div>
          <div class="r">持续 5 天<br>距上次开始 24 天</div>''',
              '''            <div class="t">10 月 23 日 – 27 日</div>
            <div class="s">已记录结束日 · 距上次 24 天</div>
          </div>
          <div class="r">持续 5 天</div>''')
s = s.replace('''            <div class="t">9 月 29 日 – 10 月 3 日</div>
            <div class="s">首次记录</div>
          </div>
          <div class="r">持续 5 天<br>无上一次</div>''',
              '''            <div class="t">9 月 29 日 – 10 月 3 日</div>
            <div class="s">首次记录</div>
          </div>
          <div class="r">持续 5 天</div>''')
p.write_text(s, encoding="utf-8")
print("ok")
