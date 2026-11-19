<template>
  <view class="tabbar">
    <view
      v-for="item in items"
      :key="item.path"
      class="tab"
      :class="{ on: item.path === current }"
      @tap="go(item)"
    >
      <view class="tab-ic" :class="{ on: item.path === current }">
        <image class="tab-img" :src="iconSrc(item)" mode="aspectFit" />
      </view>
      <text class="tab-label">{{ item.label }}</text>
    </view>
  </view>
</template>

<script setup lang="ts">
interface TabItem {
  path: string
  label: string
  icon: string
}

const props = defineProps<{ current: string }>()

// 五个一级页共用一份配置，路径变化只改这里。
// 图标取自「图标套-豆包改版/icons」：未选中线性 / 选中实心，同一套 27×27。
const items: TabItem[] = [
  { path: '/pages/home/index', label: '首页', icon: 'home' },
  { path: '/pages/period/index', label: '经期', icon: 'period' },
  { path: '/pages/weight/index', label: '体重', icon: 'weight' },
  { path: '/pages/skin/index', label: '皮肤', icon: 'skin' },
  { path: '/pages/me/index', label: '我的', icon: 'me' }
]

function iconSrc(item: TabItem): string {
  const state = item.path === props.current ? '-active' : ''
  return `/static/icons/${item.icon}${state}.svg`
}

function go(item: TabItem) {
  if (item.path === props.current) {
    return
  }
  uni.switchTab({ url: item.path })
}
</script>

<style scoped>
.tabbar {
  position: fixed;
  left: 0;
  right: 0;
  bottom: 0;
  z-index: 10;
  display: flex;
  padding: 8px 0 18px;
  padding-bottom: calc(18px + env(safe-area-inset-bottom));
  background: rgba(255, 255, 255, 0.86);
  -webkit-backdrop-filter: blur(16px) saturate(1.6);
  backdrop-filter: blur(16px) saturate(1.6);
  border-top: 1px solid var(--line);
  box-shadow: 0 -12px 30px -18px rgba(192, 86, 107, 0.4);
}
.tab {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
}
.tab-ic {
  width: 44px;
  height: 44px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
}
.tab-ic.on {
  background: var(--tabon-grad);
  box-shadow: 0 8px 16px -8px rgba(192, 86, 107, 0.4);
}
.tab-img {
  width: 27px;
  height: 27px;
  display: block;
}
.tab-label {
  font-size: 11px;
  line-height: 16px;
  color: var(--outline);
  letter-spacing: 0.5px;
}
.tab.on .tab-label {
  color: var(--berry);
  font-weight: 600;
}
</style>
