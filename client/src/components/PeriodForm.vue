<template>
  <HerlogSheet v-if="visible" :title="editing ? '更正经期' : '记录经期'" :context="selectableDay ? undefined : formatDayLabel(day)"
    :busy="saving" @close="cancel">
    <view v-if="!editing" class="modes" role="group" aria-label="记录类型">
      <H5Button v-for="option in modes" :key="option.value" class="mode"
        :class="{ active: mode === option.value }" :aria-pressed="mode === option.value"
        @click="setMode(option.value)">{{ option.label }}</H5Button>
    </view>
    <view class="date-fields">
      <view v-if="mode === 'end' && !editing" class="hint">
        这段经期从 {{ formatDayLabel(start) }} 开始。
      </view>
      <view v-else>
        <H5Label class="hr-field-label" for="period-start">开始日期</H5Label>
        <H5Input id="period-start" v-model="start" class="field" type="date" :max="today" />
      </view>
      <view v-if="editing || mode !== 'start'">
        <H5Label class="hr-field-label" for="period-end">最后一天 {{ editing ? '（选填）' : '' }}</H5Label>
        <H5Input id="period-end" v-model="end" class="field" type="date" :min="start" :max="today" />
        <H5Button v-if="editing && end" class="hr-action" @click="end = ''">清除结束日期</H5Button>
      </view>
    </view>
    <p v-if="error" ref="errorNotice" class="error" role="alert" tabindex="-1">{{ error }}</p>
    <template #actions>
      <slot name="extra-action" :day="mode === 'end' || mode === 'range' ? end : start" :disabled="saving" />
      <H5Button class="primary" :disabled="saving" @click="submit">{{ saving ? '保存中…' : '保存经期' }}</H5Button>
    </template>
  </HerlogSheet>
</template>

<script setup lang="ts">
import H5Button from './H5Button'
import { H5Label } from './H5Form'
import H5Input from './H5Input'
import HerlogSheet from './HerlogSheet.vue'
import { computed, nextTick, ref, watch } from 'vue'
import { formatDayLabel, todayString } from '../shared/dates'
import { ApiRequestError, StaleSessionError } from '../services/httpClient'
import { createPeriod, updatePeriod } from '../services/periodService'
import type { PeriodItem } from '../services/types'

interface OpenPeriod {
  id: number
  startDay: string
}

type Mode = 'start' | 'end' | 'range'

const props = defineProps<{
  visible: boolean
  day: string
  openPeriod: OpenPeriod | null
  editing?: PeriodItem | null
  selectableDay?: boolean
}>()
const emit = defineEmits<{ close: []; saved: [day: string] }>()

const mode = ref<Mode>('start')
const start = ref('')
const end = ref('')
const today = ref(todayString())
const error = ref('')
const errorNotice = ref<HTMLElement | null>(null)
const saving = ref(false)

const modes = computed<{ value: Mode; label: string }[]>(() => [
  { value: 'start', label: '记开始' },
  ...(props.openPeriod ? [{ value: 'end' as const, label: '补最后一天' }] : []),
  { value: 'range', label: '补记一段' }
])

watch(() => props.visible, visible => {
  if (!visible) return
  today.value = todayString()
  setMode(!props.editing && props.openPeriod ? 'end' : 'start')
}, { immediate: true })

function setMode(value: Mode) {
  mode.value = value
  start.value = props.editing?.start_day ?? (value === 'end' ? props.openPeriod?.startDay : props.day) ?? props.day
  end.value = props.editing?.end_day ?? (props.editing ? '' : props.day)
  error.value = ''
}

function cancel() {
  if (!saving.value) emit('close')
}

function showError(message: string) {
  error.value = message
  void nextTick(() => errorNotice.value?.focus())
}

async function submit() {
  if (saving.value) return
  error.value = ''
  const lastDay = props.editing || mode.value !== 'start' ? end.value || null : null
  const requiredEnd = !props.editing && mode.value !== 'start'
  if (!start.value || (requiredEnd && !lastDay)) {
    showError('请选择需要记录的日期')
    return
  }
  if (start.value > today.value || (lastDay && lastDay > today.value)) {
    showError('实际经期只能记今天或更早的日期')
    return
  }
  if (lastDay && lastDay < start.value) {
    showError('最后一天不能早于开始日期')
    return
  }
  const id = props.editing?.id ?? (mode.value === 'end' ? props.openPeriod?.id : undefined)
  saving.value = true
  try {
    const saved = id ? await updatePeriod(id, start.value, lastDay) : await createPeriod(start.value, lastDay)
    emit('saved', mode.value === 'end' && saved.end_day ? saved.end_day : saved.start_day)
  } catch (failure) {
    if (failure instanceof StaleSessionError) return
    showError(failure instanceof ApiRequestError ? failure.message : '保存失败，请检查网络后重试')
  } finally {
    saving.value = false
  }
}
</script>

<style scoped>
.modes { display: flex; flex-wrap: wrap; gap: 8px; margin: 0 0 16px; }
.mode {
  flex: 1 0 auto; min-height: 46px; padding: 6px 9px; border: 1px solid var(--hr-line);
  border-radius: 12px; background: var(--hr-paper); color: var(--hr-ink-2); font-size: 14px;
}
.mode.active { background: var(--hr-rose-soft); color: var(--hr-rose-deep); border-color: var(--hr-rose); font-weight: 650; }
.date-fields { display: grid; gap: 10px; margin-bottom: 8px; }
.date-fields .field { width: 100%; min-width: 0; }
.hint { padding: 10px 12px; background: var(--hr-peach); color: var(--hr-peach-ink); border-radius: 12px; font-size: 14px; }
</style>
