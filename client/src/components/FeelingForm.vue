<template>
  <view v-if="visible">
    <view class="sheet-mask" @tap="cancel" />
    <view class="sheet">
      <view class="sheet-title">记录感受 · {{ formatDayLabel(day) }}</view>

      <view class="label">经量</view>
      <view class="chips">
        <view
          v-for="item in flows"
          :key="item"
          class="chip"
          :class="{ active: flow === item }"
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
          :class="{ active: selectedSymptoms.includes(item) }"
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
          :class="{ active: impact === item }"
          @tap="toggleImpact(item)"
        >
          {{ item }}
        </view>
      </view>

      <input v-model="note" class="field" placeholder="备注（选填）" />
      <text v-if="error" class="error">{{ error }}</text>
      <button class="primary" :disabled="saving" @tap="submit">
        {{ saving ? '保存中…' : '保存' }}
      </button>
      <view class="ghost cancel" @tap="cancel">取消</view>
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
.sheet-title {
  font-size: 17px;
  font-weight: 600;
  margin-bottom: 12px;
}
.label {
  font-size: 13px;
  color: #8a7f7a;
  margin: 8px 0 6px;
}
.chips {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 6px;
}
.chip {
  padding: 6px 12px;
  border-radius: 999px;
  border: 1px solid #e4d8d3;
  font-size: 13px;
  color: #6f635e;
}
.chip.active {
  border-color: #b4544a;
  color: #b4544a;
  background: #fdf2ef;
}
.cancel {
  margin-top: 10px;
}
</style>
