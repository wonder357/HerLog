import { computed, ref, watch } from 'vue'
import { defineStore } from 'pinia'
import { useAuthStore } from './auth'
import { currentEpoch } from '../services/httpClient'
import { getCyclePreference, updateCycleMode, updateTryingStart } from '../services/fertilityService'
import type { CyclePreference } from '../services/fertilityService'
import type { CycleMode } from '../shared/fertility'

export const useCyclePreference = defineStore('cyclePreference', () => {
  const auth = useAuthStore()
  const preference = ref<CyclePreference | null>(null)
  const loading = ref(false)
  const unavailable = ref(false)
  const mode = computed(() => preference.value?.active_mode ?? 'period')
  let generation = 0

  watch(() => auth.member?.customer_id, () => {
    generation += 1
    preference.value = null
    loading.value = false
    unavailable.value = false
  }, { flush: 'sync' })

  async function load() {
    if (!auth.isLoggedIn || loading.value) return
    const request = ++generation
    const epoch = currentEpoch()
    loading.value = true
    unavailable.value = false
    const isCurrent = () => request === generation && epoch === currentEpoch()
    try {
      const result = await getCyclePreference()
      if (isCurrent()) preference.value = result
    } catch {
      if (isCurrent()) unavailable.value = true
    } finally {
      if (isCurrent()) loading.value = false
    }
  }

  async function update(request: () => Promise<CyclePreference>) {
    const epoch = currentEpoch()
    const result = await request()
    if (epoch !== currentEpoch()) return
    generation += 1
    preference.value = result
    loading.value = false
    unavailable.value = false
  }

  return {
    preference, mode, loading, unavailable, load,
    chooseMode: (value: CycleMode) => update(() => updateCycleMode(value)),
    setStart: (day: string | null) => update(() => updateTryingStart(day))
  }
})
