import { onBeforeUnmount, ref, watch } from 'vue'
import { ApiRequestError, currentEpoch, fetchBlobUrl, releaseBlobUrl } from '../services/httpClient'

export function usePrivatePhoto(path: () => string | undefined) {
  const url = ref<string | null>(null)
  const loading = ref(false)
  const error = ref('')
  let generation = 0

  function clear() {
    generation += 1
    releaseBlobUrl(url.value)
    url.value = null
    error.value = ''
    loading.value = false
  }

  async function reload() {
    clear()
    const target = path()
    if (!target) return
    const version = generation
    const epoch = currentEpoch()
    const active = () => generation === version && epoch === currentEpoch()
    loading.value = true
    try {
      const result = await fetchBlobUrl(target)
      if (active()) url.value = result
      else releaseBlobUrl(result)
    } catch (failure) {
      if (!active()) return
      const status = failure instanceof ApiRequestError ? failure.status : 0
      error.value = status === 404 ? '照片已不存在。' : status === 401 ? '请重新登录后查看照片。' : '照片读取失败，请重试。'
    } finally {
      if (active()) loading.value = false
    }
  }

  watch(path, reload, { immediate: true })
  onBeforeUnmount(clear)
  return { url, loading, error, reload }
}
