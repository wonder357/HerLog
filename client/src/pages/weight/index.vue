<template>
  <view class="hr-page hr-tab-page weight-page">
    <HerlogHeading title="体重">
      <template #actions>
        <H5Button v-if="section === 'overview'" class="hr-action" @click="openDetail">记录明细</H5Button>
      </template>
    </HerlogHeading>
    <view class="weight-shell">
      <view class="weight-tabs" role="group" aria-label="体重模块">
        <H5Button v-for="item in tabs" :key="item.code" class="weight-tab" :class="{ chosen: section === item.code }"
          :aria-pressed="section === item.code" @click="navigate(item.code)">{{ item.label }}</H5Button>
      </view>
      <template v-if="section === 'overview'">
        <view class="weight-hero">
          <view class="weight-eyebrow">最近一次测量</view>
          <view v-if="summary?.latest_grams != null" class="weight-value">{{ formatKg(summary.latest_grams) }} <text>kg</text></view>
          <view v-else class="weight-value empty">{{ loading ? '正在读取…' : '开始记录体重' }}</view>
          <view v-if="summary?.latest_measured_at" class="weight-muted">{{ formatMoment(summary.latest_measured_at) }} 测量</view>
          <view class="weight-actions">
            <H5Button class="primary" @click="formVisible = true">记体重</H5Button>
          </view>
        </view>
        <view v-if="error" class="weight-error" role="alert">{{ error }} <H5Button @click="load">重试</H5Button></view>
        <section class="weight-panel trend-panel" aria-labelledby="weight-trend" :aria-busy="loading && !showSample">
          <view class="weight-header">
            <h2 id="weight-trend" class="weight-heading">体重趋势</h2>
            <view class="weight-options" role="group" aria-label="趋势范围">
              <H5Button v-for="interval in intervals" :key="interval" class="weight-range" :class="{ chosen: days === interval }"
                :aria-pressed="days === interval" @click="setDays(interval)">近 {{ interval }} 天</H5Button>
            </view>
          </view>
          <view class="trend-meta">
            <view class="trend-meta-copy">
              <span v-if="showSample" class="sample-badge">示例数据</span>
              <span class="weight-muted">{{ formatDayLabel(trendStart) }} – {{ formatDayLabel(today) }}</span>
            </view>
            <H5Button class="hr-action trend-switch" @click="toggleSample">{{ showSample ? '查看我的记录' : '查看示例' }}</H5Button>
          </view>
          <TrendChart v-if="showSample || !loading || summary" :points="chartPoints" :from="trendStart" :to="today"
            :example="showSample" :context="!showSample && showCycle ? summary?.cycle_context : undefined" />
          <view v-else class="trend-loading weight-muted" role="status">正在读取趋势…</view>
          <view v-if="!showSample && summary && summary.days !== days" class="weight-muted" role="status">{{ loading ? '正在更新 · ' : '' }}当前显示近 {{ summary.days }} 天</view>
          <view class="weight-stats">
            <view><strong>{{ showSample ? chartPoints.length : summary?.count ?? '—' }}</strong><text>{{ showSample ? '示例次数' : '记录次数' }}</text></view>
            <view><strong>{{ showSample ? chartPoints.length : summary?.record_days ?? summary?.points.length ?? '—' }}</strong><text>{{ showSample ? '示例记录日' : '记录日' }}</text></view>
            <view v-if="chartDelta !== null"><strong>{{ formatDelta(chartDelta) }}</strong><text>{{ showSample ? '示例首尾变化' : '首尾变化' }}</text></view>
          </view>
          <p class="weight-muted trend-note">{{ showSample ? '虚构测量用于预览，缺测日期留空。' : '每天取最后一次测量，缺测日期留空。' }}</p>
          <H5Button v-if="!showSample" class="weight-secondary" @click="showCycle = !showCycle; load()">{{ showCycle ? '关闭周期背景' : '显示周期背景' }}</H5Button>
          <template v-if="!showSample && showCycle && summary?.cycle_context">
            <view class="weight-muted">阶段按记录估算，仅供回看，不用于诊断或避孕。</view>
            <scroll-view scroll-x class="weight-cycle">
              <view class="cycle-row">
                <H5Button v-for="item in summary.cycle_context" :key="item.day" class="cycle-day"
                 :class="[item.phase, { chosen: activeDay === item.day }]" @click="activeDay = item.day">{{ Number(item.day.slice(-2)) }}</H5Button>
              </view>
            </scroll-view>
            <view v-if="selectedPhase" class="weight-muted">
              {{ formatDayLabel(selectedPhase.day) }} · {{ phaseNames[selectedPhase.phase] }}{{ selectedPhase.basis === 'estimated' ? '（估算）' : selectedPhase.basis === 'recorded' ? '（已记录）' : '' }}
            </view>
            <view v-if="selectedPhase?.note" class="weight-note">{{ selectedPhase.note }}</view>
          </template>
        </section>
        <view class="weight-panel">
          <view class="weight-header">
            <view class="weight-heading">相邻时段对比</view>
            <H5Button class="weight-secondary" @click="toggleCompare">{{ comparing ? '收起' : '看对比' }}</H5Button>
          </view>
          <template v-if="comparing">
            <view v-if="compareError" class="weight-error" role="alert">{{ compareError }} <H5Button @click="loadComparison">重试</H5Button></view>
            <view v-if="comparisonLoading" class="weight-muted" role="status">正在读取近 {{ days }} 天对比…</view>
            <template v-if="comparison">
              <view v-if="comparisonDays !== days" class="weight-muted">当前显示近 {{ comparisonDays }} 天对比</view>
              <view class="compare-columns">
                <view v-for="window in [comparison.previous, comparison.current]" :key="window.start_day">
                  <view>{{ formatDayLabel(window.start_day) }}–{{ formatDayLabel(window.end_day) }}</view>
                  <view class="weight-muted">{{ window.coverage_days }} 个记录日 · {{ window.count }} 笔</view>
                  <view v-if="window.avg_kg != null">日均 {{ window.avg_kg }} kg</view>
                </view>
              </view>
              <view class="weight-muted">{{ comparison.message }}</view>
            </template>
          </template>
        </view>
      </template>
      <ExerciseSpace v-else-if="section === 'movement'" @share="openShare" />
      <ExerciseDiscussion v-else-if="pageVisible && auth.token" :key="auth.token" :reference="shareReference"
        @clear-reference="shareReference = null" />
    </view>
    <WeightForm :visible="formVisible" @close="formVisible = false" @saved="onSaved" />
    <TabBar current="/pages/weight/index" />
  </view>
</template>

<script setup lang="ts">
import H5Button from '../../components/H5Button'
import HerlogHeading from '../../components/HerlogHeading.vue'
import { computed, ref, watch } from 'vue'
import { onHide, onShow } from '@dcloudio/uni-app'
import TabBar from '../../components/TabBar.vue'
import WeightForm from '../../components/WeightForm.vue'
import TrendChart from '../../components/TrendChart.vue'
import ExerciseDiscussion from './ExerciseDiscussion.vue'
import ExerciseSpace from './ExerciseSpace.vue'
import { formatDayLabel, formatMoment, todayString } from '../../shared/dates'
import { formatDelta, formatKg, rangeStart, trendExample } from '../../shared/weight'
import { currentEpoch } from '../../services/httpClient'
import { getComparison, getSummary } from '../../services/weightService'
import type { WeightSummary } from '../../services/types'
import { phaseNames } from '../../services/wellnessService'
import type { ShareReference } from '../../services/wellnessService'
import { useAuthStore } from '../../stores/auth'

const tabs = [{ code: 'overview', label: '体重记录' }, { code: 'movement', label: '运动专区' }, { code: 'discussion', label: '运动讨论' }] as const
const intervals = [7, 30] as const
type Section = typeof tabs[number]['code']
const section = ref<Section>('overview')
const days = ref<7 | 30>(30)
const today = ref(todayString())
const summary = ref<WeightSummary | null>(null)
const previewChoice = ref<'automatic' | 'sample' | 'records'>('automatic')
const comparison = ref<Awaited<ReturnType<typeof getComparison>> | null>(null)
const comparisonDays = ref<7 | 30>(30)
const comparisonLoading = ref(false)
const showCycle = ref(false)
const activeDay = ref('')
const comparing = ref(false)
const loading = ref(false)
const error = ref('')
const compareError = ref('')
const formVisible = ref(false)
const pageVisible = ref(false)
const shareReference = ref<ShareReference | null>(null)
const auth = useAuthStore()
let summaryVersion = 0
let comparisonVersion = 0
const showSample = computed(() => previewChoice.value === 'sample' || (previewChoice.value === 'automatic' &&
  !!summary.value && !error.value && summary.value.points.length < 2))
const trendStart = computed(() => rangeStart(showSample.value ? days.value : summary.value?.days ?? days.value, today.value))
const chartPoints = computed(() => showSample.value ? trendExample(days.value, today.value)
  : (summary.value?.points ?? []).map(point => ({ day: point.day, kg: point.kg })))
const chartDelta = computed(() => {
  if (!showSample.value) return summary.value?.delta_grams ?? null
  const points = chartPoints.value
  return Math.round((points[points.length - 1].kg - points[0].kg) * 1000)
})
const selectedPhase = computed(() => summary.value?.cycle_context?.find(item => item.day === activeDay.value))
watch(() => auth.token, () => {
  summaryVersion += 1
  comparisonVersion += 1
  summary.value = null
  previewChoice.value = 'automatic'
  loading.value = false
  comparison.value = null
  comparisonLoading.value = false
  shareReference.value = null
  formVisible.value = false
  section.value = 'overview'
  if (auth.token) void load()
})
async function load() {
  const version = ++summaryVersion
  const epoch = currentEpoch()
  error.value = ''
  today.value = todayString()
  loading.value = true
  try {
    const data = await getSummary(days.value, showCycle.value)
    if (version === summaryVersion && epoch === currentEpoch()) {
      summary.value = data
      activeDay.value = data.cycle_context?.some(item => item.day === activeDay.value)
        ? activeDay.value : data.cycle_context?.at(-1)?.day ?? ''
    }
  } catch {
    if (version === summaryVersion && epoch === currentEpoch()) error.value = '体重数据没有加载成功'
  } finally {
    if (version === summaryVersion) loading.value = false
  }
}
async function loadComparison() {
  const version = ++comparisonVersion
  const epoch = currentEpoch()
  const interval = days.value
  comparisonLoading.value = true
  compareError.value = ''
  try {
    const data = await getComparison(interval)
    if (version === comparisonVersion && epoch === currentEpoch()) {
      comparison.value = data
      comparisonDays.value = interval
    }
  } catch {
    if (version === comparisonVersion && epoch === currentEpoch()) compareError.value = '对比没有加载成功'
  } finally {
    if (version === comparisonVersion) comparisonLoading.value = false
  }
}
function toggleCompare() {
  comparing.value = !comparing.value
  if (comparing.value) void loadComparison()
}
function setDays(interval: 7 | 30) {
  if (days.value === interval) return
  days.value = interval
  void load()
  if (comparing.value) void loadComparison()
}
function toggleSample() {
  previewChoice.value = showSample.value ? 'records' : 'sample'
}
function navigate(next: Section) {
  if (next !== 'discussion') shareReference.value = null
  section.value = next
}
function openShare(reference: ShareReference) {
  shareReference.value = reference
  section.value = 'discussion'
}
function openDetail() { uni.navigateTo({ url: '/pages/weight/detail' }) }
function onSaved() {
  formVisible.value = false
  previewChoice.value = 'records'
  void load()
  if (comparing.value) void loadComparison()
}
onShow(() => {
  pageVisible.value = true
  if (auth.token) void load()
  else uni.reLaunch({ url: '/pages/login/index' })
})
onHide(() => { formVisible.value = false; pageVisible.value = false; shareReference.value = null })
</script>

<style scoped>
.weight-shell { display: grid; grid-template-columns: minmax(0, 1fr); gap: 12px; }
.weight-tabs,.weight-actions,.weight-options,.weight-header { display: flex; align-items: center; gap: 8px; }
.weight-tabs,.weight-options { padding: 3px; gap: 2px; border: 1px solid var(--hr-line); background: var(--hr-surface); border-radius: 999px; }
.weight-tab,.weight-range,.cycle-day,.weight-secondary,.weight-error button {
  border: 1px solid transparent; border-radius: 999px; padding: 7px 10px; min-height: 44px;
  font-size: 13px; line-height: 1.4; background: var(--hr-paper-deep); color: var(--hr-rose-deep);
}
.weight-tab,.weight-range { margin: 0; background: transparent; color: var(--hr-ink-2); white-space: nowrap; }
.weight-tab { flex: 1; min-width: 0; padding-inline: 3px; }
.weight-tab.chosen,.weight-range.chosen { background: var(--hr-rose-soft); color: var(--hr-rose-deep); font-weight: 650; }
.weight-range { padding-inline: 10px; }
.weight-hero {
  display: grid; gap: 5px; padding: 16px;
  border: 1px solid var(--hr-line); border-radius: var(--hr-radius); background: linear-gradient(150deg, #fff7f6, var(--hr-rose-soft)); box-shadow: var(--hr-shadow);
}
.weight-eyebrow { color: var(--hr-ink-2); font-size: 14px; }
.weight-value { font: 44px/46px var(--hr-serif); font-variant-numeric: tabular-nums; color: var(--hr-ink); }
.weight-value text { font: 16px var(--hr-font); color: var(--hr-ink-2); }
.weight-value.empty { font: 650 22px/1.35 var(--hr-font); }
.weight-muted { color: var(--hr-ink-2); font-size: 13px; line-height: 1.6; }
.weight-actions { margin-top: 8px; }
.weight-secondary { justify-self: start; flex-shrink: 0; }
.weight-panel {
  display: grid; gap: 10px; padding: 16px; min-width: 0;
  border: 1px solid var(--hr-line); border-radius: var(--hr-radius); background: var(--hr-surface);
}
.weight-header { justify-content: space-between; flex-wrap: wrap; }
.weight-heading { font-weight: 680; font-size: 17px; }
.trend-panel { border-color: var(--hr-line-strong); box-shadow: var(--hr-shadow); }
.trend-panel h2,.trend-note { margin: 0; }
.trend-meta,.trend-meta-copy { display: flex; flex-wrap: wrap; align-items: center; gap: 4px 8px; }
.trend-meta { justify-content: space-between; }
.trend-meta-copy { flex: 1; }
.sample-badge { padding: 3px 7px; border-radius: 8px; background: var(--hr-plum-soft); color: var(--hr-plum); font-size: 12px; font-weight: 650; }
.trend-switch { padding-inline: 2px; font-size: 13px; }
.trend-loading { display: grid; place-items: center; min-height: 160px; }
.weight-stats,.compare-columns { display: grid; grid-auto-columns: minmax(0, 1fr); grid-auto-flow: column; gap: 8px; }
.weight-stats > view,.weight-stats > uni-view { background: var(--hr-paper); border-radius: 10px; padding: 8px 6px; text-align: center; }
.weight-stats strong,.weight-stats text,.weight-stats uni-text { display: block; }
.weight-stats text,.weight-stats uni-text { font-size: 12px; color: var(--hr-ink-2); }
.weight-stats strong { color: var(--hr-rose-deep); font: 20px var(--hr-serif); overflow-wrap: anywhere; }
.compare-columns > view,.compare-columns > uni-view { padding: 9px; border-radius: 10px; background: var(--hr-paper); font-size: 13px; }
.cycle-row { display: flex; gap: 4px; width: max-content; }
.cycle-day { min-width: 44px; min-height: 44px; padding: 7px 10px; }
.cycle-day.menstrual { background: var(--hr-rose-soft); }
.cycle-day.follicular { background: var(--hr-follicular); }
.cycle-day.ovulatory { background: var(--hr-peach); }
.cycle-day.luteal { background: var(--hr-plum-soft); }
.cycle-day.chosen { outline: 2px solid var(--hr-rose-deep); outline-offset: -2px; }
.weight-note,.weight-error { padding: 10px; border-radius: 11px; background: var(--hr-rose-soft); color: var(--hr-rose-deep); font-size: 13px; }
</style>
