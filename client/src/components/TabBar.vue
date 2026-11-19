<template>
  <view class="tabbar">
    <view
      v-for="item in items"
      :key="item.path"
      class="tab"
      :class="{ active: item.path === current }"
      @tap="go(item)"
    >
      <svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6">
        <path :d="item.icon" stroke-linecap="round" stroke-linejoin="round" />
      </svg>
      <text class="label">{{ item.label }}</text>
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
const items: TabItem[] = [
  { path: '/pages/home/index', label: '首页', icon: 'M4 11.5 12 4l8 7.5V20a1 1 0 0 1-1 1h-4.5v-6h-5v6H5a1 1 0 0 1-1-1z' },
  { path: '/pages/period/index', label: '经期', icon: 'M5 6h14v14H5zM8 3v4M16 3v4M5 10h14' },
  { path: '/pages/weight/index', label: '体重', icon: 'M12 4a2 2 0 0 1 1.7 3l5 12H5.3l5-12A2 2 0 0 1 12 4zM9 14h6' },
  { path: '/pages/skin/index', label: '皮肤', icon: 'M12 3c3 4 6 6.5 6 10a6 6 0 0 1-12 0c0-3.5 3-6 6-10zM9.5 13.5a2.5 2.5 0 0 0 5 0' },
  { path: '/pages/me/index', label: '我的', icon: 'M12 12a4 4 0 1 0 0-8 4 4 0 0 0 0 8zM4 21c0-4 3.6-6 8-6s8 2 8 6' }
]

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
  height: 58px;
  padding-bottom: env(safe-area-inset-bottom);
  background: #ffffff;
  border-top: 1px solid #f0e6e2;
}
.tab {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: #8a7f7a;
}
.tab.active {
  color: #b4544a;
}
.icon {
  width: 22px;
  height: 22px;
  margin-bottom: 2px;
}
.label {
  font-size: 11px;
}
</style>
