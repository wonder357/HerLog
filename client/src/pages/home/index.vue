<template>
  <view class="hr-page hr-tab-page home-page">
    <SkinCapture v-if="captureVisible" return-label="返回首页" @saved="afterCapture" @close="closeCapture" />
    <div v-show="!captureVisible">
      <header class="welcome">
        <div class="welcome-text">
          <p>{{ dateLabel }}</p>
          <h1>{{ auth.username ? '你好，' + auth.username : '你好' }}</h1>
          <img class="welcome-art" src="/static/home-cosmos.png" alt="" />
        </div>
        <H5Button class="cycle-status" @click="go('period')">
          <span class="phase-ring" :class="{ known: statusBasis === '已记录', estimated: statusBasis === '日期估算' }" aria-hidden="true">
            <HerlogIcon name="period" />
          </span>
          <span><strong>{{ statusLabel }}</strong><small>{{ statusBasis }}</small></span>
        </H5Button>
      </header>

      <section v-if="data && preferences.show_focus && !focusClosed" class="focus card" aria-labelledby="focus-title">
        <div class="focus-copy">
          <h2 id="focus-title">今日聚焦</h2>
          <p>{{ focusCopy[data.focus.message_key] }}</p>
        </div>
        <H5Button class="focus-close" aria-label="关闭今日聚焦" @click="focusClosed = true"><HerlogIcon name="close" /></H5Button>
        <H5Button class="hr-action focus-action" :disabled="feelingLoading" @click="runFocus">{{ focusActions[data.focus.action] }} ›</H5Button>
      </section>

      <section class="quick-section" aria-labelledby="quick-title">
        <h2 id="quick-title" class="hr-section-title">快捷记录</h2>
        <div class="shortcuts">
          <H5Button v-for="item in shortcuts" :key="item.key" class="shortcut" :class="item.key"
            :disabled="item.key === 'feeling' && feelingLoading" @click="runShortcut(item.key)">
            <span class="shortcut-symbol"><HerlogIcon :name="item.icon" /></span><span>{{ item.label }}</span>
          </H5Button>
        </div>
        <div v-if="data" class="checkins">
          <H5Button class="hr-action" :aria-expanded="checkins" @click="checkins = !checkins">{{ checkins ? '收起今日记录' : '查看今日记录' }} {{ checkins ? '−' : '+' }}</H5Button>
          <span v-if="!checkins && recordedCount" class="muted">已记 {{ recordedCount }} 类</span>
          <div v-if="checkins" class="checkin-items">
            <H5Button v-for="item in shortcuts" :key="item.key" class="ghost" :disabled="item.key === 'feeling' && feelingLoading"
              @click="runShortcut(item.key)">{{ item.short }} <span>{{ data.today_recorded[item.key] ? '已记录' : '可补记' }}</span></H5Button>
          </div>
        </div>
      </section>

      <AssistantChat ref="assistant" :key="assistantKey" :examples="examples" :show-questions="preferences.show_questions"
        @reference="openRef" />
      <section v-if="preferences.show_summary" class="card summary">
        <H5Button class="summary-toggle" :aria-expanded="summaryOpen" @click="summaryOpen = !summaryOpen">
          <span><strong>本周已记录 {{ data?.week.recorded_days ?? '—' }} 天</strong><small v-if="preferences.weekly_record_days_target">每周记录目标 {{ preferences.weekly_record_days_target }} 天</small></span>
          <span>{{ summaryOpen ? '收起' : '健康摘要 ›' }}</span>
        </H5Button>
        <div v-if="summaryOpen" class="summary-detail">
          <H5Button v-for="item in summaryItems" :key="item.page" class="hr-action" @click="go(item.page)">{{ item.text }}</H5Button>
        </div>
      </section>

      <div v-if="loadError" class="card error-row" role="alert">
        <span>{{ loadError }}</span><H5Button class="hr-action" @click="refresh">重试</H5Button>
      </div>
      <RecordCalendar :today="today" :selected="selected" :data="selectedData" :prediction="prediction"
        :recorded="data?.week.days" :loading="calendarLoading" :error="calendarError"
        @open="openCalendar" @close="selected = null" @retry="retryCalendar" @details="go" />

      <WeightForm :visible="weightVisible" @close="weightVisible = false" @saved="saved" />
      <PeriodForm :visible="periodVisible" :day="today" :open-period="openPeriod" selectable-day @close="periodVisible = false" @saved="saved">
        <template #extra-action="{ day, disabled }">
          <H5Button class="ghost" :disabled="disabled || feelingLoading || !day || day > today" @click="openFeeling(day)">记感受</H5Button>
        </template>
      </PeriodForm>
      <FeelingForm :visible="feelingVisible" :day="feelingDay" :existing="existingFeeling" @close="feelingVisible = false" @saved="saved" />
      <TabBar current="/pages/home/index" />
    </div>
  </view>
</template>

<script setup lang="ts">
import { computed, nextTick, ref, watch } from 'vue'
import { onHide, onShow } from '@dcloudio/uni-app'
import H5Button from '../../components/H5Button'
import HerlogIcon from '../../components/HerlogIcon.vue'
import TabBar from '../../components/TabBar.vue'
import WeightForm from '../../components/WeightForm.vue'
import PeriodForm from '../../components/PeriodForm.vue'
import FeelingForm from '../../components/FeelingForm.vue'
import RecordCalendar from './RecordCalendar.vue'
import AssistantChat from './AssistantChat.vue'
import SkinCapture from '../skin/SkinCapture.vue'
import { TIME_ZONE, todayString } from '../../shared/dates'
import { suggestedQuestions } from '../../shared/home'
import { useAuthStore } from '../../stores/auth'
import { ApiRequestError, currentEpoch } from '../../services/httpClient'
import { fetchHome, fetchRecordingPreferences, recordingDefaults } from '../../services/homeService'
import type { HomeOverview } from '../../services/homeService'
import { listFeelings } from '../../services/periodService'
import type { FeelingItem, RecordRef } from '../../services/types'

const auth = useAuthStore()
const today = ref(todayString())
const data = ref<HomeOverview | null>(null)
const otherMonth = ref<HomeOverview | null>(null)
const preferences = ref({ ...recordingDefaults })
const selected = ref<string | null>(null)
const loading = ref(false)
const otherLoading = ref(false)
const loadError = ref('')
const otherError = ref('')
const focusClosed = ref(false)
const summaryOpen = ref(false)
const checkins = ref(false)
const weightVisible = ref(false)
const periodVisible = ref(false)
const captureVisible = ref(false)
const feelingVisible = ref(false)
const feelingLoading = ref(false)
const feelingDay = ref(today.value)
const existingFeeling = ref<FeelingItem | null>(null)
const assistant = ref<{ close(): void } | null>(null)
const assistantKey = ref(0)
let overviewSequence = 0
let calendarSequence = 0
let formSequence = 0
let settingsSequence = 0
let captureScroll = 0
let captureFocus: HTMLElement | null = null

const shortcuts = [
  { key: 'period', label: '记经期', short: '经期', icon: 'period' },
  { key: 'feeling', label: '记感受', short: '感受', icon: 'rest' },
  { key: 'weight', label: '记体重', short: '体重', icon: 'weight' },
  { key: 'skin', label: '拍皮肤', short: '皮肤', icon: 'camera' }
] as const
type Shortcut = typeof shortcuts[number]['key']
type Tab = 'period' | 'weight' | 'skin'
const focusCopy = {
  review_today: '今天已有记录，可以回看当天摘要。',
  review_periods: '可以回看已经记下的实际经期日期。',
  review_month: '可以看看本月已经记下的日期。',
  record_period: '可以先记一次实际经期开始日。',
  record_feeling_simple: '想记下今天的感受，可以选一项。',
  record_feeling: '如果愿意，可以记下今天的感受。'
}
const focusActions = {
  review_today: '回看今天', open_period: '查看经期', open_calendar: '查看月历',
  record_period: '记录经期', record_feeling: '记录感受'
}
const dateLabel = computed(() => new Intl.DateTimeFormat('zh-CN', {
  timeZone: TIME_ZONE, month: 'long', day: 'numeric', weekday: 'long'
}).format(new Date(today.value + 'T00:00:00+08:00')))
const statusLabel = computed(() => {
  if (!data.value) return loading.value ? '读取周期…' : '周期暂不可用'
  if (data.value.active_mode === 'trying_to_conceive') return '备孕记录'
  return { menstrual: '月经期', follicular: '卵泡期', ovulatory: '排卵相关阶段', luteal: '黄体期', unknown: '阶段待记录' }[data.value.cycle_context.phase]
})
const statusBasis = computed(() => {
  if (!data.value) return '查看经期'
  if (data.value.active_mode === 'trying_to_conceive') return '查看实际记录'
  return { recorded: '已记录', estimated: '日期估算', unknown: '查看经期' }[data.value.cycle_context.basis]
})
const examples = computed(() => suggestedQuestions(data.value?.active_mode === 'trying_to_conceive'
  ? 'follicular' : data.value?.cycle_context.phase ?? 'unknown', !!data.value?.week.has_weight, !!data.value?.week.has_skin))
const summaryItems = computed<Array<{ page: Tab; text: string }>>(() => [
  { page: 'period', text: !data.value ? '查看经期' : data.value.has_period_history ? '已有经期记录' : '还没有经期记录' },
  { page: 'weight', text: !data.value ? '查看体重' : data.value.week.has_weight ? '本周有体重记录' : '本周暂无体重记录' },
  { page: 'skin', text: !data.value ? '查看皮肤' : data.value.week.has_skin ? '本周有皮肤观察' : '本周暂无皮肤观察' }
])
const currentMonth = computed(() => today.value.slice(0, 7))
const calendarMonth = computed(() => selected.value?.slice(0, 7))
const selectedData = computed(() => calendarMonth.value === currentMonth.value ? data.value : otherMonth.value)
const calendarError = computed(() => calendarMonth.value === currentMonth.value ? loadError.value : otherError.value)
const calendarLoading = computed(() => calendarMonth.value === currentMonth.value ? loading.value : otherLoading.value)
const prediction = computed(() => data.value?.period_prediction.expected_start ?? null)
const openPeriod = computed(() => data.value?.open_period
  ? { id: data.value.open_period.id, startDay: data.value.open_period.start_day } : null)
const recordedCount = computed(() => Object.values(data.value?.today_recorded ?? {}).filter(Boolean).length)

async function refresh() {
  const sequence = ++overviewSequence
  const epoch = currentEpoch()
  const active = () => sequence === overviewSequence && epoch === currentEpoch()
  loadError.value = ''
  loading.value = true
  try {
    const result = await fetchHome(currentMonth.value)
    if (active()) data.value = result
  } catch {
    if (active()) loadError.value = '暂时无法读取记录。'
  } finally {
    if (active()) loading.value = false
  }
}

async function loadMonth(month: string) {
  const sequence = ++calendarSequence
  const epoch = currentEpoch()
  const active = () => sequence === calendarSequence && epoch === currentEpoch()
  otherMonth.value = null
  otherError.value = ''
  otherLoading.value = true
  try {
    const result = await fetchHome(month)
    if (active()) otherMonth.value = result
  } catch {
    if (active()) otherError.value = '这个月的记录暂时不可用。'
  } finally {
    if (active()) otherLoading.value = false
  }
}

function openCalendar(day: string) {
  const previous = calendarMonth.value
  selected.value = day
  if (calendarMonth.value !== previous && calendarMonth.value !== currentMonth.value) void loadMonth(day.slice(0, 7))
}

function retryCalendar() {
  if (!calendarMonth.value || calendarMonth.value === currentMonth.value) void refresh()
  else void loadMonth(calendarMonth.value)
}

function go(page: Tab) {
  selected.value = null
  uni.switchTab({ url: '/pages/' + page + '/index' })
}

function openRef(reference: RecordRef) {
  const page = (['period', 'weight', 'skin'] as const).find(tab => reference.route === '/pages/' + tab + '/index')
  if (!page) return
  if (reference.id === 'entry') runShortcut(page)
  else go(page)
}

function runFocus() {
  const action = data.value?.focus.action
  if (action === 'record_feeling') void openFeeling(today.value)
  else if (action === 'record_period') periodVisible.value = true
  else if (action === 'open_period') go('period')
  else openCalendar(today.value)
}

function runShortcut(kind: Shortcut) {
  if (kind === 'period') periodVisible.value = true
  else if (kind === 'weight') weightVisible.value = true
  else if (kind === 'feeling') void openFeeling(today.value)
  else {
    captureScroll = window.scrollY
    captureFocus = document.activeElement instanceof HTMLElement ? document.activeElement : null
    captureVisible.value = true
    void nextTick(() => window.scrollTo(0, 0))
  }
}

function closeCapture() {
  captureVisible.value = false
  void nextTick(() => {
    window.scrollTo(0, captureScroll)
    captureFocus?.focus({ preventScroll: true })
    captureFocus = null
  })
}

async function openFeeling(day: string) {
  if (feelingLoading.value) return
  const epoch = currentEpoch()
  const request = ++formSequence
  const active = () => epoch === currentEpoch() && request === formSequence
  feelingLoading.value = true
  try {
    const rows = await listFeelings(day, day)
    if (!active()) return
    feelingDay.value = day
    existingFeeling.value = rows.find(row => row.day === day) ?? null
    periodVisible.value = false
    feelingVisible.value = true
  } catch (failure) {
    if (active()) uni.showToast({ title: failure instanceof ApiRequestError ? failure.message : '感受读取失败', icon: 'none' })
  } finally {
    if (active()) feelingLoading.value = false
  }
}

function saved() {
  weightVisible.value = periodVisible.value = feelingVisible.value = false
  existingFeeling.value = null
  void refresh()
  uni.showToast({ title: '已保存', icon: 'none' })
}

function afterCapture() {
  closeCapture()
  saved()
}

function reset() {
  overviewSequence += 1
  calendarSequence += 1
  formSequence += 1
  assistantKey.value += 1
  settingsSequence += 1
  data.value = otherMonth.value = null
  selected.value = null
  existingFeeling.value = null
  focusClosed.value = summaryOpen.value = checkins.value = false
  weightVisible.value = periodVisible.value = feelingVisible.value = captureVisible.value = false
  loading.value = otherLoading.value = feelingLoading.value = false
  loadError.value = otherError.value = ''
  preferences.value = { ...recordingDefaults }
}

watch(() => [auth.token, auth.privateCacheRevision], reset, { flush: 'sync' })
onHide(() => {
  assistant.value?.close()
  formSequence += 1
  selected.value = null
  captureVisible.value = periodVisible.value = weightVisible.value = feelingVisible.value = feelingLoading.value = false
  existingFeeling.value = null
})
onShow(() => {
  if (!auth.isLoggedIn) {
    uni.reLaunch({ url: '/pages/login/index' })
    return
  }
  today.value = todayString()
  void refresh()
  const request = ++settingsSequence
  const epoch = currentEpoch()
  void fetchRecordingPreferences().then(result => {
    if (request === settingsSequence && epoch === currentEpoch()) preferences.value = result
  }).catch(() => undefined)
})
</script>

<style scoped>
.home-page { min-width:0; }
.welcome { display:flex; justify-content:space-between; gap:8px; align-items:center; margin:4px 0 16px; }
.welcome-text { min-width:0; position:relative; padding-inline-end:52px; }
.welcome-art { position:absolute; inset-inline-end:0; top:0; width:48px; height:48px; object-fit:contain; }
.welcome p { margin:0 0 4px; color:var(--hr-ink-2); font-size:13px; }
.welcome h1 { margin:0; color:var(--hr-ink); font-size:clamp(23px,6vw,32px); line-height:1.2; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
.cycle-status { flex-shrink:0; min-height:49px; display:flex; align-items:center; gap:7px; text-align:left; border:0; background:transparent; padding:2px 0; color:var(--hr-ink); }
.cycle-status strong,.cycle-status small { display:block; }
.cycle-status strong { font-size:13px; }
.cycle-status small { font-size:12px; color:var(--hr-ink-2); }
.phase-ring { display:grid; place-items:center; width:40px; height:40px; border:2px dotted var(--hr-line-strong); border-radius:50%; color:var(--hr-rose-deep); background:var(--hr-surface); }
.phase-ring.known { border:2px solid var(--hr-rose); background:var(--hr-rose-soft); }
.phase-ring.estimated { border:2px dashed var(--hr-rose); }
.phase-ring svg,.focus-close svg { width:20px; height:20px; }
.focus { display:grid; grid-template-columns:minmax(0,1fr) 44px; background:linear-gradient(115deg,var(--hr-rose-soft),var(--hr-peach)); padding:12px 12px 7px 15px; align-items:start; }
.focus h2 { margin:0 0 5px; color:var(--hr-rose-deep); font-size:14px; }
.focus p { margin:0; font-size:15px; overflow-wrap:anywhere; }
.focus-action { justify-self:start; padding-left:0; }
.focus-close { display:grid; place-items:center; min-height:44px; background:transparent; color:var(--hr-ink-2); border:0; border-radius:12px; }
.quick-section { margin-bottom:12px; }
.quick-section h2 { margin:16px 0 8px; }
.shortcuts { display:grid; grid-template-columns:repeat(4,minmax(0,1fr)); gap:7px; }
.shortcut { display:grid; justify-items:center; align-items:center; min-height:72px; gap:4px; padding:7px 2px; border:1px solid var(--hr-line); border-radius:15px; background:var(--hr-surface); color:var(--hr-ink); font-size:13px; font-weight:650; overflow-wrap:anywhere; }
.shortcut-symbol { display:grid; place-items:center; width:35px; height:35px; border-radius:11px; background:var(--hr-rose-soft); color:var(--hr-rose-deep); }
.shortcut-symbol svg { width:20px; height:20px; }
.shortcut.weight .shortcut-symbol { background:var(--hr-peach); color:var(--hr-peach-ink); }
.shortcut.skin .shortcut-symbol { background:var(--hr-plum-soft); color:var(--hr-plum); }
.shortcut.feeling .shortcut-symbol { background:var(--hr-taupe-soft); color:var(--hr-taupe); }
.checkins { display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; }
.checkins > .hr-action { padding-left:1px; }
.checkin-items { display:grid; width:100%; grid-template-columns:repeat(2,minmax(0,1fr)); gap:6px; }
.checkin-items button { gap:5px; font-size:13px; }
.checkin-items span { color:var(--hr-ink-2); }
.summary { padding:5px 14px; }
.summary-toggle { display:flex; align-items:center; justify-content:space-between; text-align:left; width:100%; gap:6px; min-height:48px; padding:3px 0; border:0; background:transparent; color:var(--hr-ink); font-size:13px; }
.summary-toggle small { display:block; color:var(--hr-ink-2); font-size:12px; }
.summary-toggle > span:last-child { color:var(--hr-rose-deep); }
.summary-detail { border-top:1px solid var(--hr-line); display:grid; justify-items:start; }
.summary-detail .hr-action { padding-inline:0; font-size:13px; }
.error-row { display:flex; align-items:center; justify-content:space-between; gap:8px; font-size:13px; color:var(--hr-danger); padding-block:3px; }
@media (max-width:350px) { .shortcuts { grid-template-columns:repeat(2,minmax(0,1fr)); } }
</style>
