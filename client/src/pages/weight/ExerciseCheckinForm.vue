<template>
  <HerlogSheet :title="entry ? '编辑运动记录' : '记录活动'" :busy="saving || deleting" @close="emit('close')">
    <H5Form id="exercise-checkin-form" @submit.prevent="submit">
      <H5Label class="hr-field-label" for="exercise-type">活动类型</H5Label>
      <select id="exercise-type" v-model="activity" class="field" :disabled="locked">
        <option v-for="(name, code) in activities" :key="code" :value="code">{{ name }}</option>
      </select>
      <div class="exercise-time">
        <div>
          <H5Label class="hr-field-label" for="exercise-date">日期</H5Label>
          <H5Input id="exercise-date" v-model="day" class="field" type="date" :max="today" :disabled="locked" />
        </div>
        <div>
          <H5Label class="hr-field-label" for="exercise-time">时间</H5Label>
          <H5Input id="exercise-time" v-model="time" class="field" type="time" :disabled="locked" />
        </div>
      </div>
      <template v-if="activity !== 'rest'">
        <H5Label class="hr-field-label" for="exercise-minutes">时长 · 分钟（选填）</H5Label>
        <H5Input id="exercise-minutes" v-model="minutes" class="field" inputmode="numeric" :disabled="locked" />
        <div class="form-chips" role="group" aria-label="时长快捷选项">
          <H5Button v-for="amount in [10, 20, 30, 45]" :key="amount" class="form-chip" :disabled="locked"
            :aria-pressed="minutes === String(amount)" @click="minutes = String(amount)">{{ amount }} 分</H5Button>
        </div>
        <div class="form-block" role="group" aria-labelledby="exercise-effort">
          <div id="exercise-effort" class="hr-field-label">活动强度（选填）</div>
          <div class="form-chips">
            <H5Button v-for="(name, code) in effortNames" :key="code" class="form-chip" :disabled="locked"
              :aria-pressed="effort === code" @click="effort = effort === code ? null : code">{{ name }}</H5Button>
          </div>
        </div>
      </template>
      <div class="form-block" role="group" aria-labelledby="exercise-feeling">
        <div id="exercise-feeling" class="hr-field-label">当时的感受（选填）</div>
        <div class="form-chips">
          <H5Button v-for="(name, code) in exerciseFeelings" :key="code" class="form-chip" :disabled="locked"
            :aria-pressed="feeling === code" @click="feeling = feeling === code ? null : code">{{ name }}</H5Button>
        </div>
      </div>
      <PrivatePhotoEditor v-model="photo" v-model:processing="photoProcessing" label="运动照片"
        :saved-path="entry?.has_photo ? checkinPhotoPath(entry.id) : undefined" :disabled="locked" />
      <div v-if="entry" class="manage">
        <H5Button class="hr-action" :disabled="locked" @click="emit('share', entry)">发起讨论</H5Button>
        <H5Button class="hr-action remove" :disabled="locked" @click="emit('remove', entry)">删除记录</H5Button>
      </div>
      <p v-if="error || deleteError" ref="errorNotice" class="error" role="alert" tabindex="-1">{{ error || deleteError }}</p>
    </H5Form>
    <template #actions>
      <H5Button class="primary" type="submit" form="exercise-checkin-form" :disabled="locked || photoProcessing">
        {{ saving ? '保存中…' : entry ? '保存修改' : '保存打卡' }}
      </H5Button>
    </template>
  </HerlogSheet>
</template>

<script setup lang="ts">
import { computed, nextTick, ref } from 'vue'
import H5Button from '../../components/H5Button'
import H5Form, { H5Label } from '../../components/H5Form'
import H5Input from '../../components/H5Input'
import HerlogSheet from '../../components/HerlogSheet.vue'
import PrivatePhotoEditor from '../../components/PrivatePhotoEditor.vue'
import { currentTime, formatMoment, shanghaiDayKey, todayString, toZonedIso } from '../../shared/dates'
import { ApiRequestError, currentEpoch, StaleSessionError } from '../../services/httpClient'
import { checkinPhotoPath } from '../../services/privatePhotoService'
import type { PrivatePhotoPayload } from '../../services/privatePhotoService'
import { newClientKey } from '../../services/weightService'
import { activities, effortNames, exerciseFeelings, saveCheckin, updateCheckin } from '../../services/wellnessService'
import type { Activity, Checkin, CheckinInput } from '../../services/wellnessService'

const props = defineProps<{ preset: Activity; entry: Checkin | null; deleting: boolean; deleteError: string }>()
const emit = defineEmits<{ close: []; saved: [entry: Checkin]; share: [entry: Checkin]; remove: [entry: Checkin] }>()
const original = props.entry
const today = todayString()
const originalDay = original ? shanghaiDayKey(original.started_at) : today
const originalTime = original ? formatMoment(original.started_at).slice(-5) : currentTime()
const activity = ref(original?.activity_code ?? props.preset)
const day = ref(originalDay)
const time = ref(originalTime)
const minutes = ref(original?.duration_minutes?.toString() ?? '')
const effort = ref<CheckinInput['effort']>(original?.effort ?? null)
const feeling = ref<CheckinInput['feeling_code']>(original?.feeling_code ?? null)
const photo = ref<PrivatePhotoPayload | null>()
const photoProcessing = ref(false)
const saving = ref(false)
const locked = computed(() => saving.value || props.deleting)
const error = ref('')
const errorNotice = ref<HTMLElement | null>(null)
const clientKey = newClientKey()

function showError(message: string) {
  error.value = message
  void nextTick(() => errorNotice.value?.focus())
}

async function submit() {
  if (locked.value || photoProcessing.value) return
  error.value = ''
  if (!day.value || !time.value) {
    showError('请选择运动日期和时间。')
    return
  }
  const startedAt = original && day.value === originalDay && time.value === originalTime
    ? original.started_at : toZonedIso(day.value, time.value)
  if (startedAt !== original?.started_at && Date.parse(startedAt) > Date.now()) {
    showError('运动时间不能晚于现在。')
    return
  }
  const rest = activity.value === 'rest'
  const duration = !rest && minutes.value.trim() ? Number(minutes.value) : null
  if (duration !== null && (!/^\d+$/.test(minutes.value.trim()) || !Number.isInteger(duration) || duration < 1 || duration > 1440)) {
    showError('请输入 1 到 1440 分钟之间的整数。')
    return
  }
  const payload: CheckinInput = {
    activity_code: activity.value, started_at: startedAt, duration_minutes: duration,
    effort: rest ? null : effort.value, feeling_code: feeling.value,
    ...(photo.value !== undefined ? { photo: photo.value } : {})
  }
  saving.value = true
  const epoch = currentEpoch()
  try {
    const entry = original ? await updateCheckin(original.id, payload) : await saveCheckin(payload, clientKey)
    if (epoch === currentEpoch()) emit('saved', entry)
  } catch (failure) {
    if (epoch !== currentEpoch() || failure instanceof StaleSessionError) return
    showError(failure instanceof ApiRequestError ? failure.message : '这次记录未保存，请重试。')
  } finally {
    saving.value = false
  }
}
</script>

<style scoped>
.exercise-time { display: grid; grid-template-columns: minmax(0, 1.2fr) minmax(0, 1fr); gap: 10px; }
.form-block { margin: 12px 0; }
.form-block .hr-field-label { margin-bottom: 5px; }
.form-chips { display: flex; flex-wrap: wrap; gap: 6px; }
.form-chip {
  min-height: 44px; padding: 6px 10px; border: 1px solid var(--hr-line-strong);
  background: var(--hr-paper); border-radius: 999px; color: var(--hr-ink-2);
  font: 13px var(--hr-font);
}
.form-chip[aria-pressed='true'] { background: var(--hr-rose-soft); color: var(--hr-rose-deep); border-color: var(--hr-rose); }
.manage { display: flex; flex-wrap: wrap; justify-content: space-between; gap: 8px; border-top: 1px solid var(--hr-line); }
.remove { color: var(--hr-danger); }
</style>
