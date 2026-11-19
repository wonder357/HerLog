<template>
  <view v-if="visible">
    <view class="sheet-mask" @tap="cancel" />
    <view class="sheet">
      <view class="grab" />
      <view class="sheet-head">
        <view>
          <view class="sheet-title">记录感受</view>
          <view class="sheet-sub">{{ formatDayLabel(day) }} · 只记录当天的身体感受</view>
        </view>
        <view class="sheet-x" @tap="cancel">×</view>
      </view>

      <view class="sheet-body">
        <view class="label">经量</view>
        <view class="chips">
          <view
            v-for="item in flows"
            :key="item"
            class="chip"
            :class="{ on: flow === item }"
            @tap="toggleSingle(item)"
          >
            {{ item }}
          </view>
        </view>

        <view class="label">症状（可多选）</view>
        <view class="chips">
          <view
            v-for="item in symptoms"
            :key="item"
            class="chip"
            :class="{ on: selectedSymptoms.includes(item) }"
            @tap="toggleSymptom(item)"
          >
            {{ item }}
          </view>
        </view>

        <view class="label">生活影响</view>
        <view class="chips">
          <view
            v-for="item in impacts"
            :key="item"
            class="chip"
            :class="{ on: impact === item }"
            @tap="toggleImpact(item)"
          >
            {{ item }}
          </view>
        </view>

        <view class="label">备注</view>
        <input v-model="note" class="control" placeholder="选填，例如当时的状态" placeholder-class="ph" />

        <text v-if="error" class="error">{{ error }}</text>
      </view>

      <view class="sheet-foot">
        <button class="btn block" :disabled="saving" @tap="submit">
          {{ saving ? '保存中…' : '保存' }}
        </button>
        <view class="btn ghost block cancel" @tap="cancel">取消</view>
      </view>
    </view>
  </view>
</template>

<script setup lang="ts">
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
.label {
  margin: 16px 0 0;
  font-size: 12px;
  line-height: 18px;
  color: var(--ink-2);
  letter-spacing: 0.5px;
}
.label:first-child {
  margin-top: 4px;
}
.chips {
  margin-top: 8px;
}
.cancel {
  margin-top: 10px;
  height: 44px;
  font-size: 14px;
}
</style>
