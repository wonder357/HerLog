<template>
  <view class="hr-page herlog-skin">
    <template v-if="showPair">
      <HerlogHeading title="同部位对比" back-label="选择记录" @back="backToSelection" />
      <view class="skin-alert">光线和角度可能影响两张照片的观感。</view>
      <view class="compare-grid">
        <view v-for="row in orderedPair" :key="row.id" class="skin-panel compare-column">
          <HistoryObservation v-if="pairDetails[row.id]" :observation="pairDetails[row.id]" />
          <template v-else>
            <view class="skin-date">{{ skinMoment(row.captured_at) }}</view>
            <view v-if="pairErrors[row.id]" role="alert">
              <view class="skin-muted">这条记录没有加载成功</view>
              <SkinButton class="skin-button skin-link" @click="loadPairSide(row.id)">重试</SkinButton>
            </view>
            <view v-else class="skin-skeleton" aria-label="正在读取观察" />
          </template>
        </view>
      </view>
    </template>
    <template v-else>
      <HerlogHeading title="照片历史" back-to="/pages/skin/index" back-label="皮肤">
        <template #actions>
          <SkinButton v-if="comparing" class="hr-action" @click="stopCompare">退出对比</SkinButton>
        </template>
      </HerlogHeading>

      <view v-if="comparing" class="skin-panel pick-panel skin-block">
        <view class="pick-head">
          <view class="skin-subtitle">{{ selected.length === 0 ? '选第一条记录' : selected.length === 1 ? '选同部位的第二条记录' : '确认要对比的记录' }}</view>
          <view class="pick-progress" :class="{ done: selected.length === 2 }">{{ selected.length }} / 2</view>
        </view>
        <view class="pick-hint skin-muted">
          {{ selected.length === 2 ? '确认后会并排显示两张照片和观察。' : '同一部位、不同日期的两条记录才能对比。' }}
        </view>
        <view v-for="(row, index) in selected" :key="row.id" class="selection-line">
          <text class="selection-label">{{ index === 0 ? '第一条' : '第二条' }}</text>
          <text class="selection-value">{{ row.site }} {{ skinMoment(row.captured_at) }}</text>
          <SkinButton class="skin-button skin-link selection-remove" @click="removePick(row.id)">移除</SkinButton>
        </view>
        <view v-if="conflict" class="skin-alert skin-alert-error" role="alert">{{ conflict }}</view>
        <SkinButton v-if="selected.length === 2" class="skin-button skin-primary skin-wide pick-confirm" @click="openPair">查看对比</SkinButton>
      </view>

      <scroll-view v-if="comparing" scroll-x :show-scrollbar="false" class="site-scroll hr-rail skin-block">
        <view class="site-filters">
          <SkinButton
            v-for="item in sites" :key="item"
            class="skin-button" :class="{ 'skin-selected': site === item }"
            :aria-pressed="site === item" @click="requestSite(item)"
          >{{ item || '全部部位' }}</SkinButton>
        </view>
      </scroll-view>
      <view v-if="comparing" class="mode-switch skin-block" role="group" aria-label="记录展示方式">
        <SkinButton class="skin-button" :class="{ 'skin-selected': mode === 'list' }" :aria-pressed="mode === 'list'" @click="mode = 'list'">列表</SkinButton>
        <SkinButton class="skin-button" :class="{ 'skin-selected': mode === 'calendar' }" :aria-pressed="mode === 'calendar'" @click="mode = 'calendar'">日历</SkinButton>
      </view>
      <view class="month-toolbar">
        <SkinButton class="skin-button month-arrow" aria-label="上个月" @click="moveMonth(-1)">‹</SkinButton>
        <picker mode="date" :value="selectedDay || month" :end="today" @change="jumpToDay">
          <SkinButton class="skin-button month-label" aria-label="选择日期">{{ formatMonthLabel(month) }}</SkinButton>
        </picker>
        <SkinButton class="skin-button month-arrow" aria-label="下个月" :disabled="month >= startOfMonth(today)" @click="moveMonth(1)">›</SkinButton>
      </view>
      <view v-if="mode === 'calendar'" class="calendar skin-block">
        <view v-for="day in weekdays" :key="day" class="weekday">{{ day }}</view>
        <view v-for="index in grid.leading" :key="'blank-' + index" />
        <SkinButton
          v-for="day in grid.days" :key="day" class="day-cell"
          :class="{ 'day-current': day === selectedDay }"
          :aria-label="formatDayLabel(day) + (daysWithRecords.has(day) ? '，有记录' : '')"
          :aria-pressed="day === selectedDay" :disabled="day > today" @click="selectedDay = day"
        >
          <text class="day-core">
            {{ Number(day.slice(-2)) }}
            <text v-if="daysWithRecords.has(day)" class="day-dot" />
          </text>
        </SkinButton>
        <view class="calendar-key skin-muted"><text class="key-dot" /> 有记录</view>
      </view>

      <view v-if="selectedDay" class="skin-header day-heading">
        <text class="skin-subtitle">{{ formatDayLabel(selectedDay) }}的记录</text>
        <SkinButton class="skin-button skin-link" @click="selectedDay = ''">看整月</SkinButton>
      </view>
      <view v-if="loading && !visibleRows.length" aria-busy="true" aria-label="正在读取历史记录">
        <view class="skin-skeleton" /><view class="skin-skeleton" />
      </view>
      <view v-else-if="loadError" class="skin-alert skin-alert-error" role="alert">
        <view>历史记录没有加载成功</view>
        <SkinButton class="skin-button skin-link" @click="loadMonth()">重试</SkinButton>
      </view>
      <view v-else-if="!visibleRows.length" class="skin-panel skin-empty">
        <HerlogMascot pose="oops" :size="58" alt="" style="margin:0 auto 6px" />
        <view class="empty-title">{{ selectedDay ? '这一天还没有记录' : '这个月还没有符合条件的记录' }}</view>
        <view class="skin-muted">{{ selectedDay ? '换一天，或者看整个月的记录。' : '换个月份或部位试试，也可以先去拍一张。' }}</view>
      </view>
      <view v-for="row in visibleRows" v-else :key="row.id" class="record-row">
        <figure v-if="!comparing" class="photo-history-item">
          <PrivateSkinImage :id="row.id" :label="skinMoment(row.captured_at) + '的照片'" />
          <figcaption>{{ skinMoment(row.captured_at) }}</figcaption>
        </figure>
        <SkinButton v-else class="record-link" @click="openDetail(row.id)">
          <view>{{ row.site }} <text class="skin-date">{{ skinMoment(row.captured_at) }}</text></view>
          <ObservationCopy :observation="row" summary />
        </SkinButton>
        <SkinButton v-if="comparing" class="skin-button" :class="{ 'skin-selected': isSelected(row.id) }" @click="pick(row)">
          {{ isSelected(row.id) ? '已选' : '选择' }}
        </SkinButton>
      </view>

      <HerlogSheet v-if="detailId !== null" title="观察详情" @close="closeDetail">
          <HistoryObservation v-if="detail" :observation="detail" />
          <view v-else-if="detailError" class="skin-alert skin-alert-error" role="alert">
            <view>{{ detailError }}</view>
            <SkinButton v-if="detailRetry" class="skin-button skin-link" @click="openDetail(detailId)">重试</SkinButton>
          </view>
          <view v-else class="skin-skeleton" aria-label="正在读取观察" />
      </HerlogSheet>
    </template>
  </view>
</template>

<script setup lang="ts">
import SkinButton from '../../components/H5Button'
import HerlogHeading from '../../components/HerlogHeading.vue'
import HerlogMascot from '../../components/HerlogMascot.vue'
import HerlogSheet from '../../components/HerlogSheet.vue'
import { computed, ref, watch } from 'vue'
import { onHide, onLoad, onShow, onUnload } from '@dcloudio/uni-app'
import { formatDayLabel, formatMonthLabel, monthGrid, shiftMonth, startOfMonth, todayString } from '../../shared/dates'
import { chronologicalSkinPair, compareSkinRecords, groupSkinDays, skinMoment, skinMonthRange } from '../../shared/skin'
import { ApiRequestError, currentEpoch } from '../../services/httpClient'
import { getObservation, listObservations, SKIN_SITES } from '../../services/skinService'
import type { SkinObservation, SkinSummaryItem } from '../../services/types'
import { useAuthStore } from '../../stores/auth'
import HistoryObservation from './HistoryObservation.vue'
import ObservationCopy from './ObservationCopy.vue'
import PrivateSkinImage from './PrivateSkinImage.vue'
import './skin.css'

const auth = useAuthStore()
const sites = ['', ...SKIN_SITES]
const weekdays = ['一', '二', '三', '四', '五', '六', '日']
const today = ref(todayString())
const month = ref(startOfMonth(today.value))
const site = ref('')
const mode = ref<'list' | 'calendar'>('list')
const selectedDay = ref('')
const rows = ref<SkinSummaryItem[]>([])
const loading = ref(true)
const loadError = ref(false)
const comparing = ref(false)
const selected = ref<SkinSummaryItem[]>([])
const conflict = ref('')
const showPair = ref(false)
const pairDetails = ref<Partial<Record<number, SkinObservation>>>({})
const pairErrors = ref<Partial<Record<number, true>>>({})
const detailId = ref<number | null>(null)
const detail = ref<SkinObservation | null>(null)
const detailError = ref('')
const detailRetry = ref(false)
let monthVersion = 0
let loadedQuery = ''
let detailVersion = 0
let compareVersion = 0
let active = false

const grid = computed(() => monthGrid(month.value))
const daysWithRecords = computed(() => groupSkinDays(rows.value))
const visibleRows = computed(() => selectedDay.value ? daysWithRecords.value.get(selectedDay.value) ?? [] : rows.value)
const orderedPair = computed(() => chronologicalSkinPair(selected.value))

async function loadMonth() {
  const query = `${month.value}:${site.value}`
  const version = ++monthVersion
  const epoch = currentEpoch()
  loading.value = true
  loadError.value = false
  if (query !== loadedQuery) rows.value = []
  try {
    const result = await listObservations({ ...skinMonthRange(month.value), site: site.value || undefined })
    if (version === monthVersion && epoch === currentEpoch()) {
      rows.value = result
      loadedQuery = query
    }
  } catch {
    if (version === monthVersion && epoch === currentEpoch()) loadError.value = true
  } finally {
    if (version === monthVersion) loading.value = false
  }
}

function moveMonth(delta: number) {
  selectedDay.value = ''
  month.value = shiftMonth(month.value, delta)
  void loadMonth()
}

function jumpToDay(event: { detail: { value: string } }) {
  selectedDay.value = event.detail.value
  const nextMonth = startOfMonth(selectedDay.value)
  if (nextMonth !== month.value) {
    month.value = nextMonth
    void loadMonth()
  }
}

function requestSite(next: string) {
  if (next === site.value) return
  if (selected.value.length && next !== selected.value[0].site) {
    uni.showModal({
      title: '更换对比部位',
      content: '更换部位后会清空已选记录。',
      confirmText: '更换',
      success: (answer) => {
        if (answer.confirm) {
          selected.value = []
          applySite(next)
        }
      }
    })
    return
  }
  applySite(next)
}

function applySite(next: string) {
  site.value = next
  conflict.value = ''
  void loadMonth()
}

function startCompare() {
  comparing.value = true
}

function stopCompare() {
  backToSelection()
  comparing.value = false
  selected.value = []
  conflict.value = ''
}

function isSelected(id: number) {
  return selected.value.some((row) => row.id === id)
}

function removePick(id: number) {
  selected.value = selected.value.filter((row) => row.id !== id)
  conflict.value = ''
}

function pick(row: SkinSummaryItem) {
  conflict.value = ''
  const first = selected.value[0]
  if (first) {
    const reason = compareSkinRecords(first, row)
    if (reason) {
      conflict.value = reason
      return
    }
  }
  if (selected.value.length === 2) {
    conflict.value = '已选两条记录。可以移除一条后再选。'
    return
  }
  selected.value = [...selected.value, row]
  if (!first && site.value !== row.site) applySite(row.site)
}

function openPair() {
  if (selected.value.length !== 2) return
  closeDetail()
  backToSelection()
  showPair.value = true
  for (const row of orderedPair.value) void loadPairSide(row.id)
}

async function loadPairSide(id: number) {
  const version = compareVersion
  const epoch = currentEpoch()
  delete pairErrors.value[id]
  try {
    const record = await getObservation(id)
    if (version === compareVersion && epoch === currentEpoch()) pairDetails.value[id] = record
  } catch (failure) {
    if (version !== compareVersion || epoch !== currentEpoch()) return
    if (failure instanceof ApiRequestError && failure.status === 404) {
      backToSelection()
      removePick(id)
      conflict.value = '有一条记录无法读取，请重新选择'
    } else {
      pairErrors.value[id] = true
    }
  }
}

function backToSelection() {
  compareVersion += 1
  showPair.value = false
  pairDetails.value = {}
  pairErrors.value = {}
}

async function openDetail(id: number) {
  const version = ++detailVersion
  const epoch = currentEpoch()
  detailId.value = id
  detail.value = null
  detailError.value = ''
  detailRetry.value = false
  try {
    const record = await getObservation(id)
    if (version === detailVersion && epoch === currentEpoch()) detail.value = record
  } catch (failure) {
    if (version !== detailVersion || epoch !== currentEpoch()) return
    detailRetry.value = !(failure instanceof ApiRequestError && failure.status === 404)
    detailError.value = detailRetry.value ? '这条记录没有加载成功' : '这条记录已无法查看'
  }
}

function closeDetail() {
  detailVersion += 1
  detailId.value = null
  detail.value = null
}

function clearPrivateState() {
  monthVersion += 1
  loadedQuery = ''
  rows.value = []
  closeDetail()
  stopCompare()
}

watch(() => auth.token, () => {
  clearPrivateState()
  if (active && auth.token) void loadMonth()
})
onLoad((options) => {
  if (options?.compare === '1') startCompare()
  const day = options?.day
  if (typeof day === 'string' && /^\d{4}-\d{2}-\d{2}$/.test(day) && day <= today.value) {
    month.value = startOfMonth(day)
    selectedDay.value = day
  }
})
onShow(() => {
  active = true
  today.value = todayString()
  if (auth.token) void loadMonth()
})
onHide(() => {
  active = false
  clearPrivateState()
})
onUnload(() => {
  active = false
  clearPrivateState()
})
</script>

<style scoped>
/* ---- 记录卡片与照片 ---- */
.photo-history-item { width: 100%; margin: 0; }
.photo-history-item :deep(.skin-photo) { max-height: 240px; border-radius: 14px; }
.photo-history-item figcaption { margin-top: 8px; font-size: 12.5px; color: var(--skin-muted); }
.record-row {
  display: grid; grid-template-columns: minmax(0, 1fr) auto; align-items: center; gap: 10px;
  margin-bottom: 10px; padding: 12px 12px 12px 14px;
  border: 1px solid var(--skin-line); border-radius: 16px; background: var(--skin-surface);
}
.record-row > .photo-history-item { grid-column: 1 / -1; }
.record-link {
  min-width: 0; margin: 0; padding: 0; border: 0; text-align: start;
  background: transparent; color: var(--skin-ink); font-size: 14px; line-height: 1.5;
}
.record-link::after, .day-cell::after { border: 0; }
.record-link:focus-visible, .day-cell:focus-visible { outline: 2px solid var(--skin-rose); outline-offset: -2px; }
.record-row .skin-date { margin-left: 4px; font-size: 12.5px; }

/* ---- 对比选择 ---- */
.pick-panel { padding: 14px 14px 16px; }
.pick-head { display: flex; align-items: center; justify-content: space-between; gap: 8px; }
.pick-progress {
  flex: 0 0 auto; padding: 2px 10px; border-radius: 999px;
  color: var(--skin-rose-deep); background: var(--skin-rose-soft);
  font-size: 12.5px; font-weight: 650; font-variant-numeric: tabular-nums;
}
.pick-progress.done { color: #fff; background: var(--skin-rose); }
.pick-hint { margin-top: 5px; font-size: 12.5px; line-height: 1.5; }
.selection-line {
  display: flex; align-items: center; gap: 8px;
  margin-top: 10px; padding: 4px 4px 4px 12px;
  border-radius: 12px; background: var(--skin-rose-soft); font-size: 13px;
}
.selection-label { flex: 0 0 auto; color: var(--skin-rose-deep); font-weight: 650; }
.selection-value { flex: 1; min-width: 0; overflow-wrap: anywhere; }
.herlog-skin .selection-remove { flex: 0 0 auto; min-height: 36px; padding: 4px 10px; font-size: 12.5px; }
.herlog-skin .pick-confirm { margin-top: 12px; }

/* ---- 部位筛选：横向滑动，不露滚动条（滚动条与渐隐见 .hr-rail） ---- */
.site-filters { display: flex; width: max-content; gap: 8px; padding: 2px 30px 2px 0; }
.herlog-skin .site-filters .skin-button { min-height: 40px; padding: 6px 14px; font-size: 13.5px; white-space: nowrap; }
.herlog-skin .site-filters .skin-selected {
  border-color: var(--skin-rose); background: var(--skin-rose-soft);
  color: var(--skin-rose-deep); font-weight: 650;
}

/* ---- 列表 / 日历分段控件 ---- */
.herlog-skin .mode-switch {
  display: flex; align-items: center; gap: 2px; padding: 3px;
  border: 1px solid var(--skin-line); border-radius: 999px; background: var(--skin-surface);
}
.herlog-skin .mode-switch > .skin-button {
  flex: 1; min-width: 0; min-height: 40px; padding: 6px 10px;
  border-color: transparent; background: transparent; color: var(--skin-muted); font-size: 13.5px;
}
.herlog-skin .mode-switch > .skin-selected {
  border-color: transparent; background: var(--skin-rose-soft);
  color: var(--skin-rose-deep); font-weight: 650;
}

/* ---- 月份切换 ---- */
.month-toolbar { display: flex; align-items: center; justify-content: space-between; gap: 8px; margin-bottom: 14px; }
.herlog-skin .month-arrow {
  display: grid; place-items: center; width: 40px; min-width: 40px; min-height: 40px; padding: 0;
  border-color: transparent; border-radius: 50%; background: var(--skin-rose-soft);
  color: var(--skin-rose-deep); font-size: 17px; line-height: 1;
}
.herlog-skin .month-arrow[disabled] { color: #dcc4cd; background: var(--skin-surface); opacity: 1; }
.herlog-skin .month-label {
  min-height: 40px; padding: 4px 16px; border-color: var(--skin-line); border-radius: 999px;
  background: var(--skin-surface); color: var(--skin-ink);
  font-family: var(--hr-font); font-size: 16px; font-weight: 650;
}

/* ---- 日历 ---- */
.calendar { display: grid; grid-template-columns: repeat(7, minmax(0, 1fr)); padding: 10px 0 4px; }
.weekday { padding-bottom: 6px; text-align: center; color: var(--skin-muted); font-size: 12.5px; }
.day-cell {
  display: grid; place-items: center; width: 100%; min-height: 44px; padding: 0; margin: 0;
  border: 0; color: var(--skin-ink); background: transparent;
}
.day-cell[disabled] { color: var(--skin-muted); opacity: .45; background: transparent; }
.day-core {
  position: relative; display: grid; place-items: center; width: 36px; height: 36px;
  border: 1px solid transparent; border-radius: 12px; font: 15px var(--hr-font);
}
.day-current .day-core { border-color: var(--skin-rose); color: var(--skin-rose-deep); background: var(--skin-rose-soft); }
.day-dot, .key-dot { width: 5px; height: 5px; border-radius: 50%; background: var(--skin-rose); }
.day-dot { position: absolute; bottom: 5px; }
.key-dot { display: inline-block; margin-right: 4px; }
.calendar-key { grid-column: 1 / -1; padding-top: 8px; font-size: 12.5px; }

/* ---- 空状态 ---- */
.herlog-skin .skin-empty { padding: 26px 18px; text-align: center; border-style: dashed; }
.skin-empty .empty-title { font-size: 15px; font-weight: 600; color: var(--skin-ink); }
.skin-empty .skin-muted { margin-top: 6px; font-size: 12.5px; line-height: 1.55; }

/* ---- 日筛选与对比视图 ---- */
.herlog-skin .day-heading { margin-bottom: 10px; }
.compare-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 8px; align-items: start; }
.compare-column { min-width: 0; padding: 10px; }
</style>
