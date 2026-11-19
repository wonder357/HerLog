<template>
  <nav class="tabbar" aria-label="主导航">
    <H5Button v-for="item in items" :key="item.path" class="tab"
      :class="{ active: item.path === current }" :aria-current="item.path === current ? 'page' : undefined"
      @click="go(item.path)">
      <span class="tab-symbol"><HerlogIcon :name="item.icon" class="icon" /></span>
      <span class="label">{{ item.label }}</span>
    </H5Button>
  </nav>
</template>

<script setup lang="ts">
import H5Button from './H5Button'
import HerlogIcon from './HerlogIcon.vue'

const props = defineProps<{ current: string }>()
const items = [
  { path: '/pages/home/index', label: '首页', icon: 'home' },
  { path: '/pages/period/index', label: '经期', icon: 'period' },
  { path: '/pages/weight/index', label: '体重', icon: 'weight' },
  { path: '/pages/skin/index', label: '皮肤', icon: 'skin' },
  { path: '/pages/me/index', label: '我的', icon: 'me' },
] as const

function go(path: string) {
  if (path !== props.current) uni.switchTab({ url: path })
}
</script>

<style scoped>
.tabbar {
  position: fixed;
  z-index: 10;
  left: 50%;
  bottom: 0;
  transform: translateX(-50%);
  box-sizing: border-box;
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: 3px;
  width: min(100%, calc(var(--hr-shell-width) + 32px));
  min-height: var(--hr-tab-height);
  padding: 6px max(9px, env(safe-area-inset-right)) calc(6px + env(safe-area-inset-bottom)) max(9px, env(safe-area-inset-left));
  background: var(--hr-surface);
  border-top: 1px solid var(--hr-line);
  box-shadow: 0 -8px 24px -22px #60404c79;
}
.tab {
  display: grid;
  justify-items: center;
  align-content: center;
  gap: 2px;
  padding: 3px 0;
  min-height: 48px;
  min-width: 0;
  border: 0;
  border-radius: 12px;
  background: transparent;
  color: var(--hr-ink-2);
}
.tab-symbol {
  display: grid;
  place-items: center;
  width: 42px;
  height: 27px;
  border-radius: 11px;
}
.tab.active { color: var(--hr-rose-deep); }
.tab.active .tab-symbol { background: var(--hr-rose-soft); }
.icon { width: 21px; height: 21px; }
.label { font-size: 12px; line-height: 1.25; }
.tab.active .label { font-weight: 700; }
</style>
