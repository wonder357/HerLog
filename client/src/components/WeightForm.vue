<template>
  <view v-if="visible">
    <view class="sheet-mask" @tap="cancel" />
    <view class="sheet">
      <view class="grab" />
      <view class="sheet-head">
        <view>
          <view class="sheet-title">记体重</view>
          <view class="sheet-sub">尽量在相近的时间与条件下称重</view>
        </view>
        <view class="sheet-x" @tap="cancel">×</view>
      </view>

      <view class="sheet-body">
        <view class="wval">
          <input
            v-model="kg"
            class="winput"
            type="digit"
            placeholder="00.0"
            placeholder-class="wph"
            :adjust-position="true"
          />
          <text class="wunit">kg</text>
        </view>

        <picker mode="date" :value="day" :end="today" @change="onDayChange">
          <view class="form-row">
            <text class="row-k">日期</text>
            <text class="row-v">{{ day }}</text>
          </view>
        </picker>
        <picker mode="time" :value="time" @change="onTimeChange">
          <view class="form-row">
            <text class="row-k">时间</text>
            <text class="row-v">{{ time }}</text>
          </view>
        </picker>

        <input v-model="tag" class="control row-input" placeholder="标签（选填，如晨起）" placeholder-class="ph" />
        <input v-model="note" class="control row-input" placeholder="备注（选填）" placeholder-class="ph" />

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
.wval {
  display: flex;
  align-items: flex-end;
  justify-content: center;
  gap: 6px;
  padding: 6px 0 12px;
}
.winput {
  width: 170px;
  height: 52px;
  font-size: 40px;
  line-height: 52px;
  font-weight: 600;
  letter-spacing: -0.5px;
  text-align: center;
  color: var(--ink);
  font-variant-numeric: tabular-nums;
}
.wunit {
  font-size: 15px;
  line-height: 22px;
  color: var(--ink-2);
  padding-bottom: 8px;
}
.form-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: 46px;
  padding: 0 12px;
  margin-bottom: 10px;
  border-radius: 10px;
  border: 1px solid var(--card-line);
  background: linear-gradient(180deg, #ffffff 0%, var(--input-2) 100%);
  box-sizing: border-box;
}
.row-k {
  font-size: 13px;
  color: var(--ink-2);
}
.row-v {
  font-size: 15px;
  color: var(--ink);
  font-variant-numeric: tabular-nums;
}
.row-input {
  margin-top: 0;
  margin-bottom: 10px;
  font-size: 14px;
}
.cancel {
  margin-top: 10px;
  height: 44px;
  font-size: 14px;
}
</style>
