<template>
  <view v-if="visible">
    <view class="sheet-mask" @tap="cancel" />
    <view class="sheet">
      <view class="grab" />
      <view class="sheet-head">
        <view>
          <view class="sheet-title">记录经期</view>
          <view class="sheet-sub">选中日期：{{ formatDayLabel(day) }}</view>
        </view>
        <view class="sheet-x" @tap="cancel">×</view>
      </view>

      <view class="sheet-body">
        <view class="modes">
          <view class="mode" :class="{ on: mode === 'start' }" @tap="mode = 'start'">
            <view class="mode-t">经期开始</view>
            <view class="mode-s">把这一天记为一段经期的第一天</view>
          </view>
          <view class="mode" :class="{ on: mode === 'end' }" @tap="mode = 'end'">
            <view class="mode-t">经期最后一天</view>
            <view class="mode-s">给进行中的经期补记结束日</view>
          </view>
        </view>

        <view v-if="mode === 'end'" class="hintbox">
          {{
            openPeriod
              ? `将 ${formatDayLabel(day)} 记为 ${formatDayLabel(openPeriod.startDay)} 这段经期的最后一天`
              : '这一天之前没有未记录结束的经期，请先补记开始日'
          }}
        </view>

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
.modes {
  display: flex;
  gap: 10px;
  margin-top: 4px;
}
.mode {
  flex: 1;
  padding: 12px 10px;
  border-radius: 12px;
  border: 1px solid var(--card-line);
  background: linear-gradient(180deg, #ffffff 0%, var(--chip-2) 100%);
  box-sizing: border-box;
}
.mode.on {
  background: var(--soft-grad);
  border-color: transparent;
  box-shadow: 0 8px 18px -14px var(--btn-shadow);
}
.mode-t {
  font-size: 14px;
  line-height: 20px;
  font-weight: 600;
  color: var(--ink);
}
.mode.on .mode-t {
  color: var(--berry-deep);
}
.mode-s {
  margin-top: 4px;
  font-size: 11px;
  line-height: 16px;
  color: var(--ink-2);
}
.cancel {
  margin-top: 10px;
  height: 44px;
  font-size: 14px;
}
</style>
