<script setup lang="ts">
import { onLaunch, onShow } from '@dcloudio/uni-app'
import { useAuthStore } from './stores/auth'

onLaunch(() => {
  // 底栏由 components/TabBar.vue 绘制，这里隐藏原生 tabBar 避免出现两条。
  uni.hideTabBar({ animation: false, fail: () => undefined })
  const auth = useAuthStore()
  auth.restore()
  if (!auth.isLoggedIn) {
    uni.reLaunch({ url: '/pages/login/index' })
  }
})

onShow(() => {
  uni.hideTabBar({ animation: false, fail: () => undefined })
})
</script>

<style>
/* ============================================================
   她记 · 蜜桃奶油主题
   令牌与材质取自 豆包/业务全量稿/theme.css + 前端样式/styles.css
   ============================================================ */
:root,
page {
  --page: #fdf6f1;
  --surface: #ffffff;
  --berry: #c0566b;
  --berry-deep: #9c3b50;
  --berry-soft: #fbe2e6;
  --berry-pink: #f2b4bc;
  --ink: #3b2a2d;
  --ink-2: #7b6367;
  --line: #f4e5e1;
  --outline: #9c8285;
  --error: #a32638;

  --hero-grad: radial-gradient(120% 95% at 84% 0%, #ffd8c0 0%, rgba(255, 216, 192, 0) 58%),
    radial-gradient(85% 70% at 6% 12%, #ffe4ec 0%, rgba(255, 228, 236, 0) 62%),
    linear-gradient(168deg, #ffe7d2 0%, #f7cddc 52%, #fdf6f1 100%);
  --page-grad: linear-gradient(180deg, #fdf6f1 0%, #fcf2ea 100%);
  --card-grad: linear-gradient(180deg, #ffffff 0%, #fff9f6 100%);
  --card-line: #f6e6e2;
  --card-shadow: 0 12px 28px -14px rgba(192, 86, 107, 0.28);
  --btn-grad: linear-gradient(135deg, #d6788b 0%, #bd5266 100%);
  --btn-shadow: rgba(192, 86, 107, 0.4);
  --tabon-grad: linear-gradient(135deg, #fde7ea 0%, #fadde8 100%);
  --soft-grad: linear-gradient(135deg, #fbe2e6 0%, #fff0f2 100%);
  --segbg: #fbedea;
  --ghost-line: #efd3d8;
  --chip-2: #fff8f6;
  --input-2: #fffcfa;
  --readonly: #f8efec;
  --avatar-grad: linear-gradient(140deg, #fce3e6, #fbe7dc);
  --photo-grad: radial-gradient(120% 120% at 30% 20%, #f8ded4, #efcbbf);
  --glow: rgba(255, 236, 224, 0.85);
}

page {
  min-height: 100vh;
  background-color: #fdf6f1;
  color: var(--ink);
  font-size: 15px;
  line-height: 1.6;
  font-family: -apple-system, BlinkMacSystemFont, 'PingFang SC', 'Microsoft YaHei',
    'Segoe UI', Roboto, sans-serif;
  -webkit-font-smoothing: antialiased;
}

/* ---------- 页面容器 ---------- */
.page {
  min-height: 100vh;
  background: var(--page-grad);
  padding-bottom: calc(96px + constant(safe-area-inset-bottom));
  padding-bottom: calc(96px + env(safe-area-inset-bottom));
  box-sizing: border-box;
}
.page.plain-bottom {
  padding-bottom: calc(28px + env(safe-area-inset-bottom));
}
.main {
  padding: 0 16px;
  box-sizing: border-box;
}
.section {
  margin-top: 24px;
}

/* ---------- 页首 ---------- */
.hero {
  position: relative;
  overflow: hidden;
  padding: calc(22px + var(--status-bar-height, 0px)) 16px 20px;
  background: linear-gradient(180deg, rgba(255, 255, 255, 0) 56%, var(--page) 100%),
    var(--hero-grad);
  box-sizing: border-box;
}
.hero::before {
  content: '';
  position: absolute;
  right: -80px;
  top: -110px;
  width: 260px;
  height: 260px;
  border-radius: 50%;
  background: radial-gradient(circle at 50% 50%, var(--glow) 0%, rgba(255, 255, 255, 0) 70%);
  pointer-events: none;
}
.hero > * {
  position: relative;
  z-index: 1;
}
.h-date {
  font-size: 13px;
  line-height: 20px;
  color: var(--ink-2);
  letter-spacing: 0.3px;
}
.h-title {
  margin-top: 6px;
  font-size: 24px;
  line-height: 32px;
  font-weight: 600;
  letter-spacing: 1px;
  color: var(--ink);
}
.h-sub {
  margin-top: 6px;
  font-size: 13px;
  line-height: 20px;
  color: var(--ink-2);
}
.h-status {
  margin-top: 10px;
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
}

/* ---------- 卡片 ---------- */
.card {
  position: relative;
  background: var(--card-grad);
  border: 1px solid var(--card-line);
  border-radius: 12px;
  padding: 16px;
  margin-bottom: 12px;
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.9), var(--card-shadow);
  box-sizing: border-box;
}
.card.tight {
  padding: 12px 16px;
}

/* ---------- 按钮 ---------- */
button.btn,
.btn {
  height: 48px;
  padding: 0 22px;
  border: 0;
  border-radius: 999px;
  background: var(--btn-grad);
  color: #ffffff;
  font-size: 16px;
  line-height: 1;
  font-weight: 600;
  letter-spacing: 0.5px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  box-shadow: 0 12px 24px -10px var(--btn-shadow), inset 0 1px 0 rgba(255, 255, 255, 0.3);
}
button.btn::after {
  border: none;
}
button.btn:active {
  filter: brightness(0.94);
}
button.btn[disabled] {
  opacity: 0.55;
  box-shadow: none;
}
.btn.block {
  width: 100%;
}
.btn.ghost {
  background: linear-gradient(180deg, #ffffff 0%, #fff7f8 100%);
  color: var(--berry);
  border: 1px solid var(--ghost-line);
  box-shadow: 0 6px 16px -12px var(--btn-shadow);
}
.btn.soft {
  background: var(--soft-grad);
  color: var(--berry-deep);
  box-shadow: 0 6px 14px -12px var(--btn-shadow);
}
.btn.sm {
  height: 34px;
  padding: 0 14px;
  font-size: 13px;
  letter-spacing: 0;
  min-width: 0;
}

/* ---------- 标签 ---------- */
.tag {
  display: inline-flex;
  align-items: center;
  height: 22px;
  padding: 0 8px;
  border-radius: 4px;
  background: var(--soft-grad);
  color: var(--berry-deep);
  font-size: 11px;
  letter-spacing: 0.8px;
  box-sizing: border-box;
}
.tag.plain {
  background: var(--soft-grad);
  color: var(--ink-2);
}
.tag.outline {
  background: rgba(255, 255, 255, 0.55);
  border: 1px solid var(--berry);
  color: var(--berry);
}

.chip {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  height: 30px;
  padding: 0 13px;
  border-radius: 999px;
  background: linear-gradient(180deg, #ffffff 0%, var(--chip-2) 100%);
  border: 1px solid var(--card-line);
  color: var(--ink-2);
  font-size: 13px;
  box-sizing: border-box;
}
.chip.on {
  background: var(--soft-grad);
  border-color: transparent;
  color: var(--berry-deep);
  font-weight: 600;
}
.chips {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 8px;
}

/* ---------- 小标题 ---------- */
.h2 {
  position: relative;
  padding-left: 11px;
  font-size: 18px;
  line-height: 26px;
  font-weight: 600;
  letter-spacing: 0.3px;
  color: var(--ink);
}
.h2::before {
  content: '';
  position: absolute;
  left: 0;
  top: 5px;
  width: 4px;
  height: 16px;
  border-radius: 2px;
  background: linear-gradient(180deg, var(--berry) 0%, var(--berry-pink) 100%);
}
.section-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  margin-bottom: 12px;
}
.link {
  display: inline-flex;
  align-items: center;
  font-size: 13px;
  color: var(--berry);
  padding: 4px 0;
}

/* ---------- 文本 ---------- */
.muted {
  color: var(--ink-2);
  font-size: 13px;
  line-height: 20px;
}
.meta {
  font-size: 13px;
  line-height: 20px;
  color: var(--ink-2);
}
.note {
  font-size: 12px;
  line-height: 18px;
  color: var(--ink-2);
}
.error {
  display: block;
  color: var(--error);
  font-size: 12px;
  line-height: 18px;
  margin: 6px 0 10px;
}
.grad-text {
  background: linear-gradient(120deg, var(--berry-deep) 0%, var(--berry) 52%, var(--berry-pink) 100%);
  -webkit-background-clip: text;
  background-clip: text;
  color: transparent;
}

/* ---------- 表单 ---------- */
.field-label {
  font-size: 13px;
  color: var(--ink-2);
  margin: 14px 0 6px;
}
.control {
  width: 100%;
  height: 44px;
  border-radius: 10px;
  border: 1px solid var(--card-line);
  background: linear-gradient(180deg, #ffffff 0%, var(--input-2) 100%);
  padding: 0 12px;
  font-size: 15px;
  color: var(--ink);
  display: flex;
  align-items: center;
  box-sizing: border-box;
}
.control.readonly {
  background: var(--readonly);
  border-color: transparent;
  color: var(--ink-2);
}
.control.textarea {
  height: auto;
  min-height: 68px;
  padding: 10px 12px;
  align-items: flex-start;
  line-height: 22px;
  font-size: 14px;
}
.hint-line {
  margin-top: 6px;
  font-size: 13px;
  line-height: 20px;
  color: var(--ink-2);
}

/* uni 原生输入框在 H5 里的内部节点需要跟随外部样式 */
.uni-input-input,
.uni-textarea-textarea {
  color: inherit;
  font-size: inherit;
  font-family: inherit;
}
.ph {
  color: #b9a5a9;
}
.wph {
  color: #cfbcc0;
  font-weight: 400;
}

/* ---------- 列表行 ---------- */
.rowlink {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 15px 16px;
  background: var(--card-grad);
  border: 1px solid var(--card-line);
  border-radius: 12px;
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.9), var(--card-shadow);
  box-sizing: border-box;
}
.rowlink + .rowlink {
  margin-top: 8px;
}
.rowlink .t {
  font-size: 15px;
  color: var(--ink);
}
.rowlink .r {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 13px;
  color: var(--ink-2);
}

/* ---------- 半屏 ---------- */
.sheet-mask {
  position: fixed;
  left: 0;
  right: 0;
  top: 0;
  bottom: 0;
  background: rgba(59, 42, 45, 0.3);
  z-index: 20;
}
.sheet {
  position: fixed;
  left: 0;
  right: 0;
  bottom: 0;
  z-index: 21;
  max-height: 92vh;
  overflow-y: auto;
  padding: 8px 16px calc(22px + env(safe-area-inset-bottom));
  border-radius: 24px 24px 0 0;
  background: linear-gradient(180deg, #fffdfc 0%, #fff7f5 100%);
  box-shadow: 0 -24px 60px rgba(59, 42, 45, 0.3);
  border-top: 1px solid rgba(255, 255, 255, 0.9);
  box-sizing: border-box;
}
.grab {
  width: 38px;
  height: 4px;
  border-radius: 2px;
  background: #ebd9dd;
  margin: 2px auto 10px;
}
.sheet-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 8px;
}
.sheet-title {
  font-size: 18px;
  line-height: 24px;
  font-weight: 600;
  color: var(--ink);
}
.sheet-sub {
  margin-top: 2px;
  font-size: 12px;
  line-height: 18px;
  color: var(--ink-2);
}
.sheet-x {
  width: 34px;
  height: 34px;
  border-radius: 50%;
  border: 1px solid var(--line);
  background: #ffffff;
  color: var(--ink-2);
  font-size: 16px;
  line-height: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  flex: 0 0 auto;
}
.sheet-body {
  padding-top: 6px;
}
.sheet-foot {
  margin-top: 16px;
}

/* ---------- 二级页页首 ---------- */
.sub-hero {
  position: relative;
  overflow: hidden;
  padding: calc(12px + var(--status-bar-height, 0px)) 16px 18px;
  background: linear-gradient(180deg, rgba(255, 255, 255, 0) 58%, var(--page) 100%),
    var(--hero-grad);
  box-sizing: border-box;
}
.sub-bar {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 12px;
}
.back-btn {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(255, 255, 255, 0.62);
  border: 1px solid rgba(244, 229, 225, 0.95);
  color: var(--ink);
  box-shadow: 0 8px 18px -12px rgba(156, 59, 80, 0.45);
  flex: 0 0 auto;
}
.back-glyph {
  width: 10px;
  height: 10px;
  border-left: 1.8px solid var(--ink);
  border-bottom: 1.8px solid var(--ink);
  transform: rotate(45deg);
  margin-left: 3px;
}
.sub-kicker {
  font-size: 11px;
  letter-spacing: 2px;
  color: var(--ink-2);
}

/* ---------- 提示块 ---------- */
.hintbox {
  margin-top: 12px;
  padding: 10px 12px;
  border-radius: 10px;
  background: linear-gradient(135deg, rgba(251, 226, 230, 0.75), rgba(255, 240, 242, 0.9));
  border: 1px solid rgba(240, 205, 214, 0.8);
  font-size: 13px;
  line-height: 20px;
  color: #7a4a55;
}

/* ---------- 说明块（带竖条） ---------- */
.obs-block .k {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: var(--ink-2);
  letter-spacing: 0.5px;
}
.obs-block .k::before {
  content: '';
  width: 3px;
  height: 12px;
  border-radius: 2px;
  background: var(--berry-pink);
}
.obs-block .v {
  margin-top: 4px;
  font-size: 15px;
  line-height: 23px;
  color: var(--ink);
}
</style>
