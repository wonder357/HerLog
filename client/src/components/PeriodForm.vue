<template>
  <view v-if="visible">
    <view class="sheet-mask" @tap="cancel" />
    <view class="sheet">
      <view class="sheet-title">记录经期</view>
      <view class="muted">选中日期：{{ formatDayLabel(day) }}</view>
      <view class="modes">
        <view
          class="mode"
          :class="{ active: mode === 'start' }"
          @tap="mode = 'start'"
        >
          经期开始
        </view>
        <view class="mode" :class="{ active: mode === 'end' }" @tap="mode = 'end'">
          经期最后一天
        </view>
      </view>
      <view v-if="mode === 'end'" class="muted hint">
        {{
          openPeriod
            ? `将 ${formatDayLabel(day)} 记为 ${formatDayLabel(openPeriod.startDay)} 这段经期的最后一天`
            : '这一天之前没有未记录结束的经期，请先补记开始日'
        }}
      </view>
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
.sheet-title {
  font-size: 17px;
  font-weight: 600;
  margin-bottom: 10px;
}
.modes {
  display: flex;
  gap: 10px;
  margin: 12px 0;
}
.mode {
  flex: 1;
  height: 42px;
  line-height: 40px;
  text-align: center;
  border-radius: 12px;
  border: 1px solid #e4d8d3;
  color: #6f635e;
  font-size: 14px;
}
.mode.active {
  border-color: #b4544a;
  color: #b4544a;
  background: #fdf2ef;
}
.hint {
  margin-bottom: 10px;
}
.cancel {
  margin-top: 10px;
}
</style>
