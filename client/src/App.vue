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

<style src="./styles/herlog.css"></style>
