<template>
  <view class="hr-page hr-tab-page cycle-page">
    <HerlogHeading title="经期" />
    <view class="status-card">
      <view v-if="loadError" class="status-title" role="alert">{{ loadError }}</view>
      <view v-else class="status-title">{{ overview?.status.message || '正在读取周期记录…' }}</view>
      <H5Button v-if="loadError" class="hr-action" @click="load">重试</H5Button>
      <view v-if="predictionHint" class="muted">{{ predictionHint }}</view>
      <H5Button v-if="overview?.prediction.status === 'overdue'" class="hr-action" @click="openPeriodForm">
        补记经期开始
      </H5Button>
    </view>

    <view class="card calendar-card">
      <view class="month-row">
        <H5Button class="month-nav" aria-label="上个月" @click="shift(-1)">‹</H5Button>
        <h2 class="month-label">{{ formatMonthLabel(month) }}</h2>
        <H5Button class="month-nav" aria-label="下个月" @click="shift(1)">›</H5Button>
      </view>
      <view class="grid">
        <text v-for="name in weekdays" :key="name" class="weekday">{{ name }}</text>
        <view v-for="blank in grid.leading" :key="'blank-' + blank" />
        <H5Button v-for="day in grid.days" :key="day" class="cell" :class="cellClass(day)"
          :aria-pressed="day === selected" :aria-current="day === today ? 'date' : undefined"
          :aria-label="dayLabel(day)" @click="selected = day">
          <span class="day-number">{{ Number(day.slice(-2)) }}</span>
          <span v-if="feelingDays.has(day)" class="dot" />
        </H5Button>
      </view>
      <view class="legend">
        <view><span class="swatch actual" />实际经期</view>
        <view><span class="swatch feeling" />有感受</view>
        <view><span class="swatch predicted" />预计开始</view>
      </view>
    </view>

    <view class="card day-card">
      <view class="section-head">
        <h2 class="hr-section-title">{{ formatDayLabel(selected) }}</h2>
        <text v-if="selected === today" class="selected-today">今天</text>
      </view>
      <view v-if="selectedPeriod" class="record">
        <view>
          {{ formatDayLabel(selectedPeriod.start_day) }} 开始
          <text v-if="selectedPeriod.end_day"> · {{ formatDayLabel(selectedPeriod.end_day) }} 结束</text>
          <text v-else> · 等待记录结束</text>
        </view>
        <H5Button class="hr-action danger" @click="removePeriod(selectedPeriod)">删除经期</H5Button>
      </view>
      <view v-if="selectedFeeling" class="record">
        <view>
          <text v-if="selectedFeeling.flow">经量 {{ selectedFeeling.flow }}　</text>
          <text v-if="selectedFeeling.symptoms.length">{{ selectedFeeling.symptoms.join('、') }}　</text>
          <text v-if="selectedFeeling.impact">{{ selectedFeeling.impact }}</text>
          <view v-if="selectedFeeling.note" class="muted">{{ selectedFeeling.note }}</view>
        </view>
        <H5Button class="hr-action danger" @click="removeFeeling(selected)">删除感受</H5Button>
      </view>
      <view v-if="!selectedPeriod && !selectedFeeling" class="muted">这一天还没有记录。</view>
      <view class="day-actions">
        <H5Button class="primary" @click="openPeriodForm">记录经期</H5Button>
        <H5Button class="ghost" @click="openFeelingForm">记录感受</H5Button>
      </view>
    </view>

    <view class="card">
      <view class="section-head"><h2 class="hr-section-title">历史周期</h2></view>
      <view v-if="!items.length" class="muted">还没有经期记录。</view>
      <view v-for="item in items" :key="item.id" class="record history-row">
        <H5Button class="history-date" @click="selectHistory(item.start_day)">
          <span>{{ formatDayLabel(item.start_day) }} 开始</span>
          <span class="muted">
            {{ item.duration_days ? '持续 ' + item.duration_days + ' 天' : '等待记录结束' }}
            <text v-if="item.cycle_days"> · 距上次 {{ item.cycle_days }} 天</text>
          </span>
        </H5Button>
        <H5Button class="hr-action danger" @click="removePeriod(item)">删除</H5Button>
      </view>
    </view>

    <view v-if="openPeriod" class="card followup">
      <view class="section-head"><h2 class="hr-section-title">进行中的记录</h2></view>
      <view class="muted">{{ formatDayLabel(openPeriod.start_day) }} 开始。选中最后一天后点「记录经期」即可补记。</view>
    </view>

    <PeriodForm :visible="periodFormVisible" :day="selected"
      :open-period="openPeriod ? { id: openPeriod.id, startDay: openPeriod.start_day } : null"
      @close="periodFormVisible = false" @saved="onSaved" />
    <FeelingForm :visible="feelingFormVisible" :day="selected" :existing="selectedFeeling"
      @close="feelingFormVisible = false" @saved="onSaved" />
    <TabBar current="/pages/period/index" />
  </view>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { onShow } from '@dcloudio/uni-app'
import H5Button from '../../components/H5Button'
import HerlogHeading from '../../components/HerlogHeading.vue'
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
const loadError = ref('')
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

function dayLabel(day: string): string {
  return [
    formatDayLabel(day),
    actualDays.value.has(day) ? '实际经期' : '',
    day === predictedDay.value ? '预计开始' : '',
    feelingDays.value.has(day) ? '有感受记录' : ''
  ].filter(Boolean).join('，')
}

function selectHistory(day: string) {
  selected.value = day
  if (month.value !== startOfMonth(day)) {
    month.value = startOfMonth(day)
    void loadFeelings()
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
  loadError.value = ''
  try {
    overview.value = await getOverview()
    await loadFeelings()
  } catch (failure) {
    if (failure instanceof StaleSessionError) {
      return
    }
    loadError.value = failure instanceof ApiRequestError ? `周期记录加载失败：${failure.message}` : '周期记录加载失败'
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
.status-card {
  padding: 14px 16px; margin-bottom: 12px;
  border: 1px solid var(--hr-line); border-radius: var(--hr-radius); background: var(--hr-rose-soft);
}
.status-title { margin: 0 0 3px; color: var(--hr-rose-deep); font-size: 16px; font-weight: 650; }
.status-card .hr-action { padding-left: 0; }
.calendar-card { padding: 10px 10px 14px; }
.month-row { display: flex; justify-content: space-between; align-items: center; gap: 8px; margin-bottom: 6px; }
.month-nav {
  display: grid; place-items: center; width: 44px; min-height: 44px; padding: 0; border: 0; border-radius: 10px;
  color: var(--hr-rose-deep); background: transparent; font: 26px var(--hr-font);
}
.month-label {
  margin: 0; font-family: var(--hr-serif); font-size: 19px; font-weight: 650; font-variant-numeric: tabular-nums;
}
.grid { display: grid; grid-template-columns: repeat(7, minmax(0, 1fr)); gap: 2px; }
.weekday { text-align: center; color: var(--hr-ink-2); font-size: 12px; padding: 4px 0; }
.cell {
  position: relative; display: grid; place-items: center; min-height: 44px; min-width: 0;
  padding: 1px; border: 1px solid transparent; border-radius: 9px; color: var(--hr-ink);
  background: transparent; font: 17px var(--hr-serif);
}
.cell[aria-current='date'] .day-number { font-weight: 700; text-decoration: underline; text-underline-offset: 3px; }
.cell.actual { background: var(--hr-rose-soft); color: var(--hr-rose-deep); }
.cell.start { background: var(--hr-rose); color: #fff; }
.cell.predicted-day .day-number { padding: 4px 6px; border: 1px dashed var(--hr-plum); border-radius: 8px; color: var(--hr-plum); }
.cell.selected { border-color: var(--hr-rose-deep); box-shadow: inset 0 0 0 1px var(--hr-rose-deep); }
.dot { position: absolute; bottom: 5px; width: 5px; height: 5px; background: var(--hr-taupe); border-radius: 50%; }
.cell.start .dot { background: #fff; }
.legend { display: flex; flex-wrap: wrap; gap: 7px 12px; margin: 11px 0 0; color: var(--hr-ink-2); font-size: 12px; }
.legend view, .legend uni-view { display: flex; align-items: center; gap: 5px; }
.swatch { display: inline-block; width: 11px; height: 11px; border-radius: 4px; }
.swatch.actual { background: var(--hr-rose-soft); border: 1px solid var(--hr-rose); }
.swatch.feeling { width: 6px; height: 6px; border-radius: 50%; background: var(--hr-taupe); }
.swatch.predicted { border: 1px dashed var(--hr-plum); }
.section-head { display: flex; justify-content: space-between; align-items: center; gap: 8px; margin: 0 0 8px; }
.section-head h2 { margin: 0; }
.selected-today { padding: 2px 8px; background: var(--hr-rose-soft); color: var(--hr-rose-deep); border-radius: 99px; font-size: 12px; }
.record { display: flex; justify-content: space-between; align-items: center; gap: 8px; border-top: 1px solid var(--hr-line); font-size: 14px; }
.record .hr-action { flex-shrink: 0; padding-inline: 4px; font-size: 13px; }
.danger { color: var(--hr-danger); }
.history-date {
  display: grid; justify-items: start; min-height: 52px; text-align: left; padding: 6px 0; border: 0; color: var(--hr-ink);
  border-radius: 7px; background: transparent; font-size: 15px;
}
.day-actions { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; margin-top: 13px; }
.followup { background: var(--hr-peach); }
</style>
