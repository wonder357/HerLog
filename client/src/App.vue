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
page {
  background-color: #fdf8f6;
  color: #2f2a28;
  font-size: 15px;
}
.card {
  background: #ffffff;
  border-radius: 16px;
  padding: 16px;
  margin-bottom: 12px;
}
.muted {
  color: #8a7f7a;
  font-size: 13px;
}
.primary {
  background: #b4544a;
  color: #ffffff;
  border-radius: 12px;
  height: 46px;
  line-height: 46px;
  text-align: center;
  font-size: 16px;
}
.primary[disabled] {
  opacity: 0.6;
}
.ghost {
  border: 1px solid #e4d8d3;
  color: #b4544a;
  border-radius: 12px;
  height: 44px;
  line-height: 42px;
  text-align: center;
}
.field {
  border: 1px solid #e4d8d3;
  border-radius: 12px;
  height: 44px;
  padding: 0 12px;
  margin-bottom: 12px;
  background: #fff;
}
.error {
  color: #c0392b;
  font-size: 12px;
  margin: -6px 0 10px;
}
.sheet-mask {
  position: fixed;
  left: 0;
  right: 0;
  top: 0;
  bottom: 0;
  background: rgba(35, 28, 26, 0.35);
  z-index: 20;
}
.sheet {
  position: fixed;
  left: 0;
  right: 0;
  bottom: 0;
  z-index: 21;
  background: #fff;
  border-radius: 20px 20px 0 0;
  padding: 18px 16px calc(18px + env(safe-area-inset-bottom));
}
</style>
