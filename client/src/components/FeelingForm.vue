<template>
  <HerlogSheet v-if="visible" title="记录感受" :context="formatDayLabel(day)" :busy="saving" @close="cancel">
    <view class="hr-field-label">经量</view>
    <view class="chips">
      <H5Button v-for="item in flows" :key="item" class="chip" :class="{ active: flow === item }"
        :aria-pressed="flow === item" @click="toggleSingle(item)">{{ item }}</H5Button>
    </view>

    <view class="hr-field-label">症状 <small>可多选</small></view>
    <view class="chips">
      <H5Button v-for="item in symptoms" :key="item" class="chip" :class="{ active: selectedSymptoms.includes(item) }"
        :aria-pressed="selectedSymptoms.includes(item)" @click="toggleSymptom(item)">{{ item }}</H5Button>
    </view>

    <view class="hr-field-label">生活影响</view>
    <view class="chips">
      <H5Button v-for="item in impacts" :key="item" class="chip" :class="{ active: impact === item }"
        :aria-pressed="impact === item" @click="toggleImpact(item)">{{ item }}</H5Button>
    </view>
    <H5Label class="hr-field-label" for="cycle-note">备注 <small>选填</small></H5Label>
    <H5Input id="cycle-note" v-model="note" class="field" maxlength="500" />
    <view v-if="error" class="error" role="alert">{{ error }}</view>
    <template #actions>
      <H5Button class="primary" :disabled="saving" @click="submit">{{ saving ? '保存中…' : '保存感受' }}</H5Button>
    </template>
  </HerlogSheet>
</template>

<script setup lang="ts">
import { H5Label } from './H5Form'
import H5Button from './H5Button'
import HerlogSheet from './HerlogSheet.vue'
import H5Input from './H5Input'
import { ref, watch } from 'vue'
import { formatDayLabel } from '../shared/dates'
import { ApiRequestError, StaleSessionError } from '../services/httpClient'
import { saveFeeling } from '../services/periodService'
import type { FeelingItem } from '../services/types'

const props = defineProps<{ visible: boolean; day: string; existing: FeelingItem | null }>()
const emit = defineEmits<{ (event: 'close'): void; (event: 'saved'): void }>()

const flows = ['少量', '中等', '较多']
const symptoms = ['腹痛', '腹胀', '头痛', '疲惫', '情绪变化', '腰酸', '恶心', '乳房胀痛']
const impacts = ['无影响', '轻微影响', '影响日常', '影响睡眠']

const flow = ref<string | null>(null)
const selectedSymptoms = ref<string[]>([])
const impact = ref<string | null>(null)
const note = ref('')
const error = ref('')
const saving = ref(false)

watch(
  () => props.visible,
  (visible) => {
    if (!visible) {
      return
    }
    flow.value = props.existing?.flow ?? null
    selectedSymptoms.value = [...(props.existing?.symptoms ?? [])]
    impact.value = props.existing?.impact ?? null
    note.value = props.existing?.note ?? ''
    error.value = ''
    saving.value = false
  }
)

function toggleSingle(value: string) {
  flow.value = flow.value === value ? null : value
}

function toggleImpact(value: string) {
  impact.value = impact.value === value ? null : value
}

function toggleSymptom(value: string) {
  selectedSymptoms.value = selectedSymptoms.value.includes(value)
    ? selectedSymptoms.value.filter((item) => item !== value)
    : [...selectedSymptoms.value, value]
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
  saving.value = true
  error.value = ''
  try {
    await saveFeeling(props.day, {
      flow: flow.value,
      symptoms: selectedSymptoms.value,
      impact: impact.value,
      note: note.value.trim() || null
    })
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
.chips { display: flex; flex-wrap: wrap; gap: 8px; margin: 6px 0 14px; }
.chip {
  min-height: 44px; padding: 7px 11px; border: 1px solid var(--hr-line);
  border-radius: 12px; background: var(--hr-paper); color: var(--hr-ink-2); font-size: 13px;
}
.chip.active { background: var(--hr-rose-soft); color: var(--hr-rose-deep); border-color: var(--hr-rose); }
small { font-size: 12px; color: var(--hr-ink-3); font-weight: 400; }
</style>
