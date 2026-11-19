<template>
  <view class="page">
    <view class="card status-card">
      <view class="status-title">{{ overview?.status.message || '加载中…' }}</view>
      <view v-if="predictionHint" class="muted">{{ predictionHint }}</view>
      <view v-if="overview?.prediction.status === 'overdue'" class="link" @tap="openPeriodForm">
        补记经期开始 ›
      </view>
    </view>

    <view class="card">
      <view class="month-row">
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
          <text v-if="feelingDays.has(day)" class="dot" />
        </view>
      </view>
      <view class="legend">
        <view class="legend-item"><text class="swatch actual" />实际经期</view>
        <view class="legend-item"><text class="swatch feeling" />有感受</view>
        <view class="legend-item"><text class="swatch predicted" />预计开始</view>
      </view>
    </view>

    <view class="card">
      <view class="section-title">{{ formatDayLabel(selected) }}</view>
      <view v-if="selectedPeriod" class="record">
        <view class="record-main">
          {{ formatDayLabel(selectedPeriod.start_day) }} 开始
          <text v-if="selectedPeriod.end_day">
            · {{ formatDayLabel(selectedPeriod.end_day) }} 结束
          </text>
          <text v-else>· 未记录结束</text>
        </view>
        <view class="record-actions">
          <text class="danger" @tap="removePeriod(selectedPeriod)">删除</text>
        </view>
      </view>
      <view v-if="selectedFeeling" class="record">
        <view class="record-main">
          <text v-if="selectedFeeling.flow">经量：{{ selectedFeeling.flow }}　</text>
          <text v-if="selectedFeeling.symptoms.length">症状：{{ selectedFeeling.symptoms.join('、') }}　</text>
          <text v-if="selectedFeeling.impact">影响：{{ selectedFeeling.impact }}</text>
          <view v-if="selectedFeeling.note" class="muted">{{ selectedFeeling.note }}</view>
        </view>
        <view class="record-actions">
          <text class="danger" @tap="removeFeeling(selected)">删除</text>
        </view>
      </view>
      <view v-if="!selectedPeriod && !selectedFeeling" class="muted">这一天还没有记录。</view>
      <view class="day-actions">
        <view class="ghost action" @tap="openPeriodForm">记录经期</view>
        <view class="ghost action" @tap="openFeelingForm">记录感受</view>
      </view>
    </view>

    <view class="card">
      <view class="section-title">历史周期</view>
      <view v-if="items.length === 0" class="muted">还没有经期记录。</view>
      <view v-for="item in items" :key="item.id" class="history-row" @tap="selected = item.start_day">
        <view>
          <view>{{ formatDayLabel(item.start_day) }} 开始</view>
          <view class="muted">
            {{ item.duration_days ? `持续 ${item.duration_days} 天` : '未记录结束' }}
            <text v-if="item.cycle_days"> · 距上次 {{ item.cycle_days }} 天</text>
          </view>
        </view>
        <text class="danger" @tap.stop="removePeriod(item)">删除</text>
      </view>
    </view>

    <view v-if="openPeriod" class="card">
      <view class="section-title">进行中的记录</view>
      <view class="muted">
        {{ formatDayLabel(openPeriod.start_day) }} 开始，还没有结束日。选中最后一天后点「记录经期」即可补记。
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

const predictionHint = computed(() => {
  const prediction = overview.value?.prediction
  if (!prediction) {
    return ''
  }
  if (prediction.status === 'overdue') {
    return `${prediction.message}。预计日期不会自动顺延。`
  }
  if (prediction.status === 'insufficient' || prediction.status === 'irregular') {
    return prediction.message
  }
  return `${prediction.message}（按约 ${prediction.estimate_days} 天周期估算，实际日期可能不同，不作为避孕依据）`
})

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
    'predicted-day': day === predictedDay.value
  }
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
.page {
  min-height: 100vh;
  padding: 12px 16px 76px;
  box-sizing: border-box;
}
.status-card {
  background: #fdf2ef;
}
.status-title {
  font-size: 17px;
  font-weight: 600;
  margin-bottom: 4px;
}
.link {
  margin-top: 8px;
  color: #b4544a;
  font-size: 13px;
}
.month-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 10px;
}
.month-nav {
  width: 32px;
  text-align: center;
  font-size: 20px;
  color: #8a7f7a;
}
.month-label {
  font-size: 15px;
  font-weight: 600;
}
.weekdays {
  display: flex;
  margin-bottom: 4px;
}
.weekday {
  flex: 1;
  text-align: center;
  font-size: 11px;
  color: #a89d98;
}
.grid {
  display: flex;
  flex-wrap: wrap;
}
.cell {
  width: 14.28%;
  height: 44px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  position: relative;
  font-size: 13px;
}
.day-number {
  line-height: 1;
}
.cell.actual {
  background: #f6ded9;
  border-radius: 10px;
  color: #8c3f37;
}
.cell.start {
  background: #b4544a;
  color: #ffffff;
}
.cell.predicted-day .day-number {
  border: 1px dashed #b4544a;
  border-radius: 8px;
  padding: 2px 5px;
  color: #b4544a;
}
.cell.selected {
  outline: 2px solid #b4544a;
  outline-offset: -2px;
  border-radius: 10px;
}
.cell.today .day-number {
  font-weight: 700;
}
.dot {
  position: absolute;
  bottom: 5px;
  width: 5px;
  height: 5px;
  border-radius: 50%;
  background: #8a7f7a;
}
.legend {
  display: flex;
  gap: 12px;
  margin-top: 10px;
  font-size: 11px;
  color: #8a7f7a;
}
.legend-item {
  display: flex;
  align-items: center;
  gap: 4px;
}
.swatch {
  width: 12px;
  height: 12px;
  border-radius: 3px;
  display: inline-block;
}
.swatch.actual {
  background: #f6ded9;
}
.swatch.feeling {
  width: 5px;
  height: 5px;
  border-radius: 50%;
  background: #8a7f7a;
}
.swatch.predicted {
  border: 1px dashed #b4544a;
}
.section-title {
  font-size: 15px;
  font-weight: 600;
  margin-bottom: 8px;
}
.record {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  padding: 10px 0;
  border-bottom: 1px solid #f4ebe7;
}
.record-main {
  font-size: 14px;
  line-height: 1.6;
}
.record-actions {
  display: flex;
  gap: 12px;
}
.danger {
  color: #c0392b;
  font-size: 13px;
}
.day-actions {
  display: flex;
  gap: 10px;
  margin-top: 12px;
}
.action {
  flex: 1;
  font-size: 14px;
}
.history-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 0;
  border-bottom: 1px solid #f4ebe7;
  font-size: 14px;
}
</style>
