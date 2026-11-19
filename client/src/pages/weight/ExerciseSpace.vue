<template>
  <view class="exercise-space">
    <view class="exercise-hero">
      <text class="headline">运动打卡</text>
    </view>
    <view v-if="error" class="exercise-error" role="alert">{{ error }} <H5Button class="soft" @click="load">重试</H5Button></view>
    <view v-if="loading" class="quiet" role="status">正在读取运动记录…</view>
    <view class="exercise-cards">
      <view v-for="activity in activityOptions" :key="activity" class="exercise-card">
        <view class="exercise-symbol"><HerlogIcon :name="activity" /></view>
        <H5Button class="soft" :disabled="saving || photoProcessing" @click="begin(activity)">记{{ activities[activity] }}</H5Button>
      </view>
    </view>
    <view v-if="selected" :key="clientKey" class="card checkin-form">
      <view class="headline">记录{{ activities[selected] }}</view>
      <picker mode="date" :value="day" :end="todayString()" @change="day = $event.detail.value">
        <view class="field">{{ day }}</view>
      </picker>
      <picker mode="time" :value="time" @change="time = $event.detail.value">
        <view class="field">{{ time }}</view>
      </picker>
      <template v-if="selected !== 'rest'">
        <input v-model="minutes" class="field" type="number" placeholder="时长（分钟，选填）" />
        <view class="buttons">
          <H5Button v-for="option in efforts" :key="option.code" class="soft"
            :class="{ active: effort === option.code }" @click="effort = effort === option.code ? null : option.code">{{ option.title }}</H5Button>
        </view>
      </template>
      <PrivatePhotoEditor v-model="photo" v-model:processing="photoProcessing" label="运动照片" :disabled="saving" />
      <view v-if="formError" class="exercise-error" role="alert">{{ formError }}</view>
      <view class="buttons">
        <H5Button class="soft" :disabled="saving" @click="cancelCheckin">取消</H5Button>
        <H5Button class="exercise-primary" :disabled="saving || photoProcessing" @click="save">{{ saving ? '保存中…' : '保存打卡' }}</H5Button>
      </view>
    </view>
    <view class="exercise-history">
      <view class="headline">我的运动记录</view>
      <view v-if="!loading && !entries.length" class="quiet">暂无运动记录</view>
      <view v-for="entry in entries" :key="entry.id" class="exercise-record">
        <view>
          <view class="card-name">{{ activities[entry.activity_code] }}</view>
          <view class="quiet">{{ formatMoment(entry.started_at) }}<text v-if="entry.duration_minutes"> · {{ entry.duration_minutes }} 分钟</text><text v-if="entry.effort"> · {{ effortNames[entry.effort] }}</text></view>
        </view>
        <view class="buttons">
          <H5Button class="soft" @click="openPhoto(entry)">{{ entry.has_photo ? '查看照片' : '添加照片' }}</H5Button>
          <H5Button class="soft" @click="share(entry)">发起讨论</H5Button>
          <H5Button class="soft" @click="remove(entry.id)">删除</H5Button>
        </view>
      </view>
    </view>
    <HerlogSheet v-if="photoEntry" title="运动照片" :context="formatMoment(photoEntry.started_at)"
      :busy="photoSaving" @close="closePhoto">
      <PrivatePhotoEditor v-model="photoChange" v-model:processing="editProcessing" label="打卡照片"
        :saved-path="photoEntry.has_photo ? checkinPhotoPath(photoEntry.id) : undefined" :disabled="photoSaving" />
      <view v-if="photoError" class="exercise-error" role="alert">{{ photoError }}</view>
      <template #actions>
        <H5Button class="exercise-primary" :disabled="photoSaving || editProcessing || photoChange === undefined"
          @click="savePhoto">{{ photoSaving ? '保存中…' : '保存照片' }}</H5Button>
      </template>
    </HerlogSheet>
  </view>
</template>

<script setup lang="ts">
import H5Button from '../../components/H5Button'
import HerlogIcon from '../../components/HerlogIcon.vue'
import HerlogSheet from '../../components/HerlogSheet.vue'
import PrivatePhotoEditor from '../../components/PrivatePhotoEditor.vue'
import { onBeforeUnmount, onMounted, ref } from 'vue'
import { currentTime, formatMoment, todayString, toZonedIso } from '../../shared/dates'
import { ApiRequestError, currentEpoch } from '../../services/httpClient'
import { checkinPhotoPath } from '../../services/privatePhotoService'
import type { PrivatePhotoPayload } from '../../services/privatePhotoService'
import { newClientKey } from '../../services/weightService'
import { activities, deleteCheckin, exerciseHistory, saveCheckin, updateCheckinPhoto } from '../../services/wellnessService'
import type { Activity, Checkin, CheckinInput, ShareReference } from '../../services/wellnessService'

const emit = defineEmits<{ share: [ShareReference] }>()
const selected = ref<Activity | null>(null)
const activityOptions = Object.keys(activities) as Activity[]
const entries = ref<Checkin[]>([])
const day = ref(todayString())
const time = ref(currentTime())
const minutes = ref('')
const effort = ref<CheckinInput['effort']>(null)
const photo = ref<PrivatePhotoPayload | null>()
const photoProcessing = ref(false)
const photoEntry = ref<Checkin | null>(null)
const photoChange = ref<PrivatePhotoPayload | null>()
const editProcessing = ref(false)
const photoSaving = ref(false)
const photoError = ref('')
const loading = ref(false)
const saving = ref(false)
const error = ref('')
const formError = ref('')
const effortNames = { easy: '轻松', moderate: '适中', hard: '比较吃力' }
const efforts = Object.entries(effortNames).map(([code, title]) => ({ code: code as keyof typeof effortNames, title }))
let clientKey = newClientKey()
let active = true
const epoch = currentEpoch()
const isActive = () => active && epoch === currentEpoch()
onBeforeUnmount(() => { active = false })
onMounted(load)

async function load() {
  loading.value = true
  error.value = ''
  try {
    const history = await exerciseHistory()
    if (isActive()) entries.value = history
  } catch {
    if (isActive()) error.value = '运动记录没有加载成功'
  } finally {
    loading.value = false
  }
}

function begin(activity: Activity) {
  selected.value = activity
  day.value = todayString()
  time.value = currentTime()
  minutes.value = ''
  effort.value = null
  photo.value = undefined
  formError.value = ''
  clientKey = newClientKey()
}

function cancelCheckin() {
  selected.value = null
  photo.value = undefined
}

async function save() {
  const activity = selected.value
  if (!activity || saving.value || photoProcessing.value) return
  const duration = minutes.value.trim() ? Number(minutes.value) : null
  if (duration !== null && (!Number.isInteger(duration) || duration < 1 || duration > 1440)) {
    formError.value = '请输入 1 到 1440 分钟之间的整数'
    return
  }
  saving.value = true
  formError.value = ''
  try {
    const entry = await saveCheckin({
      activity_code: activity,
      started_at: toZonedIso(day.value, time.value),
      duration_minutes: duration,
      effort: effort.value,
      ...(photo.value ? { photo: photo.value } : {})
    }, clientKey)
    if (!isActive()) return
    cancelCheckin()
    entries.value = [entry, ...entries.value.filter(item => item.id !== entry.id)]
    uni.showToast({ title: activity === 'rest' ? '已记下今天的休息' : '已记下这次活动', icon: 'none' })
  } catch (failure) {
    if (isActive()) formError.value = failure instanceof ApiRequestError ? failure.message : '这次打卡未保存，请重试'
  } finally {
    saving.value = false
  }
}

function openPhoto(entry: Checkin) {
  photoChange.value = undefined
  photoError.value = ''
  photoEntry.value = entry
}

function closePhoto() {
  photoEntry.value = null
  photoChange.value = undefined
}

async function savePhoto() {
  if (!photoEntry.value || photoChange.value === undefined || photoSaving.value || editProcessing.value) return
  photoSaving.value = true
  photoError.value = ''
  try {
    const entry = await updateCheckinPhoto(photoEntry.value.id, photoChange.value)
    if (!isActive()) return
    entries.value = entries.value.map(item => item.id === entry.id ? entry : item)
    closePhoto()
    uni.showToast({ title: '运动照片已更新', icon: 'none' })
  } catch (failure) {
    if (isActive()) photoError.value = failure instanceof ApiRequestError ? failure.message : '照片保存失败，请重试。'
  } finally {
    photoSaving.value = false
  }
}

function share(entry: Checkin) {
  emit('share', { checkin_id: entry.id, activity: activities[entry.activity_code] })
}

function remove(id: number) {
  uni.showModal({
    title: '删除这次打卡？', content: '打卡照片将一并删除，关联的讨论和分享也会撤回。',
    success: async result => {
      if (!result.confirm || !isActive()) return
      try {
        await deleteCheckin(id)
        if (isActive()) entries.value = entries.value.filter(entry => entry.id !== id)
      } catch {
        if (isActive()) error.value = '删除未完成，请重试'
      }
    }
  })
}
</script>

<style scoped>
.exercise-space { display: grid; gap: 12px; color: var(--hr-ink); }
.exercise-hero {
  padding: 18px; border-radius: var(--hr-radius-lg); background: var(--hr-peach);
  border: 1px solid var(--hr-line); display: grid; justify-items: start; gap: 8px;
}
.headline { font-size: 19px; font-weight: 680; }
.quiet { font-size: 13px; color: var(--hr-ink-2); }
.exercise-cards { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 8px; }
.exercise-card,.exercise-history { background: var(--hr-surface); border: 1px solid var(--hr-line); border-radius: var(--hr-radius); padding: 12px; }
.exercise-card { display: flex; flex-direction: column; gap: 8px; }
.exercise-card .soft { margin-top: auto; }
.card-name { font-size: 15px; font-weight: 650; }
.exercise-symbol {
  display: grid; place-items: center; width: 38px; height: 38px; border-radius: 11px;
  color: var(--hr-rose-deep); background: var(--hr-rose-soft);
}
.exercise-symbol svg { width: 21px; height: 21px; }
.soft,.exercise-primary {
  padding: 7px 10px; min-height: 44px; border: 1px solid var(--hr-line);
  border-radius: 999px; font-size: 13px; line-height: 1.35; color: var(--hr-rose-deep); background: var(--hr-paper);
}
.soft.active,.exercise-primary { background: var(--hr-rose); color: white; border-color: var(--hr-rose); }
.buttons { display: flex; gap: 8px; flex-wrap: wrap; }
.exercise-record { display: flex; flex-wrap: wrap; justify-content: space-between; align-items: center; gap: 8px; padding: 10px 0; border-bottom: 1px solid var(--hr-line); }
.exercise-error { font-size: 13px; color: var(--hr-danger); background: var(--hr-danger-soft); padding: 10px; border-radius: 10px; }
.checkin-form .headline { margin-bottom: 10px; }
</style>
