import { onScopeDispose, ref, watch } from 'vue'
import { listFertilityDays } from '../../services/fertilityService'
import { ApiRequestError, currentEpoch, StaleSessionError } from '../../services/httpClient'
import type { DateRange, FertilityDay } from '../../shared/fertility'

export function useFertilityRange(getRange: () => DateRange | null, refresh: () => number) {
  const rows = ref<FertilityDay[]>([])
  const loading = ref(false)
  const error = ref('')
  let sequence = 0

  async function load(clear = false) {
    const current = ++sequence
    const epoch = currentEpoch()
    const range = getRange()
    if (clear || !range) rows.value = []
    loading.value = Boolean(range)
    error.value = ''
    if (!range) return
    const active = () => current === sequence && epoch === currentEpoch()
    try {
      const items = await listFertilityDays(range)
      if (active()) rows.value = items
    } catch (failure) {
      if (active() && !(failure instanceof StaleSessionError)) {
        error.value = failure instanceof ApiRequestError && failure.status === 503
          ? '备孕记录暂时不可用，请稍后重试。' : '暂时无法读取备孕记录。'
      }
    } finally {
      if (active()) loading.value = false
    }
  }

  watch(() => [getRange()?.from, getRange()?.to].join('/'), () => void load(true), { immediate: true, flush: 'sync' })
  watch(refresh, () => void load())
  onScopeDispose(() => { sequence += 1 })
  return { rows, loading, error, retry: () => load() }
}
