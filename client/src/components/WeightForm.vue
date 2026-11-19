<template>
  <HerlogSheet v-if="visible" title="记体重" :context="formatDayLabel(day)" :busy="saving" @close="cancel">
    <view class="measure">
      <H5Label class="hr-field-label" for="weight-kg">体重</H5Label>
      <view class="kg-row">
        <H5Input id="weight-kg" v-model="kg" inputmode="decimal" class="kg-input hr-number"
          placeholder="0.0" :aria-invalid="!!error" autocomplete="off" />
        <text>kg</text>
      </view>
    </view>

    <view class="time-row">
      <view>
        <H5Label for="weight-day" class="hr-field-label">日期</H5Label>
        <H5Input id="weight-day" v-model="day" type="date" class="field" :max="today" />
      </view>
      <view>
        <H5Label for="weight-time" class="hr-field-label">时间</H5Label>
        <H5Input id="weight-time" v-model="time" type="time" class="field" />
      </view>
    </view>

    <details class="optional">
      <summary>身体感受、标签和备注 <span>选填</span></summary>
      <view class="hr-field-label">身体感受</view>
      <view class="feeling-options">
        <H5Button v-for="item in feelingOptions" :key="item.code" class="feeling-option"
          :class="{ chosen: feelingTags.includes(item.code) }" :aria-pressed="feelingTags.includes(item.code)"
          @click="toggleFeeling(item.code)">{{ item.label }}</H5Button>
      </view>
      <H5Label class="hr-field-label" for="weight-tag">标签</H5Label>
      <H5Input id="weight-tag" v-model="tag" class="field" maxlength="32" placeholder="例如晨起" />
      <H5Label class="hr-field-label" for="weight-note">备注</H5Label>
      <H5Input id="weight-note" v-model="note" class="field" maxlength="500" />
    </details>
    <view v-if="error" class="error" role="alert">{{ error }}</view>
    <template #actions>
      <H5Button class="primary" :disabled="saving" @click="submit">{{ saving ? '保存中…' : '保存' }}</H5Button>
    </template>
  </HerlogSheet>
</template>

<script setup lang="ts">
import { H5Label } from './H5Form'
import H5Input from './H5Input'
import HerlogSheet from './HerlogSheet.vue'
import H5Button from './H5Button'
import { ref, watch } from 'vue'
import { currentTime, formatDayLabel, todayString, toZonedIso } from '../shared/dates'
import { parseKgToGrams } from '../shared/weight'
import { ApiRequestError, StaleSessionError } from '../services/httpClient'
import { createWeight, newClientKey } from '../services/weightService'
import type { Feeling } from '../services/wellnessService'

const props = defineProps<{ visible: boolean; presetDay?: string; presetTime?: string }>()
const emit = defineEmits<{ (event: 'close'): void; (event: 'saved'): void }>()

const kg = ref('')
const day = ref(todayString())
const time = ref(currentTime())
const tag = ref('')
const note = ref('')
const feelingTags = ref<Feeling[]>([])
const feelingOptions: { code: Feeling; label: string }[] = [
  { code: 'comfortable', label: '舒适' }, { code: 'tired', label: '疲惫' },
  { code: 'bloating', label: '腹胀' }, { code: 'puffy', label: '感觉浮肿' }
]
const error = ref('')
const saving = ref(false)
// 同一笔记录的重试必须沿用同一个请求键，保存成功后才换新的。
const clientKey = ref(newClientKey())

const today = todayString()

watch(
  () => props.visible,
  (visible) => {
    if (!visible) {
      return
    }
    day.value = props.presetDay || todayString()
    time.value = props.presetTime || currentTime()
    error.value = ''
    saving.value = false
    clientKey.value = newClientKey()
  }
)

function toggleFeeling(code: Feeling) {
  if (feelingTags.value.includes(code)) feelingTags.value = feelingTags.value.filter(value => value !== code)
  else if (feelingTags.value.length < 3) feelingTags.value = [...feelingTags.value, code]
  else uni.showToast({ title: '最多选择三项', icon: 'none' })
}

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
  if (!day.value || !time.value) {
    error.value = '请选择测量日期和时间'
    return
  }
  try {
    parseKgToGrams(kg.value)
  } catch (validation) {
    error.value = (validation as Error).message
    return
  }
  saving.value = true
  try {
    await createWeight({
      client_key: clientKey.value,
      kg: kg.value.trim(),
      measured_at: toZonedIso(day.value, time.value),
      tag: tag.value.trim() || null,
      note: note.value.trim() || null,
      feeling_tags: feelingTags.value
    })
    kg.value = ''
    tag.value = ''
    note.value = ''
    feelingTags.value = []
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
.measure {
  border: 1px solid var(--hr-line); background: var(--hr-paper);
  border-radius: 16px; padding: 10px 12px; margin-bottom: 12px;
}
.kg-row { display: flex; align-items: baseline; gap: 8px; min-width: 0; color: var(--hr-ink-2); }
.kg-input {
  box-sizing: border-box; min-width: 0; width: 7.5ch; min-height: 49px; padding: 1px 2px;
  border: 0; border-bottom: 1px solid var(--hr-line-strong); border-radius: 4px;
  color: var(--hr-rose-deep); background: transparent; font-size: 37px;
}
.kg-input::placeholder { color: var(--hr-ink-3); }
.time-row { display: grid; grid-template-columns: minmax(0, 1.35fr) minmax(0, 1fr); gap: 8px; }
.optional { border-top: 1px solid var(--hr-line); }
.optional summary { cursor: pointer; min-height: 44px; padding: 9px 2px; box-sizing: border-box; font-size: 14px; color: var(--hr-ink-2); }
.optional summary span { color: var(--hr-ink-3); font-size: 12px; margin-left: 5px; }
.feeling-options { display: flex; gap: 8px; flex-wrap: wrap; margin: 8px 0 10px; }
.feeling-option {
  min-height: 44px; padding: 7px 10px; font-size: 13px;
  border: 1px solid var(--hr-line); border-radius: 999px; color: var(--hr-ink-2); background: var(--hr-surface);
}
.feeling-option.chosen { background: var(--hr-rose-soft); color: var(--hr-rose-deep); border-color: var(--hr-rose); }
</style>
