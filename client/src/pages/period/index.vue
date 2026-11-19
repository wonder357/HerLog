<template>
  <view class="page">
    <view class="hero">
      <view class="h-title">经期</view>
      <view class="h-status">
        <text class="status-main grad-text">{{ overview?.status.message || '经期记录' }}</text>
        <view v-if="overview?.status.start_day" class="tag outline">
          {{ formatDayLabel(overview.status.start_day) }} 开始
        </view>
      </view>
      <view class="h-sub">
        <text>{{ predictionLine }}</text>
        <text v-if="showHowItWorks" class="link inline" @tap="explainPrediction">怎么算的 ›</text>
      </view>
      <view v-if="overview?.prediction.status === 'overdue'" class="link" @tap="openPeriodForm">
        补记经期开始 ›
      </view>
    </view>

    <view class="main">
      <view class="card">
        <view class="monthbar">
          <view class="month-nav" @tap="shift(-1)">‹</view>
          <view class="month-label">{{ formatMonthLabel(month) }}</view>
          <view class="month-nav" @tap="shift(1)">›</view>
        </view>

        <view class="weekdays">
          <text v-for="name in weekdays" :key="name" class="weekday">{{ name }}</text>
        </view>

        <view class="grid">
          <view v-for="blank in grid.leading" :key="`b-${blank}`" class="cell" />
          <view
            v-for="day in grid.days"
            :key="day"
            class="cell"
            :class="cellClass(day)"
            @tap="selected = day"
          >
            <text class="day-number">{{ Number(day.slice(-2)) }}</text>
            <text v-if="day === today" class="day-sub">今天</text>
            <text v-if="feelingDays.has(day)" class="dot" />
          </view>
        </view>

        <view class="legend">
          <view class="legend-item"><text class="sw sw-period" />实际经期</view>
          <view class="legend-item"><text class="sw sw-expected" />预计开始</view>
          <view class="legend-item"><text class="sw sw-feel" />有感受记录</view>
        </view>
      </view>

      <view class="card">
        <view class="record-head">
          <view>
            <view class="record-date">{{ formatDayLabel(selected) }} · 星期{{ weekdayOf(selected) }}</view>
            <view v-if="selectedSummary" class="record-sub">{{ selectedSummary }}</view>
          </view>
          <view v-if="selectedPeriod || selectedFeeling" class="tag">已记录</view>
        </view>

        <view v-if="selectedPeriod" class="record-row">
          <view class="record-main">
            {{ formatDayLabel(selectedPeriod.start_day) }} 开始
            <text v-if="selectedPeriod.end_day"> · {{ formatDayLabel(selectedPeriod.end_day) }} 结束</text>
            <text v-else> · 未记录结束</text>
          </view>
          <text class="danger-link" @tap="removePeriod(selectedPeriod)">删除这段</text>
        </view>

        <view v-if="selectedFeeling" class="record-row">
          <view class="record-main">
            <view v-if="selectedFeeling.flow" class="record-tags">
              <text class="chip on">经量 {{ selectedFeeling.flow }}</text>
              <text
                v-for="symptom in selectedFeeling.symptoms"
                :key="symptom"
                class="chip on"
              >
                {{ symptom }}
              </text>
              <text v-if="selectedFeeling.impact" class="chip on">{{ selectedFeeling.impact }}</text>
            </view>
            <view v-if="selectedFeeling.note" class="meta">{{ selectedFeeling.note }}</view>
          </view>
          <text class="danger-link" @tap="removeFeeling(selected)">删除感受</text>
        </view>

        <view v-if="!selectedPeriod && !selectedFeeling" class="muted empty-line">
          这一天还没有记录，可以先记经期，或者只记录当时的感受。
        </view>

        <view class="record-actions">
          <view class="btn soft action" @tap="openPeriodForm">记录经期</view>
          <view class="btn ghost action" @tap="openFeelingForm">记录感受</view>
        </view>

        <view class="note record-note">
          感受与经期日期分开保存，单独记录感受不会新建一段经期。
        </view>
      </view>

      <view class="section">
        <view class="section-head">
          <view class="h2">历史回顾</view>
          <view class="link" @tap="selected = items[0]?.start_day || selected">
            共 {{ items.length }} 段 ›
          </view>
        </view>

        <view class="card">
          <view v-if="items.length === 0" class="muted">还没有经期记录。</view>
          <view
            v-for="item in items"
            :key="item.id"
            class="cycle"
            @tap="selected = item.start_day"
          >
            <view class="cycle-date">
              <view class="dd">{{ formatDayLabel(item.start_day) }}</view>
              <view class="dm">{{ item.end_day ? `${formatDayLabel(item.end_day)} 结束` : '未记录结束' }}</view>
            </view>
            <view class="cycle-right">
              <view class="cr-main">
                {{ item.duration_days ? `持续 ${item.duration_days} 天${item.end_day ? '' : '（至今）'}` : '未记录结束' }}
              </view>
              <view class="cr-sub">
                {{ item.cycle_days ? `距上次开始 ${item.cycle_days} 天` : '首次记录' }}
              </view>
            </view>
          </view>
        </view>
        <view class="note footnote">
          预计日期根据历史记录估算，实际日期可能不同，不作为避孕依据。
        </view>
      </view>

      <view v-if="openPeriod" class="hintbox">
        进行中的记录：{{ formatDayLabel(openPeriod.start_day) }} 开始，还没有结束日。选中最后一天后点「记录经期」即可补记。
      </view>
    </view>

    <PeriodForm
      :visible="periodFormVisible"
      :day="selected"
      :open-period="openPeriod ? { id: openPeriod.id, startDay: openPeriod.start_day } : null"
      @close="periodFormVisible = false"
      @saved="onSaved"
    />
    <FeelingForm
      :visible="feelingFormVisible"
      :day="selected"
      :existing="selectedFeeling"
      @close="feelingFormVisible = false"
      @saved="onSaved"
    />
    <TabBar current="/pages/period/index" />
  </view>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { onShow } from '@dcloudio/uni-app'
import TabBar from '../../components/TabBar.vue'
import PeriodForm from '../../components/PeriodForm.vue'
import FeelingForm from '../../components/FeelingForm.vue'
import {
  daysInMonth,
  formatDayLabel,
  formatMonthLabel,
  monthGrid,
  shiftMonth,
  startOfMonth,
  todayString
} from '../../shared/dates'
import { ApiRequestError, StaleSessionError } from '../../services/httpClient'
import {
  deleteFeeling,
  deletePeriod,
  getOverview,
  listFeelings
} from '../../services/periodService'
import type { FeelingItem, PeriodItem, PeriodOverview } from '../../services/types'

const weekdays = ['一', '二', '三', '四', '五', '六', '日']
const WEEKDAYS = ['日', '一', '二', '三', '四', '五', '六']

const today = todayString()
const month = ref(startOfMonth(today))
const selected = ref(today)
const overview = ref<PeriodOverview | null>(null)
const feelings = ref<FeelingItem[]>([])
const periodFormVisible = ref(false)
const feelingFormVisible = ref(false)

const grid = computed(() => monthGrid(month.value))
const items = computed(() => overview.value?.items ?? [])

const actualDays = computed(() => {
  const marks = new Map<string, 'start' | 'end' | 'middle'>()
  for (const item of items.value) {
    const end = item.end_day ?? item.start_day
    const cursor = new Date(`${item.start_day}T00:00:00Z`).getTime()
    const last = new Date(`${end}T00:00:00Z`).getTime()
    for (let time = cursor; time <= last; time += 86400000) {
      const day = new Date(time).toISOString().slice(0, 10)
      marks.set(day, day === item.start_day ? 'start' : day === end ? 'end' : 'middle')
    }
  }
  return marks
})

const feelingDays = computed(() => new Set(feelings.value.map((item) => item.day)))

const predictedDay = computed(() => {
  const prediction = overview.value?.prediction
  if (!prediction || prediction.status !== 'upcoming') {
    return null
  }
  return prediction.expected_start
})

const predictionLine = computed(() => {
  const prediction = overview.value?.prediction
  if (!prediction) {
    return '记下开始和结束，就能估算下次时间。'
  }
  if (prediction.status === 'upcoming' && prediction.expected_start) {
    const sample = prediction.starts_used || prediction.cycle_count
    return `预计下次开始：${formatDayLabel(prediction.expected_start)} · 按近 ${sample} 次记录估算`
  }
  return prediction.message
})

const showHowItWorks = computed(() => overview.value?.prediction.status === 'upcoming')

const selectedPeriod = computed<PeriodItem | null>(() => {
  const day = selected.value
  for (const item of items.value) {
    const end = item.end_day ?? item.start_day
    if (day >= item.start_day && day <= end) {
      return item
    }
  }
  return null
})

const selectedFeeling = computed<FeelingItem | null>(
  () => feelings.value.find((item) => item.day === selected.value) ?? null
)

// 当天的一句话摘要：只写已记录了什么，不做健康判断。
const selectedSummary = computed(() => {
  const parts: string[] = []
  if (selectedPeriod.value) {
    const index = selectedPeriod.value.start_day
    const span = Math.round(
      (new Date(`${selected.value}T00:00:00Z`).getTime() -
        new Date(`${index}T00:00:00Z`).getTime()) /
        86400000
    )
    parts.push(`经期第 ${span + 1} 天`)
  }
  if (selectedFeeling.value) {
    const names: string[] = []
    if (selectedFeeling.value.flow) {
      names.push('经量')
    }
    if (selectedFeeling.value.symptoms.length) {
      names.push(...selectedFeeling.value.symptoms.slice(0, 2))
    }
    parts.push(`已记录${names.join('、')}`)
  }
  return parts.join(' · ')
})

const openPeriod = computed<PeriodItem | null>(() => {
  const candidate = items.value.find((item) => item.end_day === null && item.start_day <= selected.value)
  return candidate ?? null
})

function cellClass(day: string): Record<string, boolean> {
  const mark = actualDays.value.get(day)
  return {
    selected: day === selected.value,
    today: day === today,
    actual: Boolean(mark),
    start: mark === 'start',
    end: mark === 'end',
    predicted: day === predictedDay.value
  }
}

function weekdayOf(day: string): string {
  const [year, monthValue, date] = day.split('-').map(Number)
  return WEEKDAYS[new Date(Date.UTC(year, monthValue - 1, date)).getUTCDay()]
}

function shift(delta: number) {
  month.value = shiftMonth(month.value, delta)
  loadFeelings()
}

function openPeriodForm() {
  periodFormVisible.value = true
}

function openFeelingForm() {
  feelingFormVisible.value = true
}

function explainPrediction() {
  const prediction = overview.value?.prediction
  const sample = prediction?.starts_used || prediction?.cycle_count || 0
  const estimate = prediction?.estimate_days
  uni.showModal({
    title: '预计日期怎么算',
    content: `取最近 ${sample} 次经期开始的间隔${estimate ? `，平均约 ${estimate} 天` : ''}，从最近一次开始日往后推算。样本不足或间隔波动大时，只提示不可估算。估算仅作参考，实际日期可能不同，不作为避孕依据。`,
    showCancel: false,
    confirmText: '知道了'
  })
}

async function loadFeelings() {
  const first = month.value
  const last = `${month.value.slice(0, 7)}-${String(daysInMonth(month.value)).padStart(2, '0')}`
  try {
    feelings.value = await listFeelings(first, last)
  } catch (failure) {
    if (failure instanceof StaleSessionError) {
      return
    }
    feelings.value = []
  }
}

async function load() {
  try {
    overview.value = await getOverview()
    await loadFeelings()
  } catch (failure) {
    if (failure instanceof StaleSessionError) {
      return
    }
    uni.showToast({
      title: failure instanceof ApiRequestError ? failure.message : '加载失败',
      icon: 'none'
    })
  }
}

async function onSaved() {
  periodFormVisible.value = false
  feelingFormVisible.value = false
  await load()
  uni.showToast({ title: '已保存', icon: 'none' })
}

function removePeriod(item: PeriodItem) {
  uni.showModal({
    title: '删除经期记录',
    content: `${formatDayLabel(item.start_day)} 开始的经期段将被删除，当天感受记录会保留。此操作无法撤销。`,
    confirmText: '删除',
    success: async (result) => {
      if (!result.confirm) {
        return
      }
      try {
        await deletePeriod(item.id)
        await load()
      } catch (failure) {
        uni.showToast({
          title: failure instanceof ApiRequestError ? failure.message : '删除失败',
          icon: 'none'
        })
      }
    }
  })
}

function removeFeeling(day: string) {
  uni.showModal({
    title: '删除感受记录',
    content: `${formatDayLabel(day)} 的经量、症状、影响与备注将被删除，经期日期不受影响。`,
    confirmText: '删除',
    success: async (result) => {
      if (!result.confirm) {
        return
      }
      try {
        await deleteFeeling(day)
        await load()
      } catch (failure) {
        uni.showToast({
          title: failure instanceof ApiRequestError ? failure.message : '删除失败',
          icon: 'none'
        })
      }
    }
  })
}

onShow(load)
</script>

<style scoped>
.status-main {
  font-size: 18px;
  line-height: 26px;
  font-weight: 600;
}
.link.inline {
  margin-left: 6px;
}
.monthbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 4px;
  margin-bottom: 6px;
}
.month-nav {
  width: 40px;
  height: 40px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 20px;
  color: var(--ink-2);
}
.month-label {
  font-size: 15px;
  font-weight: 600;
  letter-spacing: 0.5px;
  color: var(--ink);
}
.weekdays {
  display: flex;
  margin: 6px 0 2px;
}
.weekday {
  flex: 1;
  text-align: center;
  font-size: 12px;
  color: var(--ink-2);
  padding: 6px 0;
}
.grid {
  display: flex;
  flex-wrap: wrap;
  row-gap: 4px;
}
.cell {
  position: relative;
  width: 14.28%;
  height: 46px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 2px;
  border-radius: 8px;
  box-sizing: border-box;
}
.day-number {
  font-size: 15px;
  line-height: 19px;
  color: var(--ink);
  font-variant-numeric: tabular-nums;
}
.day-sub {
  font-size: 9px;
  line-height: 11px;
  color: var(--berry-deep);
}
.cell.actual {
  background: var(--berry-soft);
  border-radius: 0;
}
.cell.actual .day-number {
  color: var(--berry-deep);
}
.cell.start {
  border-top-left-radius: 8px;
  border-bottom-left-radius: 8px;
}
.cell.end {
  border-top-right-radius: 8px;
  border-bottom-right-radius: 8px;
}
.cell.predicted {
  border: 1.5px dashed var(--berry);
  background: transparent;
}
.cell.selected {
  box-shadow: inset 0 0 0 1.5px var(--berry);
  border-radius: 8px;
}
.cell.today .day-number {
  font-weight: 600;
}
.dot {
  position: absolute;
  bottom: 5px;
  width: 4px;
  height: 4px;
  border-radius: 50%;
  background: var(--berry-pink);
}
.cell.actual .dot {
  background: var(--berry);
}
.legend {
  display: flex;
  flex-wrap: wrap;
  gap: 14px;
  margin-top: 12px;
}
.legend-item {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: var(--ink-2);
}
.sw {
  display: inline-block;
  width: 14px;
  height: 14px;
  border-radius: 4px;
}
.sw-period {
  background: var(--berry-soft);
}
.sw-expected {
  border: 1.5px dashed var(--berry);
}
.sw-feel {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--berry-pink);
  margin: 0 4px;
}
.record-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 10px;
}
.record-date {
  font-size: 15px;
  font-weight: 600;
  color: var(--ink);
}
.record-sub {
  margin-top: 4px;
  font-size: 13px;
  line-height: 20px;
  color: var(--ink-2);
}
.record-row {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 10px;
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid var(--card-line);
}
.record-main {
  flex: 1;
  min-width: 0;
  font-size: 14px;
  line-height: 22px;
  color: var(--ink);
}
.record-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}
.record-tags .chip {
  height: 26px;
  padding: 0 10px;
  font-size: 12px;
}
.danger-link {
  flex: 0 0 auto;
  font-size: 12px;
  color: var(--error);
  padding-top: 2px;
}
.empty-line {
  margin-top: 12px;
}
.record-actions {
  display: flex;
  gap: 8px;
  margin-top: 16px;
}
.action {
  flex: 1;
  height: 44px;
  font-size: 14px;
  letter-spacing: 0;
}
.record-note {
  margin-top: 12px;
}
.section {
  margin-top: 24px;
}
.cycle {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 14px 0;
  border-bottom: 1px solid var(--card-line);
}
.cycle:first-child {
  padding-top: 2px;
}
.cycle:last-child {
  padding-bottom: 2px;
  border-bottom: 0;
}
.cycle-date {
  width: 88px;
  flex: 0 0 auto;
}
.dd {
  font-size: 19px;
  line-height: 24px;
  font-weight: 600;
  color: var(--ink);
  font-variant-numeric: tabular-nums;
}
.dm {
  margin-top: 2px;
  font-size: 10.5px;
  line-height: 16px;
  color: var(--ink-2);
}
.cycle-right {
  flex: 1;
  min-width: 0;
  text-align: right;
}
.cr-main {
  font-size: 13px;
  line-height: 20px;
  color: var(--ink-2);
}
.cr-sub {
  margin-top: 2px;
  font-size: 12px;
  line-height: 18px;
  color: var(--ink-2);
}
.footnote {
  margin-top: 10px;
}
</style>
