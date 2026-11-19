<template>
  <image v-if="url" :src="url" :aria-label="label" mode="aspectFit" class="skin-photo" @error="failed" />
  <view v-else class="skin-photo picture-state">
    <text v-if="loading" class="skin-muted" role="status">正在读取照片</text>
    <template v-else>
      <text class="skin-muted">图片没有加载成功</text>
      <SkinButton class="skin-button skin-link" @click="load">重试</SkinButton>
    </template>
  </view>
</template>

<script setup lang="ts">
import SkinButton from '../../components/H5Button'
import { onBeforeUnmount, ref, watch } from 'vue'
import { currentEpoch } from '../../services/httpClient'
import { observationImageUrl, releaseBlobUrl } from '../../services/skinService'

const props = defineProps<{ id: number; label: string }>()
const url = ref<string | null>(null)
const loading = ref(true)
let requestVersion = 0

function failed() {
  releaseBlobUrl(url.value)
  url.value = null
}

async function load() {
  const version = ++requestVersion
  const epoch = currentEpoch()
  failed()
  loading.value = true
  try {
    const image = await observationImageUrl(props.id)
    if (requestVersion !== version || currentEpoch() !== epoch) {
      releaseBlobUrl(image)
      return
    }
    url.value = image
  } catch {
    // 保留照片占位，单独重试失败的一张。
  } finally {
    if (requestVersion === version) loading.value = false
  }
}

watch(() => props.id, load, { immediate: true })
onBeforeUnmount(() => {
  requestVersion += 1
  failed()
})
</script>

<style scoped>
.picture-state { display: grid; place-content: center; justify-items: center; padding: 8px; text-align: center; border-radius: 16px; }
</style>
