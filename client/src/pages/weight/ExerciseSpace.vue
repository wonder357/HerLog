<template>
  <view class="exercise-space">
    <view class="exercise-hero">
      <text class="headline">今天想怎么动？</text>
      <text v-if="phase" class="phase">{{ phaseNames[phase.phase] }}{{ phase.basis === 'estimated' ? ' · 估算' : '' }}</text>
      <view>从舒服的节奏开始，休息也可以记下来。</view>
      <H5Button class="soft" @click="cycle = !cycle; loadCards()">{{ cycle ? '关闭周期推荐' : '按周期推荐' }}</H5Button>
    </view>
    <view v-if="error" class="exercise-error" role="alert">{{ error }} <H5Button class="soft" @click="load">重试</H5Button></view>
    <view v-if="loading" class="quiet" role="status">正在读取运动卡…</view>
    <view class="exercise-cards">
      <view v-for="card in cards" :key="card.activity_code" class="exercise-card">
        <view class="exercise-symbol"><HerlogIcon :name="card.activity_code" /></view>
        <view class="card-name">{{ card.title }}</view>
        <view class="quiet">{{ card.instructions }}</view>
        <H5Button class="soft" @click="begin(card.activity_code)">记一次{{ card.title }}</H5Button>
      </view>
    </view>
    <view v-if="selected" class="card checkin-form">
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
      <view v-if="formError" class="exercise-error" role="alert">{{ formError }}</view>
      <view class="buttons">
        <H5Button class="soft" :disabled="saving" @click="selected = null">取消</H5Button>
        <H5Button class="exercise-primary" :disabled="saving" @click="save">{{ saving ? '保存中…' : '保存打卡' }}</H5Button>
      </view>
    </view>
    <view class="exercise-history">
      <view class="headline">我的运动记录</view>
      <view v-if="!entries.length" class="quiet">你可以从一次散步或休息开始。</view>
      <view v-for="entry in entries" :key="entry.id" class="exercise-record">
        <view>
          <view class="card-name">{{ activities[entry.activity_code] }}</view>
          <view class="quiet">{{ formatMoment(entry.started_at) }}<text v-if="entry.duration_minutes"> · {{ entry.duration_minutes }} 分钟</text><text v-if="entry.effort"> · {{ effortNames[entry.effort] }}</text></view>
        </view>
        <view class="buttons">
          <H5Button class="soft" @click="share(entry)">预览分享</H5Button>
          <H5Button class="soft" @click="remove(entry.id)">删除</H5Button>
        </view>
      </view>
    </view>
  </view>
</template>

<script setup lang="ts">
import H5Button from '../../components/H5Button'
import HerlogIcon from '../../components/HerlogIcon.vue'
import { onBeforeUnmount, onMounted, ref } from 'vue'
import { currentTime, formatMoment, todayString, toZonedIso } from '../../shared/dates'
import { currentEpoch } from '../../services/httpClient'
import { newClientKey } from '../../services/weightService'
import { activities, deleteCheckin, exerciseCards, exerciseHistory, phaseNames, saveCheckin } from '../../services/wellnessService'
import type { Activity, Checkin, CheckinInput, CycleDay, ExerciseCard, ShareReference } from '../../services/wellnessService'

const emit = defineEmits<{ share: [ShareReference] }>()
const selected = ref<Activity | null>(null)
const cards = ref<ExerciseCard[]>([])
const phase = ref<CycleDay | null>(null)
const entries = ref<Checkin[]>([])
const cycle = ref(true)
const day = ref(todayString())
const time = ref(currentTime())
const minutes = ref('')
const effort = ref<CheckinInput['effort']>(null)
const loading = ref(false)
const saving = ref(false)
const error = ref('')
const formError = ref('')
const effortNames = { easy: '轻松', moderate: '适中', hard: '比较吃力' }
const efforts = Object.entries(effortNames).map(([code, title]) => ({ code: code as keyof typeof effortNames, title }))
let clientKey = newClientKey()
let active = true
let recommendationVersion = 0
const epoch = currentEpoch()
const isActive = () => active && epoch === currentEpoch()
onBeforeUnmount(() => { active = false })
onMounted(load)

async function loadCards() {
  const version = ++recommendationVersion
  try {
    const data = await exerciseCards(cycle.value)
    if (isActive() && version === recommendationVersion) {
      cards.value = data.cards
      phase.value = data.phase
    }
  } catch {
    if (isActive() && version === recommendationVersion) error.value = '运动卡没有加载成功'
  }
}

async function load() {
  loading.value = true
  error.value = ''
  try {
    const [history] = await Promise.all([exerciseHistory(), loadCards()])
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
  formError.value = ''
  clientKey = newClientKey()
}

async function save() {
  const activity = selected.value
  if (!activity || saving.value) return
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
      effort: effort.value
    }, clientKey)
    if (!isActive()) return
    selected.value = null
    entries.value = [entry, ...entries.value.filter(item => item.id !== entry.id)]
    uni.showToast({ title: activity === 'rest' ? '已记下今天的休息' : '已记下这次活动', icon: 'none' })
  } catch {
    if (isActive()) formError.value = '这次打卡未保存，请重试'
  } finally {
    saving.value = false
  }
}

function share(entry: Checkin) {
  emit('share', { checkin_id: entry.id, activity: activities[entry.activity_code], duration: entry.duration_minutes })
}

function remove(id: number) {
  uni.showModal({
    title: '删除这次打卡？', content: '这次打卡的相关分享也会撤回。',
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
.phase { padding: 4px 9px; border-radius: 999px; background: var(--hr-plum-soft); color: var(--hr-plum); font-size: 12px; }
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
