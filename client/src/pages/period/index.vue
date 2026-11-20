<template>
  <view class="hr-page hr-tab-page cycle-page">
    <HerlogHeading title="经期">
      <template #actions>
        <H5Button class="hr-action mode-entry" @click="modeSheetVisible = true">
          {{ isFertility ? '模式 · 备孕' : '周期模式' }}
        </H5Button>
        <H5Button class="hr-action" @click="goToday">回到今天</H5Button>
      </template>
    </HerlogHeading>

    <view v-if="!cyclePreference.preference && !cyclePreference.unavailable" class="card muted" role="status">正在读取周期模式…</view>
    <FertilityJournal v-else-if="isFertility && pageVisible" :selected="selected" :today="today"
      :overview="overview" :predicted-day="predictedDay" :predicted-end="predictedEnd" :selected-feeling="selectedFeeling"
      :feelings-loading="feelingsLoading" :feeling-error="feelingError" :period-action="periodAction"
      :trying-started-on="cyclePreference.preference?.trying_started_on ?? null"
      @select="selectDate" @pick-month="monthPickerVisible = true"
      @record-period="openPeriodForm(selectedPeriod)" @record-feeling="openFeeling()"
      @retry-feelings="loadFeelings">
      <template #prediction>
        <PeriodPredictionCard v-bind="predictionProps" @show-day="showPredictedDay" @backfill="backfillPeriod"
          @retry="loadOverview" @remind="reminderVisible = true" />
      </template>
    </FertilityJournal>
    <template v-else-if="!isFertility">
    <nav class="cycle-sections" aria-label="经期页面视图">
      <H5Button class="cycle-section" :aria-pressed="section === 'calendar'" @click="section = 'calendar'">
        <HerlogIcon name="period" />月历
      </H5Button>
      <H5Button class="cycle-section" :aria-pressed="section === 'review'" @click="section = 'review'">
        <HerlogIcon name="mobility" />周期回顾
      </H5Button>
    </nav>

    <div v-if="section === 'calendar'">
      <section class="cycle-panel" :class="{ forecast: heroForecast }" aria-labelledby="cycle-status">
        <div class="cycle-panel-content" aria-live="polite">
          <p class="panel-label">{{ heroForecast ? '预计下次经期' : '今天的周期' }}</p>
          <h2 id="cycle-status">{{ heroTitle }}</h2>
          <p v-if="heroNote" class="panel-note" :role="overviewError ? 'alert' : undefined">{{ heroNote }}</p>
          <p v-if="phaseLabel" class="phase-label">{{ phaseLabel }}</p>
        </div>
        <div class="panel-icon" aria-hidden="true"><HerlogIcon name="period" /></div>
        <div class="panel-actions">
          <H5Button v-if="overview && !overviewError" class="primary" @click="recordToday">{{ todayAction }}</H5Button>
          <H5Button v-if="overview && !overviewError" class="ghost" :disabled="preparingFeeling" @click="recordTodayFeeling">
            {{ preparingFeeling ? '正在读取…' : '记今日感受' }}
          </H5Button>
          <H5Button v-if="overviewError" class="ghost" @click="loadOverview">重新加载</H5Button>
        </div>
      </section>

      <CycleCalendar :month="month" :selected="selected" :today="today" :predicted-day="predictedDay"
        :predicted-end="predictedEnd" :ovulatory-window="ovulatoryWindow"
        :periods="items" :marked-days="markedDays" :mark-label="filter ? filter.label : '有感受'"
        @select="selectDate" @pick-month="monthPickerVisible = true">
        <H5Button v-if="filter" class="hr-action" @click="filter = null">清除筛选</H5Button>
      </CycleCalendar>

      <CycleInsightCard v-if="overview && pageVisible" :key="auth.member?.customer_id" :signature="insightSignature" />

      <section ref="dayCard" class="card day-card" aria-labelledby="day-title" tabindex="-1">
        <div class="section-head">
          <h2 id="day-title" class="hr-section-title">{{ formatDayLabel(selected) }}</h2>
          <span v-if="selected === today" class="today-tag">今天</span>
        </div>
        <p v-if="selectedInPrediction" class="day-context estimate">
          {{ selected === predictedDay ? '预计经期开始 · 根据近期记录推算，实际日期可能不同。' : '预计经期 · 根据以往经期时长估算。' }}
        </p>
        <p v-else-if="selectedInOvulatoryWindow" class="day-context estimate">
          {{ selected === ovulatoryWindow?.estimated_day ? '排卵估算日 · 阶段区间的中心日期。' : '排卵阶段估算 · 根据经期日期推算。' }}
          仅供记录参考。
        </p>
        <p v-else-if="selected > today" class="muted">可以在当天或之后补记。</p>
        <template v-if="selected <= today">
          <div v-if="selectedPeriod" class="day-context actual">
            <strong>实际经期 · 第 {{ diffDays(selected, selectedPeriod.start_day) + 1 }} 天</strong>
            <span>{{ periodRange(selectedPeriod) }}</span>
          </div>
          <p v-else-if="openPeriod" class="day-context actual">{{ formatDayLabel(openPeriod.start_day) }} 开始的经期尚未填写结束日。</p>
          <div v-if="feelingError" class="retry-row" role="alert">
            <span class="muted">暂时无法读取当天感受。</span>
            <H5Button class="hr-action" @click="loadFeelings">重试</H5Button>
          </div>
          <p v-else-if="feelingsLoading" class="muted" role="status">正在读取当天感受…</p>
          <div v-else class="journal-grid" role="group" aria-label="当天感受">
            <H5Button v-for="entry in journalFields" :key="entry.key" class="journal-field"
              :aria-label="entry.label + '，' + entry.value + '，点按记录'" @click="openFeeling(entry.key)">
              <span class="journal-label">{{ entry.label }}</span>
              <strong :class="{ 'journal-empty': !entry.recorded }">{{ entry.value }}</strong>
            </H5Button>
          </div>
          <p v-if="selectedFeeling?.note && !feelingError && !feelingsLoading" class="diary-note">{{ selectedFeeling.note }}</p>
          <div class="day-actions">
            <H5Button class="ghost" :disabled="!overview || overviewError" @click="openPeriodForm(selectedPeriod)">
              {{ periodAction }}
            </H5Button>
            <H5Button class="ghost" :disabled="feelingsLoading || feelingError"
              @click="openFeeling()">{{ selectedFeeling ? '编辑感受' : '记录感受' }}</H5Button>
          </div>
          <div v-if="selectedPeriod || selectedFeeling" class="delete-actions">
            <H5Button v-if="selectedPeriod" class="hr-action" @click="removePeriod(selectedPeriod)">删除经期</H5Button>
            <H5Button v-if="selectedFeeling" class="hr-action" @click="removeFeeling(selected)">删除感受</H5Button>
          </div>
        </template>
      </section>

      <PeriodPredictionCard v-bind="predictionProps" @show-day="showPredictedDay" @backfill="backfillPeriod"
        @retry="loadOverview" @remind="reminderVisible = true" />
    </div>

    <div v-show="section === 'review'">
      <CycleReview :key="auth.member?.customer_id" :items="items" :feelings="feelings"
        :filter="filter" :month="month" :loaded="Boolean(overview) && !overviewError" :pending="overviewLoading"
        :failed="overviewError" :diary-loading="feelingsLoading" :diary-failed="feelingError"
        @backfill="backfillPeriod" @retry="loadOverview" @retry-diary="loadFeelings"
        @pick-month="monthPickerVisible = true" @select="showDay" @edit="editFromHistory" @filter="toggleFilter" />
    </div>
    </template>

    <PeriodForm :visible="periodFormVisible" :day="predictionBackfill ? '' : selected" :editing="periodEditing"
      :selectable-day="predictionBackfill"
      :open-period="!predictionBackfill && openPeriod ? { id: openPeriod.id, startDay: openPeriod.start_day } : null"
      @close="periodFormVisible = false" @saved="onPeriodSaved" />
    <FeelingForm :visible="feelingFormVisible" :day="selected" :existing="selectedFeeling" :initial-section="feelingSection"
      @close="feelingFormVisible = false" @saved="onFeelingSaved" />
    <CycleMonthPicker v-if="monthPickerVisible" :month="month" :today="today" :forecast-end="predictedEnd"
      @close="monthPickerVisible = false" @select="pickMonth" />
    <CycleReminder v-if="reminderVisible && predictedDay" :expected-start="predictedDay"
      @close="reminderVisible = false" />
    <CycleModeSheet v-if="modeSheetVisible" @close="modeSheetVisible = false" @changed="modeSheetVisible = false" />
    <TabBar current="/pages/period/index" />
  </view>
</template>

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, ref, watch } from 'vue'
import { onHide, onShow } from '@dcloudio/uni-app'
import H5Button from '../../components/H5Button'
import HerlogHeading from '../../components/HerlogHeading.vue'
import HerlogIcon from '../../components/HerlogIcon.vue'
import TabBar from '../../components/TabBar.vue'
import PeriodForm from '../../components/PeriodForm.vue'
import FeelingForm from '../../components/FeelingForm.vue'
import CycleReminder from './CycleReminder.vue'
import CycleCalendar from './CycleCalendar.vue'
import CycleInsightCard from './CycleInsightCard.vue'
import CycleMonthPicker from './CycleMonthPicker.vue'
import CycleReview from './CycleReview.vue'
import PeriodPredictionCard from './PeriodPredictionCard.vue'
import CycleModeSheet from './CycleModeSheet.vue'
import FertilityJournal from './FertilityJournal.vue'
import {
  daysInMonth, diffDays, formatDayLabel, startOfMonth, todayString
} from '../../shared/dates'
import {
  matchesFeeling, openPeriodOnDay, periodOnDay, periodRange, reminderDay
} from '../../shared/period'
import type { FeelingFilter } from '../../shared/period'
import { ApiRequestError, currentEpoch, StaleSessionError } from '../../services/httpClient'
import { deleteFeeling, deletePeriod, getOverview, listFeelings } from '../../services/periodService'
import { fetchCycleContext } from '../../services/homeService'
import { phaseNames } from '../../services/wellnessService'
import type { CycleDay } from '../../services/wellnessService'
import type { FeelingItem, PeriodItem, PeriodOverview } from '../../services/types'
import { useAuthStore } from '../../stores/auth'
import { useCyclePreference } from '../../stores/cyclePreference'
import type { CycleMode } from '../../shared/fertility'

const auth = useAuthStore()
const cyclePreference = useCyclePreference()
const today = ref(todayString())
const pageVisible = ref(false)
const modeSheetVisible = ref(false)
const monthPickerVisible = ref(false)
const section = ref<'calendar' | 'review'>('calendar')
const isFertility = computed(() => cyclePreference.mode === 'trying_to_conceive')
const lastSelected: Partial<Record<CycleMode, string>> = {}
const selected = ref(today.value)
const month = ref(startOfMonth(today.value))
const overview = ref<PeriodOverview | null>(null)
const feelings = ref<FeelingItem[]>([])
const overviewLoading = ref(true)
const activePhase = ref<CycleDay | null>(null)
const phaseLabel = computed(() => {
  const phase = activePhase.value
  if (phase?.basis !== 'estimated') return ''
  return '当前阶段估算 · ' + (phase.phase === 'ovulatory' ? '排卵相关阶段' : phaseNames[phase.phase])
})
const feelingsLoading = ref(true)
const overviewError = ref(false)
const feelingError = ref(false)
const periodFormVisible = ref(false)
const feelingFormVisible = ref(false)
const feelingSection = ref<FeelingFilter['kind']>()
const preparingFeeling = ref(false)
const reminderVisible = ref(false)
const periodEditing = ref<PeriodItem | null>(null)
const predictionBackfill = ref(false)
const filter = ref<FeelingFilter | null>(null)
const dayCard = ref<HTMLElement | null>(null)
let overviewRequest = 0
let feelingRequest = 0
let epoch = currentEpoch()
let todayTimer: ReturnType<typeof setInterval> | undefined

const items = computed(() => overview.value?.items ?? [])
const prediction = computed(() => {
  if (overviewError.value || overviewLoading.value) return null
  const data = overview.value?.prediction
  if (data?.status === 'upcoming' && data.expected_start && data.expected_start < today.value) {
    return { ...data, status: 'overdue' as const, expected_start: null, expected_end: null, ovulatory_window: null }
  }
  return data ?? null
})
const predictedDay = computed(() => prediction.value?.status === 'upcoming' ? prediction.value.expected_start : null)
const predictedEnd = computed(() => predictedDay.value ? prediction.value?.expected_end ?? predictedDay.value : null)
const selectedInPrediction = computed(() =>
  !selectedPeriod.value && predictedDay.value && predictedEnd.value &&
  selected.value >= predictedDay.value && selected.value <= predictedEnd.value
)
const ovulatoryWindow = computed(() => predictedDay.value ? prediction.value?.ovulatory_window ?? null : null)
const selectedInOvulatoryWindow = computed(() => {
  const range = ovulatoryWindow.value
  return range && !selectedPeriod.value && selected.value >= range.start_day && selected.value <= range.end_day
})
const predictionProps = computed(() => ({
  prediction: prediction.value,
  day: predictedDay.value,
  end: predictedEnd.value,
  today: today.value,
  loading: overviewLoading.value,
  failed: overviewError.value,
  reminderAvailable: Boolean(predictedDay.value && reminderDay(predictedDay.value, 0, new Date().toISOString()))
}))
const insightSignature = computed(() => JSON.stringify([today.value, items.value.map(({ start_day, end_day }) => [start_day, end_day])]))
const selectedPeriod = computed(() => periodOnDay(items.value, selected.value))
const openPeriod = computed(() => openPeriodOnDay(items.value, selected.value))
const periodAction = computed(() => selectedPeriod.value ? '更正经期' : openPeriod.value ? '补记结束' : '记录经期')
const actualToday = computed(() => periodOnDay(items.value, today.value))
const openToday = computed(() => openPeriodOnDay(items.value, today.value))
const selectedFeeling = computed(() => feelings.value.find(item => item.day === selected.value) ?? null)
const matchedFeelings = computed(() => {
  const active = filter.value
  return active ? feelings.value.filter(item => matchesFeeling(item, active)) : feelings.value
})
const markedDays = computed(() => new Set(matchedFeelings.value.map(item => item.day)))
const journalFields = computed(() => {
  const entry = selectedFeeling.value
  const fields = [
    { key: 'flow', label: '经量', value: entry?.flow },
    { key: 'mood', label: '心情', value: entry?.mood },
    { key: 'symptom', label: '身体感受', value: entry?.symptoms.join('、') },
    { key: 'impact', label: '生活影响', value: entry?.impact }
  ] as const
  return fields.map(field => ({ ...field, recorded: Boolean(field.value), value: field.value || '添加记录' }))
})

const heroForecast = computed(() => Boolean(predictedDay.value && !actualToday.value && !openToday.value))
const heroTitle = computed(() => {
  if (overviewError.value) return '暂时读不到周期记录'
  if (!overview.value) return '正在读取周期记录…'
  if (actualToday.value) return '经期第 ' + (diffDays(today.value, actualToday.value.start_day) + 1) + ' 天'
  if (openToday.value) return '待补记结束'
  if (predictedDay.value) return formatDayLabel(predictedDay.value)
  if (prediction.value?.status === 'overdue') return '已过预计开始日'
  return items.value.length ? '记录这一次周期' : '记下第一次经期'
})
const heroNote = computed(() => {
  if (overviewError.value) return '请检查网络并重试。'
  if (!overview.value) return ''
  if (openToday.value) return formatDayLabel(openToday.value.start_day) + ' 已记开始'
  if (heroForecast.value && predictedDay.value) {
    const days = diffDays(predictedDay.value, today.value)
    return days ? '还有 ' + days + ' 天，实际日期可能不同。' : '预计今天开始，实际日期可能不同。'
  }
  if (prediction.value?.status === 'overdue') return '经期已开始时，可以补记实际日期。'
  const latest = items.value.find(item => item.start_day <= today.value)
  if (latest && !actualToday.value) return '上次开始于 ' + formatDayLabel(latest.start_day)
  if (!items.value.length) return '先记开始日期，结束后可补记。'
  return ''
})
const todayAction = computed(() =>
  actualToday.value?.end_day ? '更正今日经期' : openToday.value ? '补记经期结束' : '记经期'
)

function setSelection(day: string): boolean {
  selected.value = day
  const next = startOfMonth(day)
  if (month.value === next) return false
  month.value = next
  filter.value = null
  feelings.value = []
  return true
}

function selectDate(day: string) {
  if (setSelection(day)) void loadFeelings()
}

function goToday() {
  section.value = 'calendar'
  selectDate(today.value)
}

function pickMonth(day: string) {
  monthPickerVisible.value = false
  selectDate(day)
}

async function showDay(day: string) {
  section.value = 'calendar'
  selectDate(day)
  await nextTick()
  dayCard.value?.scrollIntoView({ block: 'start' })
  dayCard.value?.focus({ preventScroll: true })
}

async function showPredictedDay(day: string) {
  selectDate(day)
  await nextTick()
  const calendar = document.getElementById('cycle-calendar')
  calendar?.scrollIntoView({ block: 'start' })
  calendar?.querySelector<HTMLElement>('button.cell[aria-pressed="true"]')?.focus({ preventScroll: true })
}

function recordToday() {
  selectDate(today.value)
  openPeriodForm(actualToday.value?.end_day ? actualToday.value : null)
}

function openFeeling(initial?: FeelingFilter['kind']) {
  if (feelingsLoading.value || feelingError.value || selected.value > today.value) return
  feelingSection.value = initial
  feelingFormVisible.value = true
}

async function recordTodayFeeling() {
  const session = currentEpoch()
  const day = today.value
  const changedMonth = setSelection(day)
  if (changedMonth || feelingsLoading.value || feelingError.value) {
    preparingFeeling.value = true
    await loadFeelings()
    if (session !== currentEpoch()) return
    preparingFeeling.value = false
  }
  if (!pageVisible.value || isFertility.value || section.value !== 'calendar' || selected.value !== day) return
  if (feelingError.value) await showDay(day)
  else openFeeling()
}

function openPeriodForm(editing: PeriodItem | null, backfill = false) {
  predictionBackfill.value = backfill
  periodEditing.value = editing
  periodFormVisible.value = true
}

function backfillPeriod() {
  openPeriodForm(null, true)
}

function editFromHistory(item: PeriodItem) {
  selectDate(item.start_day)
  openPeriodForm(item)
}

function toggleFilter(next: FeelingFilter | null) {
  const active = filter.value
  filter.value = next && active?.kind === next.kind && active.label === next.label ? null : next
}

async function loadOverview() {
  const request = ++overviewRequest
  const session = currentEpoch()
  overviewLoading.value = true
  overviewError.value = false
  void fetchCycleContext(today.value).then(result => {
    if (request === overviewRequest && session === currentEpoch()) activePhase.value = result
  }).catch(() => {
    if (request === overviewRequest && session === currentEpoch()) activePhase.value = null
  })
  try {
    const result = await getOverview()
    if (request === overviewRequest && session === currentEpoch()) overview.value = result
  } catch (failure) {
    if (request === overviewRequest && session === currentEpoch() && !(failure instanceof StaleSessionError)) {
      overviewError.value = true
    }
  } finally {
    if (request === overviewRequest && session === currentEpoch()) overviewLoading.value = false
  }
}

async function loadFeelings() {
  const request = ++feelingRequest
  const session = currentEpoch()
  const first = month.value
  const last = first.slice(0, 7) + '-' + String(daysInMonth(first)).padStart(2, '0')
  feelingsLoading.value = true
  feelingError.value = false
  try {
    const rows = await listFeelings(first, last)
    if (request !== feelingRequest || session !== currentEpoch()) return
    feelings.value = rows
    if (filter.value && !matchedFeelings.value.length) filter.value = null
  } catch (failure) {
    if (request === feelingRequest && session === currentEpoch() && !(failure instanceof StaleSessionError)) {
      feelingError.value = true
    }
  } finally {
    if (request === feelingRequest && session === currentEpoch()) feelingsLoading.value = false
  }
}

function resetAccount() {
  epoch = currentEpoch()
  overviewRequest += 1
  feelingRequest += 1
  overview.value = null
  activePhase.value = null
  feelings.value = []
  filter.value = null
  section.value = 'calendar'
  delete lastSelected.period
  delete lastSelected.trying_to_conceive
  modeSheetVisible.value = false
  monthPickerVisible.value = false
  periodFormVisible.value = false
  feelingFormVisible.value = false
  feelingSection.value = undefined
  preparingFeeling.value = false
  reminderVisible.value = false
  periodEditing.value = null
  predictionBackfill.value = false
  overviewLoading.value = feelingsLoading.value = true
  overviewError.value = feelingError.value = false
  setSelection(today.value)
}

watch(() => auth.member?.customer_id, resetAccount, { flush: 'sync' })
watch(() => cyclePreference.mode, (next, previous) => {
  lastSelected[previous] = selected.value
  const day = lastSelected[next] ?? today.value
  if (pageVisible.value && auth.isLoggedIn) selectDate(day)
  else setSelection(day)
})
function refreshToday() {
  const now = todayString()
  if (today.value === now) return false
  const wasToday = selected.value === today.value
  today.value = now
  if (wasToday) setSelection(now)
  return true
}
onShow(() => {
  pageVisible.value = true
  refreshToday()
  if (epoch !== currentEpoch()) resetAccount()
  if (!auth.isLoggedIn) {
    uni.reLaunch({ url: '/pages/login/index' })
    return
  }
  void cyclePreference.load()
  void loadOverview()
  void loadFeelings()
  clearInterval(todayTimer)
  todayTimer = setInterval(() => {
    if (!pageVisible.value || !auth.isLoggedIn || !refreshToday()) return
    void loadOverview()
    void loadFeelings()
  }, 15_000)
})
onHide(() => {
  clearInterval(todayTimer)
  pageVisible.value = false
  modeSheetVisible.value = false
  monthPickerVisible.value = false
})
onBeforeUnmount(() => clearInterval(todayTimer))

function onPeriodSaved(day: string) {
  periodFormVisible.value = false
  selectDate(day)
  void loadOverview()
  uni.showToast({ title: '已保存', icon: 'none' })
}

function onFeelingSaved() {
  feelingFormVisible.value = false
  void loadFeelings()
  uni.showToast({ title: '已保存', icon: 'none' })
}

function confirmDelete(title: string, content: string, remove: () => Promise<unknown>, refresh: () => Promise<void>) {
  const session = currentEpoch()
  uni.showModal({
    title, content, confirmText: '删除',
    success: async result => {
      if (!result.confirm || session !== currentEpoch()) return
      try {
        await remove()
        if (session === currentEpoch()) await refresh()
      } catch (failure) {
        if (session === currentEpoch() && !(failure instanceof StaleSessionError)) {
          uni.showToast({ title: failure instanceof ApiRequestError ? failure.message : '删除失败', icon: 'none' })
        }
      }
    }
  })
}

function removePeriod(item: PeriodItem) {
  confirmDelete('删除经期记录', '将删除这段经期，已保存的感受会保留。', () => deletePeriod(item.id), loadOverview)
}

function removeFeeling(day: string) {
  confirmDelete('删除感受记录', formatDayLabel(day) + ' 的感受将被删除，经期日期会保留。', () => deleteFeeling(day), loadFeelings)
}
</script>

<style scoped>
.mode-entry { color: var(--hr-rose-deep); background: var(--hr-rose-soft); }
.cycle-sections { display: grid; grid-template-columns: 1fr 1fr; gap: 5px; padding: 4px; margin: 0 0 12px; border: 1px solid var(--hr-line); border-radius: 18px; background: var(--hr-surface); }
.cycle-section { display: flex; align-items: center; justify-content: center; gap: 7px; min-height: 44px; padding: 4px 8px; border: 0; border-radius: 14px; background: transparent; color: var(--hr-ink-2); font: 600 14px var(--hr-font); }
.cycle-section[aria-pressed='true'] { color: var(--hr-rose-deep); background: var(--hr-rose-soft); }
.cycle-section svg { width: 18px; height: 18px; }
.cycle-panel {
  position: relative; isolation: isolate; overflow: hidden; display: grid; grid-template-columns: minmax(0, 1fr) auto;
  align-items: center; gap: 10px 8px; padding: 14px 14px 12px; margin-bottom: 12px;
  color: var(--hr-rose-deep); background: linear-gradient(115deg, var(--hr-rose-soft), var(--hr-peach));
  border: 1px solid var(--hr-line); border-radius: var(--hr-radius-lg);
}
.cycle-panel.forecast { color: var(--hr-plum); background: linear-gradient(115deg, var(--hr-plum-soft), var(--hr-peach)); }
.cycle-panel h2 { margin: 2px 0 0; font: 680 clamp(23px, 7vw, 32px)/1.2 var(--hr-serif, Georgia, "Songti SC", serif); }
.panel-label { margin: 0; color: var(--hr-ink-2); font-size: 13px; font-weight: 650; }
.panel-note { margin: 4px 0 0; color: var(--hr-ink-2); font-size: 13px; line-height: 1.5; }
.phase-label { display: inline-block; margin: 5px 0 0; color: var(--hr-ink-2); font-size: 12px; line-height: 1.45; }
.panel-icon {
  display: grid; place-items: center; width: 50px; height: 50px; margin-inline: 8px 4px;
  border: 1px solid var(--hr-line); border-radius: 50%; background: var(--hr-surface);
  box-shadow: 0 0 0 5px var(--hr-rose-soft), 0 0 0 6px var(--hr-line);
}
.forecast .panel-icon { box-shadow: 0 0 0 5px var(--hr-plum-soft), 0 0 0 6px var(--hr-line); }
.panel-icon svg { width: 24px; height: 24px; }
.panel-actions, .day-actions { display: grid; grid-template-columns: repeat(auto-fit, minmax(min(100%, 124px), 1fr)); gap: 8px; }
.panel-actions { grid-column: 1 / -1; }
.panel-actions:empty { display: none; }
.panel-actions .primary, .panel-actions .ghost, .day-actions .ghost { min-height: 44px; padding-inline: 8px; font-size: 14px; }
.section-head, .retry-row { display: flex; justify-content: space-between; align-items: center; gap: 8px; }
.section-head { margin-bottom: 8px; }
.section-head h2 { margin: 0; font: 700 21px/1.25 var(--hr-serif, Georgia, "Songti SC", serif); }
.day-card { scroll-margin-top: 12px; }
.muted { margin: 5px 0; color: var(--hr-ink-2); font-size: 14px; line-height: 1.5; }
.today-tag { padding: 3px 8px; border-radius: 99px; background: var(--hr-rose-soft); color: var(--hr-rose-deep); font-size: 12px; }
.day-context { display: grid; gap: 2px; margin: 0 0 10px; padding: 8px 10px; border-radius: 11px; font-size: 13px; line-height: 1.5; }
.day-context.estimate { background: var(--hr-plum-soft); color: var(--hr-plum); }
.day-context.actual { background: var(--hr-rose-soft); color: var(--hr-rose-deep); }
.journal-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 8px; }
.journal-field { display: grid; gap: 2px; align-content: center; min-width: 0; min-height: 56px; padding: 8px 9px; text-align: left; border: 1px solid var(--hr-line); border-radius: 11px; color: var(--hr-ink); background: var(--hr-paper); font: 14px/1.45 var(--hr-font); overflow-wrap: anywhere; }
.journal-label { color: var(--hr-ink-2); font-size: 12px; }
.journal-field strong { font-weight: 650; }
.journal-field .journal-empty { color: var(--hr-ink-2); font-weight: 400; }
.diary-note { margin: 9px 0 0; padding: 9px 10px; border-left: 2px solid var(--hr-line-strong); color: var(--hr-ink); font-size: 14px; line-height: 1.55; white-space: pre-wrap; overflow-wrap: anywhere; }
.day-actions { margin-top: 10px; }
.delete-actions { display: flex; justify-content: flex-end; gap: 8px; margin-top: 4px; }
.delete-actions .hr-action { color: var(--hr-ink-2); }
</style>
