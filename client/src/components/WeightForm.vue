<template>
  <view v-if="visible">
    <view class="sheet-mask" @tap="cancel" />
    <view class="sheet">
      <view class="sheet-title">记体重</view>
      <input v-model="kg" class="field" type="digit" placeholder="体重 kg，例如 56.8" />
      <picker mode="date" :value="day" :end="today" @change="onDayChange">
        <view class="field">日期：{{ day }}</view>
      </picker>
      <picker mode="time" :value="time" @change="onTimeChange">
        <view class="field">时间：{{ time }}</view>
      </picker>
      <input v-model="tag" class="field" placeholder="标签（选填，如晨起）" />
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
import { currentTime, todayString, toZonedIso } from '../shared/dates'
import { parseKgToGrams } from '../shared/weight'
import { ApiRequestError, StaleSessionError } from '../services/httpClient'
import { createWeight, newClientKey } from '../services/weightService'

const props = defineProps<{ visible: boolean; presetDay?: string; presetTime?: string }>()
const emit = defineEmits<{ (event: 'close'): void; (event: 'saved'): void }>()

const kg = ref('')
const day = ref(todayString())
const time = ref(currentTime())
const tag = ref('')
const note = ref('')
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

function onDayChange(event: { detail: { value: string } }) {
  day.value = event.detail.value
}

function onTimeChange(event: { detail: { value: string } }) {
  time.value = event.detail.value
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
      note: note.value.trim() || null
    })
    kg.value = ''
    tag.value = ''
    note.value = ''
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
  margin-bottom: 14px;
}
.cancel {
  margin-top: 10px;
}
</style>
