<template>
  <HerlogSheet v-if="visible" title="记录经期" :context="formatDayLabel(day)" :busy="saving" @close="cancel">
    <view class="modes" aria-label="记录类型">
      <H5Button class="mode" :class="{ active: mode === 'start' }" :aria-pressed="mode === 'start'"
        @click="mode = 'start'">经期开始</H5Button>
      <H5Button class="mode" :class="{ active: mode === 'end' }" :aria-pressed="mode === 'end'"
        @click="mode = 'end'">经期最后一天</H5Button>
    </view>
    <view class="hint">
      {{ mode === 'start' ? '把选中的日期记为经期第一天。'
        : openPeriod ? '这段经期从 ' + formatDayLabel(openPeriod.startDay) + ' 开始。'
        : '请先补记这段经期的开始日。' }}
    </view>
    <view v-if="error" class="error" role="alert">{{ error }}</view>
    <template #actions>
      <H5Button class="primary" :disabled="saving" @click="submit">{{ saving ? '保存中…' : '保存' }}</H5Button>
    </template>
  </HerlogSheet>
</template>

<script setup lang="ts">
import H5Button from './H5Button'
import HerlogSheet from './HerlogSheet.vue'
import { ref, watch } from 'vue'
import { formatDayLabel } from '../shared/dates'
import { ApiRequestError, StaleSessionError } from '../services/httpClient'
import { createPeriod, updatePeriod } from '../services/periodService'

interface OpenPeriod {
  id: number
  startDay: string
}

const props = defineProps<{
  visible: boolean
  day: string
  openPeriod: OpenPeriod | null
}>()
const emit = defineEmits<{ (event: 'close'): void; (event: 'saved'): void }>()

const mode = ref<'start' | 'end'>('start')
const error = ref('')
const saving = ref(false)

watch(
  () => props.visible,
  (visible) => {
    if (!visible) {
      return
    }
    mode.value = props.openPeriod ? 'end' : 'start'
    error.value = ''
    saving.value = false
  }
)

function cancel() {
  if (saving.value) {
    return
  }
  emit('close')
}

async function submit() {
  if (saving.value) {
    return
  }
  error.value = ''
  saving.value = true
  try {
    if (mode.value === 'start') {
      await createPeriod(props.day, null)
    } else if (!props.openPeriod) {
      error.value = '这一天之前没有未记录结束的经期，请先补记开始日'
      return
    } else if (props.openPeriod.startDay > props.day) {
      error.value = '最后一天不能早于开始日'
      return
    } else {
      await updatePeriod(props.openPeriod.id, props.openPeriod.startDay, props.day)
    }
    emit('saved')
  } catch (failure) {
    if (failure instanceof StaleSessionError) {
      return
    }
    error.value =
      failure instanceof ApiRequestError ? failure.message : '保存失败，请检查网络后重试'
  } finally {
    saving.value = false
  }
}
</script>

<style scoped>
.modes { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; margin: 0 0 12px; }
.mode {
  min-height: 46px; padding: 6px; border: 1px solid var(--hr-line);
  border-radius: 12px; background: var(--hr-paper); color: var(--hr-ink-2); font-size: 14px;
}
.mode.active { background: var(--hr-rose-soft); color: var(--hr-rose-deep); border-color: var(--hr-rose); font-weight: 650; }
.hint { padding: 11px; margin-bottom: 8px; background: var(--hr-peach); color: var(--hr-peach-ink); border-radius: 11px; font-size: 14px; }
</style>
