<template>
  <view class="hr-page hr-tab-page weight-page">
    <HerlogHeading title="体重" />
    <view class="weight-shell">
      <view class="weight-tabs">
        <H5Button v-for="item in tabs" :key="item.code" :class="{ chosen: section === item.code }"
          :aria-pressed="section === item.code" @click="navigate(item.code)">{{ item.label }}</H5Button>
      </view>
      <template v-if="section === 'overview'">
        <view class="weight-hero">
          <view class="weight-eyebrow">最近一次测量</view>
          <view v-if="summary?.latest_grams != null" class="weight-value">{{ formatKg(summary.latest_grams) }} <text>kg</text></view>
          <view v-else class="weight-value empty">{{ loading ? '正在读取…' : '开始记录体重' }}</view>
          <view class="weight-muted">{{ summary?.latest_measured_at ? formatMoment(summary.latest_measured_at) + ' 测量' : '留下你愿意记录的数据。' }}</view>
          <view class="weight-actions">
            <H5Button class="primary weight-primary" @click="formVisible = true">记体重</H5Button>
            <H5Button class="weight-secondary" @click="openDetail">记录明细</H5Button>
          </view>
        </view>
        <view v-if="error" class="weight-error" role="alert">{{ error }} <H5Button @click="load">重试</H5Button></view>
        <view class="weight-panel">
          <view class="weight-header">
            <view class="weight-heading">体重趋势</view>
            <view class="weight-options">
              <H5Button v-for="interval in intervals" :key="interval" :class="{ chosen: days === interval }" @click="setDays(interval)">近 {{ interval }} 天</H5Button>
            </view>
          </view>
          <TrendChart v-if="!loading || summary" :points="chartPoints" :context="summary?.cycle_context" />
          <view v-else class="weight-muted">正在读取趋势…</view>
          <view class="weight-stats">
            <view><strong>{{ summary?.count ?? '—' }}</strong><text>记录次数</text></view>
            <view><strong>{{ summary?.record_days ?? summary?.points.length ?? '—' }}</strong><text>记录日</text></view>
            <view v-if="summary?.delta_grams != null"><strong>{{ formatDelta(summary.delta_grams) }}</strong><text>首尾变化</text></view>
          </view>
          <view v-if="summary?.points.length === 1" class="weight-muted">再记录一个不同日期，就可以查看首尾变化。</view>
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
        </view>
        <view class="weight-panel">
          <view class="weight-header">
            <view class="weight-heading">相邻时段对比</view>
            <H5Button class="weight-secondary" @click="toggleCompare">{{ comparing ? '收起' : '看对比' }}</H5Button>
          </view>
          <template v-if="comparing">
            <view v-if="compareError" class="weight-error" role="alert">{{ compareError }} <H5Button @click="loadComparison">重试</H5Button></view>
            <view v-else-if="!comparison" class="weight-muted">正在读取对比…</view>
            <template v-else>
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
        <view class="weight-panel">
          <view class="weight-heading">照顾自己的节奏</view>
          <view class="weight-muted">按当天感受选择活动或休息。也可以记下日常饮食和作息，回看时多一些背景。</view>
          <H5Button class="weight-secondary" @click="navigate('movement')">去运动专区</H5Button>
        </view>
      </template>
      <ExerciseSpace v-else-if="section === 'movement'" @share="openShare" />
      <WellnessGroup v-else topic="exercise" :reference="shareReference" @published="shareReference = null" />
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
import WellnessGroup from '../../components/WellnessGroup.vue'
import ExerciseSpace from './ExerciseSpace.vue'
import { formatDayLabel, formatMoment } from '../../shared/dates'
import { formatDelta, formatKg } from '../../shared/weight'
import { currentEpoch } from '../../services/httpClient'
import { getComparison, getSummary } from '../../services/weightService'
import type { WeightSummary } from '../../services/types'
import { phaseNames } from '../../services/wellnessService'
import type { ShareReference } from '../../services/wellnessService'
import { useAuthStore } from '../../stores/auth'

const tabs = [{ code: 'overview', label: '体重记录' }, { code: 'movement', label: '运动专区' }, { code: 'group', label: '运动分享' }] as const
const intervals = [7, 30] as const
type Section = typeof tabs[number]['code']
const section = ref<Section>('overview')
const days = ref<7 | 30>(30)
const summary = ref<WeightSummary | null>(null)
const comparison = ref<Awaited<ReturnType<typeof getComparison>> | null>(null)
const showCycle = ref(false)
const activeDay = ref('')
const comparing = ref(false)
const loading = ref(false)
const error = ref('')
const compareError = ref('')
const formVisible = ref(false)
const shareReference = ref<ShareReference | null>(null)
const auth = useAuthStore()
let summaryVersion = 0
let comparisonVersion = 0
const chartPoints = computed(() => (summary.value?.points ?? []).map(point => ({ day: point.day, kg: point.kg })))
const selectedPhase = computed(() => summary.value?.cycle_context?.find(item => item.day === activeDay.value))
watch(() => auth.token, () => {
  summaryVersion += 1
  comparisonVersion += 1
  summary.value = null
  comparison.value = null
  shareReference.value = null
  formVisible.value = false
  section.value = 'overview'
  if (auth.token) void load()
})
async function load() {
  const version = ++summaryVersion
  const epoch = currentEpoch()
  error.value = ''
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
  comparison.value = null
  compareError.value = ''
  try {
    const data = await getComparison(days.value)
    if (version === comparisonVersion && epoch === currentEpoch()) comparison.value = data
  } catch {
    if (version === comparisonVersion && epoch === currentEpoch()) compareError.value = '对比没有加载成功'
  }
}
function toggleCompare() {
  comparing.value = !comparing.value
  if (comparing.value) void loadComparison()
}
function setDays(interval: 7 | 30) {
  if (days.value === interval) return
  days.value = interval
  summary.value = null
  void load()
  if (comparing.value) void loadComparison()
}
function navigate(next: Section) {
  if (next !== 'group') shareReference.value = null
  section.value = next
}
function openShare(reference: ShareReference) {
  shareReference.value = reference
  section.value = 'group'
}
function openDetail() { uni.navigateTo({ url: '/pages/weight/detail' }) }
function onSaved() {
  formVisible.value = false
  void load()
  if (comparing.value) void loadComparison()
}
onShow(() => { if (auth.token) void load() })
onHide(() => { formVisible.value = false })
</script>

<style scoped>
.weight-shell { display: grid; gap: 12px; }
.weight-tabs,.weight-actions,.weight-options,.weight-header { display: flex; align-items: center; gap: 8px; }
.weight-tabs { padding: 4px; border: 1px solid var(--hr-line); background: var(--hr-surface); border-radius: 15px; }
.weight-tabs button,.weight-options button,.cycle-day,.weight-secondary,.weight-error button {
  border: 1px solid transparent; border-radius: 999px; padding: 7px 10px; min-height: 44px;
  font-size: 13px; line-height: 1.4; background: var(--hr-paper-deep); color: var(--hr-rose-deep);
}
.weight-tabs button { flex: 1; min-width: 0; background: transparent; color: var(--hr-ink-2); }
.weight-tabs button.chosen,.weight-options button.chosen { background: var(--hr-rose-soft); color: var(--hr-rose-deep); font-weight: 700; }
.weight-options { flex-shrink: 0; gap: 3px; }
.weight-options button { padding-inline: 7px; }
.weight-hero {
  display: grid; gap: 5px; padding: clamp(15px, 4vw, 24px);
  border: 1px solid var(--hr-line); border-radius: var(--hr-radius-lg); background: var(--hr-surface); box-shadow: var(--hr-shadow);
}
.weight-eyebrow { color: var(--hr-ink-2); font-size: 14px; }
.weight-value { font: 48px/1.1 var(--hr-serif); font-variant-numeric: tabular-nums; color: var(--hr-rose-deep); }
.weight-value text { font: 16px var(--hr-font); color: var(--hr-ink-2); }
.weight-value.empty { font: 650 22px/1.35 var(--hr-font); }
.weight-muted { color: var(--hr-ink-2); font-size: 13px; line-height: 1.6; }
.weight-actions { margin-top: 8px; }
.weight-primary { flex: 1; }
.weight-secondary { justify-self: start; flex-shrink: 0; }
.weight-panel {
  display: grid; gap: 10px; padding: 14px; min-width: 0;
  border: 1px solid var(--hr-line); border-radius: var(--hr-radius); background: var(--hr-surface);
}
.weight-header { justify-content: space-between; flex-wrap: wrap; }
.weight-heading { font-weight: 680; font-size: 17px; }
.weight-stats,.compare-columns { display: grid; grid-auto-columns: minmax(0, 1fr); grid-auto-flow: column; gap: 8px; }
.weight-stats > view,.weight-stats > uni-view { background: var(--hr-paper); border-radius: 10px; padding: 8px 6px; text-align: center; }
.weight-stats strong,.weight-stats text,.weight-stats uni-text { display: block; }
.weight-stats text,.weight-stats uni-text { font-size: 12px; color: var(--hr-ink-2); }
.weight-stats strong { color: var(--hr-rose-deep); font: 20px var(--hr-serif); overflow-wrap: anywhere; }
.compare-columns > view,.compare-columns > uni-view { padding: 9px; border-radius: 10px; background: var(--hr-paper); font-size: 13px; }
.cycle-row { display: flex; gap: 4px; width: max-content; }
.cycle-day { min-width: 44px; min-height: 44px; padding: 7px 10px; }
.cycle-day.menstrual { background: var(--hr-rose-soft); }
.cycle-day.follicular { background: var(--hr-sage-soft); }
.cycle-day.ovulatory { background: var(--hr-peach); }
.cycle-day.luteal { background: var(--hr-plum-soft); }
.cycle-day.chosen { outline: 2px solid var(--hr-rose-deep); outline-offset: -2px; }
.weight-note,.weight-error { padding: 10px; border-radius: 11px; background: var(--hr-rose-soft); color: var(--hr-rose-deep); font-size: 13px; }
</style>
