<template>
  <view class="hr-page hr-tab-page cycle-page">
    <HerlogHeading title="经期" description="按自己的节奏来。">
      <template #actions>
        <H5Button class="hr-action mode-entry" @click="modeSheetVisible = true">
          {{ isFertility ? '模式 · 备孕' : '周期模式' }}
        </H5Button>
        <H5Button class="hr-action" @click="selectDate(today)">回到今天</H5Button>
      </template>
    </HerlogHeading>

    <view v-if="!cyclePreference.preference && !cyclePreference.unavailable" class="card muted" role="status">正在读取周期模式…</view>
    <FertilityJournal v-else-if="isFertility && pageVisible" :selected="selected" :today="today"
      :overview="overview" :overview-error="overviewError" :selected-feeling="selectedFeeling"
      :feelings-loading="feelingsLoading" :feeling-error="feelingError" :period-action="periodAction"
      :trying-started-on="cyclePreference.preference?.trying_started_on ?? null"
      @select="selectDate" @record-period="openPeriodForm(selectedPeriod)" @record-feeling="feelingFormVisible = true"
      @retry-overview="loadOverview" @retry-feelings="loadFeelings" />
    <template v-else-if="!isFertility">
    <section class="cycle-panel" aria-labelledby="cycle-status">
      <view class="cycle-panel-content" aria-live="polite">
        <text class="panel-label">{{ heroLabel }}</text>
        <h2 id="cycle-status">{{ heroTitle }}</h2>
        <view v-if="heroNote" class="panel-note" :role="overviewError ? 'alert' : undefined">{{ heroNote }}</view>
        <view v-if="phaseLabel" class="panel-note">{{ phaseLabel }}</view>
      </view>
      <view class="panel-icon"><HerlogIcon name="period" /></view>
      <view class="panel-actions">
        <H5Button v-if="overview" class="primary" @click="recordToday">{{ todayAction }}</H5Button>
        <H5Button v-if="canAddReminder"
          class="ghost" @click="reminderVisible = true">添加日历提醒</H5Button>
        <H5Button v-if="overviewError" class="ghost" @click="loadOverview">重新加载</H5Button>
      </view>
    </section>

    <CycleCalendar :month="month" :selected="selected" :today="today" :predicted-day="predictedDay"
      :periods="items" :marked-days="markedDays" :mark-label="filter ? filter.label : '有感受'" @select="selectDate">
      <H5Button v-if="filter" class="hr-action" @click="filter = null">清除筛选</H5Button>
    </CycleCalendar>

    <section ref="dayCard" class="card day-card" aria-labelledby="day-title">
      <view class="section-head">
        <h2 id="day-title" class="hr-section-title">{{ formatDayLabel(selected) }}</h2>
        <text v-if="selected === today" class="today-tag">今天</text>
      </view>
      <view v-if="selected > today" class="muted">
        {{ selected === predictedDay ? '这是预计开始日。实际日期可能不同，请在当天或之后补记。' : '这一天还没到，可以回到今天继续记录。' }}
      </view>
      <template v-else>
        <view v-if="selectedPeriod" class="day-record">
          <view class="record-copy">
            <text class="record-label">实际经期 · 第 {{ diffDays(selected, selectedPeriod.start_day) + 1 }} 天</text>
            <text class="muted">{{ periodRange(selectedPeriod) }}</text>
          </view>
          <H5Button class="hr-action" @click="removePeriod(selectedPeriod)">删除经期</H5Button>
        </view>
        <view v-else-if="openPeriod" class="muted">
          {{ formatDayLabel(openPeriod.start_day) }} 开始的经期还没有结束日期。
        </view>
        <view v-if="feelingError" class="retry-row" role="alert">
          <span class="muted">这月的感受暂时读不到。</span>
          <H5Button class="hr-action" @click="loadFeelings">重试</H5Button>
        </view>
        <view v-else-if="feelingsLoading" class="muted" role="status">正在读取感受…</view>
        <view v-else-if="selectedFeeling" class="day-record">
          <view class="record-copy">
            <text class="record-label">当天感受</text>
            <view v-if="feelingTags.length" class="day-tags">
              <span v-for="tag in feelingTags" :key="tag">{{ tag }}</span>
            </view>
            <text v-if="selectedFeeling.note" class="diary-note">{{ selectedFeeling.note }}</text>
          </view>
          <H5Button class="hr-action" @click="removeFeeling(selected)">删除感受</H5Button>
        </view>
        <view v-else-if="overview && !selectedPeriod && !openPeriod" class="muted">这一天还没有记录。</view>
        <view class="day-actions">
          <H5Button class="primary" :disabled="!overview" @click="openPeriodForm(selectedPeriod)">
            {{ periodAction }}
          </H5Button>
          <H5Button class="ghost" :disabled="!overview || feelingsLoading || feelingError"
            @click="feelingFormVisible = true">{{ selectedFeeling ? '编辑感受' : '记录感受' }}</H5Button>
        </view>
      </template>
    </section>

    <section class="card diary-card" aria-labelledby="diary-title">
      <view class="section-head">
        <h2 id="diary-title" class="hr-section-title">本月感受小结</h2>
        <text v-if="!feelingsLoading && !feelingError && diary.days" class="today-tag">已记 {{ diary.days }} 天</text>
      </view>
      <view v-if="feelingsLoading" class="muted">正在整理本月记录…</view>
      <view v-else-if="feelingError" class="muted">重试加载感受后可查看小结。</view>
      <view v-else-if="!diary.days" class="muted">这月还没有感受记录。经量、心情或一句备注都可以单独记。</view>
      <template v-else>
        <view v-if="diary.moods.length || diary.symptoms.length" class="muted diary-hint">按记录天数汇总，点标签可在月历上回看。</view>
        <view v-else class="muted">点月历上的圆点可查看当天感受。</view>
        <view v-for="group in diaryGroups" :key="group.kind" class="diary-group">
          <h3>{{ group.title }}</h3>
          <view class="diary-filters" role="group" :aria-label="group.title">
            <H5Button v-for="item in group.items" :key="item.label" class="diary-filter"
              :aria-pressed="filter?.kind === group.kind && filter.label === item.label"
              @click="toggleFilter({ kind: group.kind, label: item.label })">
              {{ item.label }} <span>{{ item.days }} 天</span>
            </H5Button>
          </view>
        </view>
        <view v-if="filter" class="matched-dates">
          <text class="muted">{{ filter.label }} · 记录日期</text>
          <view class="diary-filters">
            <H5Button v-for="entry in matchedFeelings" :key="entry.day" class="diary-filter"
              :aria-pressed="selected === entry.day" @click="showDay(entry.day)">
              {{ formatDayLabel(entry.day) }}
            </H5Button>
          </view>
        </view>
      </template>
    </section>

    <section class="card history-card" aria-labelledby="cycle-history">
      <view class="section-head">
        <h2 id="cycle-history" class="hr-section-title">周期回顾</h2>
        <text v-if="items.length" class="muted">{{ items.length }} 次记录</text>
      </view>
      <view v-if="overviewLoading && !overview" class="muted">正在读取经期记录…</view>
      <view v-else-if="overviewError && !overview" class="muted">重试加载后可查看历史。</view>
      <view v-else-if="!items.length" class="muted">保存第一段经期后，就能在这里回看。</view>
      <template v-else>
        <view v-if="cycleStats.interval || cycleStats.duration" class="cycle-stats">
          <view v-if="cycleStats.interval">
            <text class="muted">开始日间隔</text>
            <text class="stats-value">{{ formatRange(cycleStats.interval) }} <small>天</small></text>
            <text class="stats-caption">最近 {{ cycleStats.interval.count }} 个间隔</text>
          </view>
          <view v-if="cycleStats.duration">
            <text class="muted">经期持续</text>
            <text class="stats-value">{{ formatRange(cycleStats.duration) }} <small>天</small></text>
            <text class="stats-caption">最近 {{ cycleStats.duration.count }} 段完整记录</text>
          </view>
        </view>
        <view v-for="item in visibleHistory" :key="item.id" class="history-row">
          <H5Button class="history-date" :aria-label="'查看 ' + item.start_day + ' 的记录'" @click="showDay(item.start_day)">
            <span>{{ periodRange(item) }}</span>
            <span class="muted">
              {{ item.duration_days === null ? '未记录结束' : '持续 ' + item.duration_days + ' 天' }}
              <template v-if="item.cycle_days !== null"> · 距上次开始 {{ item.cycle_days }} 天</template>
            </span>
          </H5Button>
          <H5Button class="hr-action" :aria-label="'更正 ' + item.start_day + ' 开始的经期'"
            @click="editFromHistory(item)">更正</H5Button>
        </view>
        <H5Button v-if="items.length > 4" class="hr-action" :aria-expanded="allHistory"
          @click="allHistory = !allHistory">{{ allHistory ? '收起较早记录' : '查看全部记录' }}</H5Button>
      </template>
    </section>
    </template>

    <PeriodForm :visible="periodFormVisible" :day="selected" :editing="periodEditing"
      :open-period="openPeriod ? { id: openPeriod.id, startDay: openPeriod.start_day } : null"
      @close="periodFormVisible = false" @saved="onPeriodSaved" />
    <FeelingForm :visible="feelingFormVisible" :day="selected" :existing="selectedFeeling"
      @close="feelingFormVisible = false" @saved="onFeelingSaved" />
    <CycleReminder v-if="reminderVisible && predictedDay" :expected-start="predictedDay"
      @close="reminderVisible = false" />
    <CycleModeSheet v-if="modeSheetVisible" @close="modeSheetVisible = false" @changed="modeSheetVisible = false" />
    <TabBar current="/pages/period/index" />
  </view>
</template>

<script setup lang="ts">
import { computed, nextTick, ref, watch } from 'vue'
import { onHide, onShow } from '@dcloudio/uni-app'
import H5Button from '../../components/H5Button'
import HerlogHeading from '../../components/HerlogHeading.vue'
import HerlogIcon from '../../components/HerlogIcon.vue'
import TabBar from '../../components/TabBar.vue'
import PeriodForm from '../../components/PeriodForm.vue'
import FeelingForm from '../../components/FeelingForm.vue'
import CycleReminder from './CycleReminder.vue'
import CycleCalendar from './CycleCalendar.vue'
import CycleModeSheet from './CycleModeSheet.vue'
import FertilityJournal from './FertilityJournal.vue'
import {
  daysInMonth, diffDays, formatDayLabel, startOfMonth, todayString
} from '../../shared/dates'
import {
  matchesFeeling, openPeriodOnDay, periodOnDay, recentCycleStats, reminderDay, summarizeDiary
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
const reminderVisible = ref(false)
const periodEditing = ref<PeriodItem | null>(null)
const allHistory = ref(false)
const filter = ref<FeelingFilter | null>(null)
const dayCard = ref<HTMLElement | null>(null)
let overviewRequest = 0
let feelingRequest = 0
let epoch = currentEpoch()

const items = computed(() => overview.value?.items ?? [])
const predictedDay = computed(() =>
  overview.value?.prediction.status === 'upcoming' ? overview.value.prediction.expected_start : null
)
const canAddReminder = computed(() => predictedDay.value && reminderDay(predictedDay.value, 0, new Date().toISOString()))
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
const diary = computed(() => summarizeDiary(feelings.value))
const diaryGroups = computed(() => [
  { kind: 'mood' as const, title: '心情', items: diary.value.moods },
  { kind: 'symptom' as const, title: '身体感受', items: diary.value.symptoms }
].filter(group => group.items.length))
const cycleStats = computed(() => recentCycleStats(items.value))
const visibleHistory = computed(() => allHistory.value ? items.value : items.value.slice(0, 4))
const feelingTags = computed(() => {
  const entry = selectedFeeling.value
  if (!entry) return []
  return [entry.flow && '经量 ' + entry.flow, entry.mood, ...entry.symptoms, entry.impact]
    .filter((tag): tag is string => Boolean(tag))
})

const heroLabel = computed(() => actualToday.value || openToday.value ? '当前记录'
  : predictedDay.value ? '下次开始 · 预计' : '周期状态')
const heroTitle = computed(() => {
  if (!overview.value) return overviewError.value ? '暂时读不到周期记录' : '正在读取周期记录…'
  if (actualToday.value) return '经期第 ' + (diffDays(today.value, actualToday.value.start_day) + 1) + ' 天'
  if (openToday.value) return '待补记结束'
  if (predictedDay.value) return formatDayLabel(predictedDay.value)
  if (overview.value.prediction.status === 'overdue') return '已过预计开始日'
  const latest = items.value.find(item => item.start_day <= today.value)
  return latest ? formatDayLabel(latest.start_day) + ' 开始' : '从一次记录开始'
})
const heroNote = computed(() => {
  const prediction = overview.value?.prediction
  if (!prediction) return overviewError.value ? '请检查网络并重试。' : ''
  if (predictedDay.value) {
    const date = actualToday.value || openToday.value ? '预计下次 ' + formatDayLabel(predictedDay.value) + '。' : ''
    return date + '根据近 ' + prediction.cycle_count + ' 个周期估算，仅供记录参考，不用于避孕。'
  }
  if (openToday.value) return formatDayLabel(openToday.value.start_day) + ' 已记开始。确定最后一天后可补记。'
  if (!items.value.length) return '记下实际开始日期，之后可以补记最后一天。'
  return prediction.message + '。'
})
const todayAction = computed(() =>
  actualToday.value?.end_day ? '更正今日经期' : openToday.value ? '补记经期结束' : '记经期'
)

function formatRange(range: { min: number; max: number }): string {
  return range.min === range.max ? String(range.min) : range.min + '–' + range.max
}

function periodRange(item: PeriodItem): string {
  const start = formatDayLabel(item.start_day)
  if (!item.end_day || item.end_day === item.start_day) return item.start_day.slice(0, 4) + ' 年 ' + start
  const endYear = item.end_day.slice(0, 4) === item.start_day.slice(0, 4) ? '' : item.end_day.slice(0, 4) + ' 年 '
  return item.start_day.slice(0, 4) + ' 年 ' + start + ' – ' + endYear + formatDayLabel(item.end_day)
}

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

async function showDay(day: string) {
  selectDate(day)
  await nextTick()
  dayCard.value?.scrollIntoView({ block: 'start' })
}

function recordToday() {
  selectDate(today.value)
  openPeriodForm(actualToday.value?.end_day ? actualToday.value : null)
}

function openPeriodForm(editing: PeriodItem | null) {
  periodEditing.value = editing
  periodFormVisible.value = true
}

function editFromHistory(item: PeriodItem) {
  selectDate(item.start_day)
  openPeriodForm(item)
}

function toggleFilter(next: FeelingFilter) {
  const active = filter.value
  filter.value = active?.kind === next.kind && active.label === next.label ? null : next
  if (filter.value && matchedFeelings.value.length) selected.value = matchedFeelings.value[0].day
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
  allHistory.value = false
  delete lastSelected.period
  delete lastSelected.trying_to_conceive
  modeSheetVisible.value = false
  periodFormVisible.value = false
  feelingFormVisible.value = false
  reminderVisible.value = false
  periodEditing.value = null
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
onShow(() => {
  pageVisible.value = true
  const now = todayString()
  if (today.value !== now) {
    const wasToday = selected.value === today.value
    today.value = now
    if (wasToday) setSelection(now)
  }
  if (epoch !== currentEpoch()) resetAccount()
  if (!auth.isLoggedIn) {
    uni.reLaunch({ url: '/pages/login/index' })
    return
  }
  void cyclePreference.load()
  void loadOverview()
  void loadFeelings()
})
onHide(() => {
  pageVisible.value = false
  modeSheetVisible.value = false
})

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
.cycle-panel {
  display: grid; grid-template-columns: minmax(0, 1fr) auto; gap: 14px 8px;
  padding: 18px 16px 15px; margin-bottom: 14px; color: var(--hr-rose-deep);
  background: radial-gradient(ellipse at 100% 0%, var(--hr-peach) 0%, transparent 62%), var(--hr-rose-soft);
  border: 1px solid var(--hr-line); border-radius: var(--hr-radius-lg);
}
.cycle-panel h2 { margin: 4px 0 5px; font: 680 clamp(25px, 7vw, 34px)/1.2 var(--hr-serif); }
.panel-label { font-size: 13px; font-weight: 650; }
.panel-note { max-width: 35em; color: var(--hr-ink-2); font-size: 13px; line-height: 1.55; }
.panel-icon {
  display: grid; place-items: center; width: 46px; height: 46px; color: var(--hr-rose-deep);
  border: 1px solid var(--hr-line); border-radius: 50%; background: var(--hr-surface);
}
.panel-icon svg { width: 24px; height: 24px; }
.panel-actions, .day-actions {
  display: grid; grid-template-columns: repeat(auto-fit, minmax(min(100%, 132px), 1fr)); gap: 8px;
}
.panel-actions { grid-column: 1 / -1; }
.panel-actions:empty { display: none; }
.section-head, .retry-row { display: flex; justify-content: space-between; align-items: center; gap: 8px; }
.section-head { margin-bottom: 9px; }
.section-head h2 { margin: 0; }
.muted, .stats-caption { color: var(--hr-ink-2); font-size: 13px; line-height: 1.5; }
.today-tag { padding: 3px 8px; border-radius: 99px; background: var(--hr-rose-soft); color: var(--hr-rose-deep); font-size: 12px; }
.day-record, .history-row {
  display: flex; justify-content: space-between; align-items: flex-start; gap: 6px;
  padding: 7px 0; border-top: 1px solid var(--hr-line); font-size: 14px;
}
.record-copy, .history-date { display: grid; gap: 5px; min-width: 0; padding: 6px 0; }
.record-label { font-weight: 650; }
.day-record .hr-action, .history-row .hr-action { flex-shrink: 0; padding-inline: 4px; }
.day-actions { margin-top: 12px; }
.day-tags, .diary-filters { display: flex; flex-wrap: wrap; gap: 6px; }
.day-tags span {
  background: var(--hr-paper-deep); border-radius: 999px; padding: 3px 8px;
  color: var(--hr-ink-2); font-size: 12px;
}
.diary-note { color: var(--hr-ink); white-space: pre-wrap; overflow-wrap: anywhere; }
.diary-group, .matched-dates { margin-top: 12px; }
.diary-group h3 { font: 650 13px var(--hr-font); margin: 0 0 5px; }
.diary-filter {
  display: inline-flex; gap: 5px; align-items: center; min-height: 44px; padding: 6px 10px;
  background: var(--hr-paper); color: var(--hr-ink); border: 1px solid var(--hr-line-strong);
  border-radius: 999px; font-size: 13px;
}
.diary-filter span { color: var(--hr-ink-2); font-size: 12px; }
.diary-filter[aria-pressed='true'] { color: var(--hr-rose-deep); border-color: var(--hr-rose); background: var(--hr-rose-soft); }
.matched-dates .diary-filters { margin-top: 4px; }
.cycle-stats {
  display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 8px;
  padding: 10px 12px; margin-bottom: 8px; border-radius: 12px; background: var(--hr-paper-deep);
}
.cycle-stats > * { display: grid; gap: 2px; }
.stats-value { font: 680 22px/1.15 var(--hr-serif); color: var(--hr-rose-deep); }
.stats-value small { font: 13px var(--hr-font); }
.stats-caption { font-size: 12px; }
.history-date {
  justify-items: start; min-height: 44px; text-align: left; border: 0;
  border-radius: 8px; background: transparent; color: var(--hr-ink); font-size: 14px;
}
.diary-filter:active, .history-date:active { filter: brightness(.95); }
</style>
