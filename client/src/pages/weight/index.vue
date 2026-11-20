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
        <div class="analysis-switch" role="group" aria-label="体重分析视图">
          <H5Button class="analysis-option" :aria-pressed="analysis === 'trend'" @click="analysis = 'trend'">记录趋势</H5Button>
          <H5Button class="analysis-option" :aria-pressed="analysis === 'cycle'" @click="analysis = 'cycle'">周期对比</H5Button>
        </div>
        <div v-if="analysis === 'trend'" class="weight-hero">
          <div>
            <div class="weight-eyebrow">最近一次体重</div>
            <div v-if="summary?.latest_grams != null" class="weight-value">{{ formatKg(summary.latest_grams) }} <small>kg</small></div>
            <div v-else class="weight-value empty">{{ loading ? '正在读取…' : '开始记录体重' }}</div>
            <div v-if="summary?.latest_measured_at" class="weight-muted">{{ formatMoment(summary.latest_measured_at) }} 测量</div>
          </div>
          <div class="weight-actions">
            <H5Button class="primary" @click="formVisible = true">记体重</H5Button>
          </div>
        </div>
        <div class="metric-strip" role="group" aria-label="选择测量指标">
          <H5Button v-for="(item, key) in weightMetrics" :key="key" class="metric-tab"
            :aria-pressed="metric === key" @click="metric = key">
            <span>{{ item.label }}</span>
            <strong>{{ metricValues[key] === null ? '—' : measureValue(metricValues[key]!, key) }}</strong>
            <small>{{ metricValues[key] === null ? '暂无数据' : item.unit }}</small>
          </H5Button>
        </div>
        <view v-if="error" class="weight-error" role="alert">{{ error }} <H5Button @click="load">重试</H5Button></view>
        <CycleWeightComparison v-if="analysis === 'cycle'" :key="auth.token" :metric="metric"
          :has-height="summary?.metrics?.bmi?.status !== 'missing_height'" :refresh="cycleRefresh"
          @period="openPeriod" @profile="openProfile" />
        <template v-else>
        <section class="weight-panel trend-panel" aria-labelledby="weight-trend" :aria-busy="loading">
          <view class="weight-header">
            <h2 id="weight-trend" class="weight-heading">{{ metricInfo.label }}趋势</h2>
            <view class="weight-options" role="group" aria-label="趋势范围">
              <H5Button v-for="interval in intervals" :key="interval" class="weight-range" :class="{ chosen: days === interval }"
                :aria-pressed="days === interval" @click="setDays(interval)">近 {{ interval }} 天</H5Button>
            </view>
          </view>
          <view class="weight-muted">{{ formatDayLabel(trendStart) }} – {{ formatDayLabel(today) }}</view>
          <TrendChart v-if="summary" :key="metric" :title="metricInfo.label" :unit="metricInfo.unit"
            :points="trendPoints" :from="trendStart" :to="today" :empty-hint="metricNotes[metric]"
            :context="showCycle ? summary.cycle_context : undefined" />
          <view v-else-if="loading" class="trend-loading weight-muted" role="status">正在读取趋势…</view>
          <view v-if="summary && summary.days !== days" class="weight-muted" role="status">{{ loading ? '正在更新 · ' : '' }}当前显示近 {{ summary.days }} 天</view>
          <view class="weight-stats">
            <view v-if="metric === 'weight_kg'"><strong>{{ summary?.count ?? '—' }}</strong><text>记录次数</text></view>
            <view><strong>{{ summary ? trendPoints.length : '—' }}</strong><text>记录日</text></view>
            <view v-if="metricDelta !== null"><strong>{{ measureChange(metricDelta, metric) }}</strong><text>首尾变化</text></view>
          </view>
          <p class="weight-muted trend-note">{{ metricNotes[metric] }}</p>
          <p v-if="metric === 'body_fat_pct' && summary?.metrics?.body_fat_pct?.measured_at" class="weight-muted trend-note">
            最近测量 {{ formatMoment(summary.metrics.body_fat_pct.measured_at) }} · {{ summary.metrics.body_fat_pct.source === 'scale' ? '设备测量' : '手动填录' }}
          </p>
          <H5Button v-if="metric === 'bmi' && summary?.metrics?.bmi?.status === 'missing_height'"
            class="hr-action profile-link" @click="openProfile">去补充身高</H5Button>
          <H5Button v-if="metric === 'body_fat_pct' && summary?.metrics?.body_fat_pct?.status === 'no_data'"
            class="hr-action profile-link" @click="formVisible = true">添加体脂率记录</H5Button>
          <H5Button class="weight-secondary" @click="showCycle = !showCycle; load()">{{ showCycle ? '关闭周期背景' : '显示周期背景' }}</H5Button>
          <template v-if="showCycle && summary?.cycle_context">
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
            <view class="weight-heading">相邻时段体重对比</view>
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
      </template>
      <ExerciseSpace v-else-if="section === 'movement' && pageVisible && auth.token" :key="auth.token" @share="openShare" />
      <ExerciseDiscussion v-else-if="section === 'discussion' && pageVisible && auth.token" :key="auth.token" :reference="shareReference"
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
import CycleWeightComparison from './CycleWeightComparison.vue'
import ExerciseDiscussion from './ExerciseDiscussion.vue'
import ExerciseSpace from './ExerciseSpace.vue'
import { formatDayLabel, formatMoment, todayString } from '../../shared/dates'
import { formatKg, measureChange, measureValue, rangeStart, weightMetrics } from '../../shared/weight'
import type { WeightMetric } from '../../shared/weight'
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
const analysis = ref<'trend' | 'cycle'>('trend')
const metric = ref<WeightMetric>('weight_kg')
const metricNotes: Record<WeightMetric, string> = {
  weight_kg: '每天取最后一笔体重，缺测日期留空。',
  bmi: '按当前资料身高换算，BMI 不反映体脂和肌肉分布。',
  body_fat_pct: '每天取最后一笔有体脂率的测量，首尾差值用百分点表示。'
}
const cycleRefresh = ref(0)
const days = ref<7 | 30>(30)
const today = ref(todayString())
const summary = ref<WeightSummary | null>(null)
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
const trendStart = computed(() => rangeStart(summary.value?.days ?? days.value, today.value))
const selectedPhase = computed(() => summary.value?.cycle_context?.find(item => item.day === activeDay.value))
const metricInfo = computed(() => weightMetrics[metric.value])
const metricValues = computed<Record<WeightMetric, number | null>>(() => ({
  weight_kg: summary.value?.latest_kg ?? null,
  bmi: summary.value?.metrics?.bmi?.value ?? null,
  body_fat_pct: summary.value?.metrics?.body_fat_pct?.value ?? null
}))
const trendPoints = computed(() => {
  const data = summary.value
  const selected = metric.value
  if (!data) return []
  return selected === 'weight_kg' ? data.points.map(point => ({ day: point.day, value: point.kg }))
    : data.metric_trends?.[selected]?.points ?? []
})
const metricDelta = computed(() => (metric.value === 'weight_kg' ? summary.value?.delta_kg
  : summary.value?.metric_trends?.[metric.value]?.delta) ?? null)
watch(() => auth.token, () => {
  summaryVersion += 1
  comparisonVersion += 1
  summary.value = null
  loading.value = false
  comparison.value = null
  comparisonLoading.value = false
  shareReference.value = null
  formVisible.value = false
  section.value = 'overview'
  analysis.value = 'trend'
  metric.value = 'weight_kg'
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
function navigate(next: Section) {
  if (next !== 'discussion') shareReference.value = null
  section.value = next
}
function openShare(reference: ShareReference) {
  shareReference.value = reference
  section.value = 'discussion'
}
function openDetail() { uni.navigateTo({ url: '/pages/weight/detail' }) }
function openPeriod() { uni.switchTab({ url: '/pages/period/index' }) }
function openProfile() { uni.switchTab({ url: '/pages/me/index' }) }
function onSaved() {
  formVisible.value = false
  cycleRefresh.value += 1
  void load()
  if (comparing.value) void loadComparison()
}
onShow(() => {
  pageVisible.value = true
  if (auth.token) {
    cycleRefresh.value += 1
    void load()
  }
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
.analysis-switch { display: grid; grid-template-columns: 1fr 1fr; gap: 5px; padding: 3px; border: 1px solid var(--hr-line); border-radius: 14px; background: var(--hr-surface); }
.analysis-option { min-height: 44px; padding: 4px 6px; border: 0; border-radius: 10px; background: transparent; color: var(--hr-ink-2); font: 650 14px var(--hr-font); }
.analysis-option[aria-pressed='true'] { color: var(--hr-plum); background: var(--hr-plum-soft); }
.metric-strip { display: grid; grid-template-columns: repeat(3, minmax(0,1fr)); gap: 6px; }
.metric-tab { display: grid; justify-items: start; align-content: start; min-height: 77px; min-width: 0; padding: 7px 8px; text-align: left; border: 1px solid var(--hr-line); border-radius: 13px; background: var(--hr-surface); color: var(--hr-ink-2); font: 13px/1.25 var(--hr-font); }
.metric-tab strong { margin: 3px 0; font: 700 20px/1.1 var(--hr-serif, Georgia, serif); color: var(--hr-ink); }
.metric-tab small { font-size: 11px; }
.metric-tab[aria-pressed='true'] { border-color: var(--hr-rose); background: var(--hr-rose-soft); color: var(--hr-rose-deep); }
.metric-tab[aria-pressed='true'] strong { color: var(--hr-rose-deep); }
.weight-hero {
  display: grid; grid-template-columns: minmax(0, 1fr) auto; align-items: end; gap: 8px; padding: 14px 14px 12px;
  border: 1px solid var(--hr-line); border-radius: var(--hr-radius); background: linear-gradient(150deg, #fff7f6, var(--hr-rose-soft)); box-shadow: var(--hr-shadow);
}
.weight-eyebrow { color: var(--hr-ink-2); font-size: 14px; }
.weight-value { font: 44px/46px var(--hr-font); font-variant-numeric: tabular-nums; color: var(--hr-ink); }
.weight-value small { font: 15px var(--hr-font); color: var(--hr-ink-2); }
.weight-value.empty { font: 650 22px/1.35 var(--hr-font); }
.weight-muted { color: var(--hr-ink-2); font-size: 13px; line-height: 1.6; }
.weight-actions { margin-top: 8px; }
.weight-actions .primary { min-height: 44px; padding-inline: 11px; white-space: nowrap; font-size: 13px; }
.profile-link { justify-self: start; padding-inline: 0; }
.weight-secondary { justify-self: start; flex-shrink: 0; }
.weight-panel {
  display: grid; gap: 10px; padding: 16px; min-width: 0;
  border: 1px solid var(--hr-line); border-radius: var(--hr-radius); background: var(--hr-surface);
}
.weight-header { justify-content: space-between; flex-wrap: wrap; }
.weight-heading { font-weight: 680; font-size: 17px; }
.trend-panel { border-color: var(--hr-line-strong); box-shadow: var(--hr-shadow); }
.trend-panel h2,.trend-note { margin: 0; }
.trend-loading { display: grid; place-items: center; min-height: 160px; }
.weight-stats,.compare-columns { display: grid; grid-auto-columns: minmax(0, 1fr); grid-auto-flow: column; gap: 8px; }
.weight-stats > view,.weight-stats > uni-view { background: var(--hr-paper); border-radius: 10px; padding: 8px 6px; text-align: center; }
.weight-stats strong,.weight-stats text,.weight-stats uni-text { display: block; }
.weight-stats text,.weight-stats uni-text { font-size: 12px; color: var(--hr-ink-2); }
.weight-stats strong { color: var(--hr-rose-deep); font: 650 17px/1.35 var(--hr-font); overflow-wrap: anywhere; }
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
