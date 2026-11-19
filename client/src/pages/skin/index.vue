<template>
  <view class="hr-page herlog-skin" :class="{ 'hr-tab-page': !capturing }">
    <SkinCapture v-if="capturing" @close="capturing = false" @saved="saved" />
    <template v-else>
      <SkinStudio v-if="auth.token" :key="auth.token" :latest="latest" :photo-loading="loading" :photo-error="loadError"
        @capture="capturing = true" @history="openHistory" @refresh-photo="loadLatest" />
      <TabBar current="/pages/skin/index" />
    </template>
  </view>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { onHide, onShow } from '@dcloudio/uni-app'
import TabBar from '../../components/TabBar.vue'
import { currentEpoch } from '../../services/httpClient'
import { listObservations } from '../../services/skinService'
import type { SkinSummaryItem } from '../../services/types'
import { useAuthStore } from '../../stores/auth'
import SkinCapture from './SkinCapture.vue'
import SkinStudio from './SkinStudio.vue'
import './skin.css'

const auth = useAuthStore()
const capturing = ref(false)
const latest = ref<SkinSummaryItem | null>(null)
const loading = ref(true)
const loadError = ref(false)
let loadVersion = 0

async function loadLatest() {
  const version = ++loadVersion
  const epoch = currentEpoch()
  loading.value = true
  loadError.value = false
  try {
    const rows = await listObservations({ limit: 1 })
    if (version === loadVersion && epoch === currentEpoch()) latest.value = rows[0] ?? null
  } catch {
    if (version === loadVersion && epoch === currentEpoch()) loadError.value = true
  } finally {
    if (version === loadVersion) loading.value = false
  }
}

function openHistory(compare: boolean, day?: string) {
  const query = compare ? '?compare=1' : day ? '?day=' + encodeURIComponent(day) : ''
  uni.navigateTo({ url: '/pages/skin/history' + query })
}

function saved() {
  capturing.value = false
  uni.showToast({ title: '皮肤观察已保存', icon: 'none' })
  void loadLatest()
}

function clear() {
  capturing.value = false
  loadVersion += 1
  latest.value = null
}

watch(() => auth.token, clear, { flush: 'sync' })
onShow(() => { if (auth.token) void loadLatest() })
onHide(clear)
</script>
