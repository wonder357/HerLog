<template>
  <view class="hr-page hr-tab-page home-page" :class="{ 'home-capture': captureVisible }">
    <SkinCapture v-if="captureVisible" return-label="返回首页" @saved="afterCapture" @close="closeCapture" />
    <div v-if="auth.isLoggedIn" v-show="!captureVisible">
      <AssistantChat ref="assistant" :key="assistantKey" :record-questions="recordQuestions" :starters="starters"
        :show-questions="preferences.show_questions" :date-label="dateLabel" :visible="pageVisible && !captureVisible"
        @reference="openRef" @keyboard="keyboardOpen = $event"
        @shortcut="runShortcut" @today-records="recordsVisible = true" :feeling-loading="feelingLoading" />

      <HerlogSheet v-if="recordsVisible" title="今日记录" :context="dateLabel" @close="recordsVisible = false">
        <div class="summary-header">
          <H5Button class="cycle-status" @click="go('period')">
            <span class="phase-ring" :class="{ known: statusBasis === '已记录', estimated: statusBasis === '日期估算' }" aria-hidden="true">
              <HerlogIcon name="period" />
            </span>
            <span><strong>{{ statusLabel }}</strong><small>{{ statusBasis }}</small></span>
          </H5Button>
          <H5Button class="hr-action" @click="openCalendar(today)">打开月历 ›</H5Button>
        </div>
        <div v-if="data" class="checkin-items">
          <H5Button v-for="item in shortcuts" :key="item.key" class="ghost" :disabled="item.key === 'feeling' && feelingLoading"
            @click="runShortcut(item.key)">{{ item.short }} <span>{{ data.today_recorded[item.key] ? '已记录' : '可补记' }}</span></H5Button>
        </div>
        <section v-if="data && preferences.show_focus && !focusClosed" class="focus card" aria-labelledby="focus-title">
          <div class="focus-copy">
            <h2 id="focus-title">今日聚焦</h2>
            <p>{{ focusCopy[data.focus.message_key] }}</p>
          </div>
          <H5Button class="focus-close" aria-label="关闭今日聚焦" @click="focusClosed = true"><HerlogIcon name="close" /></H5Button>
          <H5Button class="hr-action focus-action" :disabled="feelingLoading" @click="runFocus">{{ focusActions[data.focus.action] }} ›</H5Button>
        </section>

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
      </HerlogSheet>
      <RecordCalendar :today="today" :selected="selected" :data="selectedData" :prediction="prediction"
        :loading="calendarLoading" :error="calendarError"
        @open="openCalendar" @close="selected = null" @retry="retryCalendar" @details="go" />

      <WeightForm :visible="weightVisible" @close="weightVisible = false" @saved="saved" />
      <PeriodForm :visible="periodVisible" :day="today" :open-period="openPeriod" selectable-day @close="periodVisible = false" @saved="saved">
        <template #extra-action="{ day, disabled }">
          <H5Button class="ghost" :disabled="disabled || feelingLoading || !day || day > today" @click="openFeeling(day)">记感受</H5Button>
        </template>
      </PeriodForm>
      <FeelingForm :visible="feelingVisible" :day="feelingDay" :existing="existingFeeling" @close="feelingVisible = false" @saved="saved" />
      <TabBar v-show="!keyboardOpen" current="/pages/home/index" />
    </div>
  </view>
</template>

<script setup lang="ts">
import { computed, nextTick, ref, watch } from 'vue'
import { onHide, onShow } from '@dcloudio/uni-app'
import H5Button from '../../components/H5Button'
import HerlogSheet from '../../components/HerlogSheet.vue'
import HerlogIcon from '../../components/HerlogIcon.vue'
import TabBar from '../../components/TabBar.vue'
import WeightForm from '../../components/WeightForm.vue'
import PeriodForm from '../../components/PeriodForm.vue'
import FeelingForm from '../../components/FeelingForm.vue'
import RecordCalendar from './RecordCalendar.vue'
import AssistantChat from './AssistantChat.vue'
import SkinCapture from '../skin/SkinCapture.vue'
import { TIME_ZONE, todayString } from '../../shared/dates'
import { assistantStarters, homeShortcuts as shortcuts, suggestedQuestions } from '../../shared/home'
import type { HomeShortcut } from '../../shared/home'
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
const recordsVisible = ref(false)
const keyboardOpen = ref(false)
const pageVisible = ref(false)
const weightVisible = ref(false)
const periodVisible = ref(false)
const captureVisible = ref(false)
const feelingVisible = ref(false)
const feelingLoading = ref(false)
const feelingDay = ref(today.value)
const existingFeeling = ref<FeelingItem | null>(null)
const assistant = ref<{ suspend(): void } | null>(null)
const assistantKey = ref(0)
let overviewSequence = 0
let calendarSequence = 0
let formSequence = 0
let settingsSequence = 0
let captureScroll = 0
let captureFocus: HTMLElement | null = null

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
const recordQuestions = computed(() => suggestedQuestions(data.value?.active_mode === 'trying_to_conceive'
  ? 'follicular' : data.value?.cycle_context.phase ?? 'unknown', !!data.value?.week.has_weight, !!data.value?.week.has_skin))
const starters = computed(() => assistantStarters(data.value?.active_mode === 'trying_to_conceive'
  ? 'unknown' : data.value?.cycle_context.phase ?? 'unknown', !!data.value?.week.has_weight, !!data.value?.week.has_skin))
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
  recordsVisible.value = false
  const previous = calendarMonth.value
  selected.value = day
  if (calendarMonth.value !== previous && calendarMonth.value !== currentMonth.value) void loadMonth(day.slice(0, 7))
}

function retryCalendar() {
  if (!calendarMonth.value || calendarMonth.value === currentMonth.value) void refresh()
  else void loadMonth(calendarMonth.value)
}

function go(page: Tab) {
  recordsVisible.value = false
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
  recordsVisible.value = false
  const action = data.value?.focus.action
  if (action === 'record_feeling') void openFeeling(today.value)
  else if (action === 'record_period') periodVisible.value = true
  else if (action === 'open_period') go('period')
  else openCalendar(today.value)
}

function runShortcut(kind: HomeShortcut) {
  recordsVisible.value = false
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
  focusClosed.value = summaryOpen.value = recordsVisible.value = keyboardOpen.value = false
  weightVisible.value = periodVisible.value = feelingVisible.value = captureVisible.value = false
  loading.value = otherLoading.value = feelingLoading.value = false
  loadError.value = otherError.value = ''
  preferences.value = { ...recordingDefaults }
}

watch(() => [auth.token, auth.privateCacheRevision], reset, { flush: 'sync' })
onHide(() => {
  pageVisible.value = keyboardOpen.value = recordsVisible.value = false
  assistant.value?.suspend()
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
  pageVisible.value = true
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
.home-page:not(.home-capture) { padding:0; }
.summary-header { display:flex; align-items:center; justify-content:space-between; gap:8px; margin-bottom:8px; }
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
.checkin-items { display:grid; width:100%; grid-template-columns:repeat(2,minmax(0,1fr)); gap:6px; margin-bottom:10px; }
.checkin-items button { gap:5px; font-size:13px; }
.checkin-items span { color:var(--hr-ink-2); }
.summary { padding:5px 14px; }
.summary-toggle { display:flex; align-items:center; justify-content:space-between; text-align:left; width:100%; gap:6px; min-height:48px; padding:3px 0; border:0; background:transparent; color:var(--hr-ink); font-size:13px; }
.summary-toggle small { display:block; color:var(--hr-ink-2); font-size:12px; }
.summary-toggle > span:last-child { color:var(--hr-rose-deep); }
.summary-detail { border-top:1px solid var(--hr-line); display:grid; justify-items:start; }
.summary-detail .hr-action { padding-inline:0; font-size:13px; }
.error-row { display:flex; align-items:center; justify-content:space-between; gap:8px; font-size:13px; color:var(--hr-danger); padding-block:3px; }
</style>
