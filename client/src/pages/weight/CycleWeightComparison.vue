<template>
  <section class="cycle-card" aria-labelledby="weight-cycle-title" :aria-busy="loading">
    <header class="cycle-intro">
      <h2 id="weight-cycle-title">同周期日对比</h2>
      <p>按两次经期的实际开始日对齐测量。</p>
    </header>
    <p v-if="loading && !comparison" class="muted" role="status">正在整理周期记录…</p>
    <div v-else-if="error" class="retry" role="alert">
      <span>{{ error }}</span><H5Button class="hr-action" @click="load(selection)">重试</H5Button>
      <H5Button v-if="selection" class="hr-action" @click="load()">查看最近两次</H5Button>
    </div>
    <div v-else-if="comparison && (!comparison.current || !comparison.previous)" class="cycle-empty">
      <strong>再记录{{ comparison.cycles.length ? '一次' : '两次' }}经期开始日</strong>
      <p>有两个实际开始日后，就可以对齐体重和体成分记录。</p>
      <H5Button class="ghost" @click="emit('period')">去经期页</H5Button>
    </div>
    <template v-if="comparison?.current && comparison.previous && !error">
      <div class="cycle-picker">
        <div>
          <H5Label class="hr-field-label" for="weight-cycle-current">当前周期</H5Label>
          <component :is="'select'" id="weight-cycle-current" class="field" :value="currentStart" :disabled="loading"
            @change="chooseCurrent(($event.target as HTMLSelectElement).value)">
            <option v-for="cycle in comparison.cycles.slice(0, -1)" :key="cycle.start_day" :value="cycle.start_day">
              {{ cycleLabel(cycle.start_day) }}
            </option>
          </component>
        </div>
        <div>
          <H5Label class="hr-field-label" for="weight-cycle-previous">对照周期</H5Label>
          <component :is="'select'" id="weight-cycle-previous" class="field" :value="previousStart" :disabled="loading"
            @change="choosePrevious(($event.target as HTMLSelectElement).value)">
            <option v-for="cycle in previousOptions" :key="cycle.start_day" :value="cycle.start_day">
              {{ cycleLabel(cycle.start_day) }}
            </option>
          </component>
        </div>
      </div>
      <p v-if="loading" class="muted" role="status">正在对齐所选周期…</p>
      <template v-else>
        <div class="phase-chips" role="group" aria-label="对比阶段">
          <H5Button v-for="(label, value) in phases" :key="value" class="phase-chip"
            :aria-pressed="phase === value" @click="phase = value">{{ label }}</H5Button>
        </div>
        <div class="paired-result" aria-live="polite">
          <div class="paired-head">
            <span>{{ phase === 'all' ? '同周期日均值差' : phases[phase] + ' · 同周期日均值差' }}</span>
            <span>{{ result.pairs.length }} 个配对日</span>
          </div>
          <strong v-if="displayAverages" class="difference">
            {{ measureChange(displayAverages.current - displayAverages.previous, metric) }}
          </strong>
          <strong v-else>配对记录不足</strong>
          <p v-if="displayAverages" class="muted">
            当前均值 {{ measureValue(displayAverages.current, metric) }}{{ metricInfo.unit === '%' ? '%' : ' ' + metricInfo.unit }}，
            对照均值 {{ measureValue(displayAverages.previous, metric) }}{{ metricInfo.unit === '%' ? '%' : ' ' + metricInfo.unit }}
          </p>
          <p v-else class="muted">至少两个周期日都有{{ metricInfo.label }}测量时，才显示均值差。</p>
          <p class="muted">对齐前 {{ comparison.aligned_days }} 天 · 当前记 {{ result.currentPoints.length }} 天 · 对照记 {{ result.previousPoints.length }} 天</p>
        </div>
        <div class="cycle-legend">
          <span><i />{{ formatDayLabel(currentStart) }}开始</span>
          <span><i class="dashed" />{{ formatDayLabel(previousStart) }}开始</span>
        </div>
        <TrendChart :key="metric + phase + currentStart + previousStart" :title="metricInfo.label"
          :unit="metricInfo.unit" :points="chartCurrent" :secondary-points="chartPrevious"
          :from="currentStart" :to="through" relative />
        <H5Button v-if="metric === 'bmi' && !hasHeight" class="hr-action" @click="emit('profile')">去补充身高</H5Button>
        <p class="muted compare-note">经期以已记录日期为准，其余阶段按日期估算。缺测留空，周期对齐只用于回顾变化。</p>
        <details v-if="result.pairs.length" class="paired-days">
          <summary>查看配对日期</summary>
          <table>
            <thead><tr><th scope="col">周期日</th><th scope="col">当前</th><th scope="col">对照</th></tr></thead>
            <tbody>
              <tr v-for="pair in result.pairs" :key="pair.current.cycle_day">
                <th scope="row">第 {{ pair.current.cycle_day }} 天</th>
                <td><span>{{ formatDayLabel(pair.current.day) }}</span>{{ measureValue(pair.current[metric]!, metric) }} {{ metricInfo.unit }}</td>
                <td><span>{{ formatDayLabel(pair.previous.day) }}</span>{{ measureValue(pair.previous[metric]!, metric) }} {{ metricInfo.unit }}</td>
              </tr>
            </tbody>
          </table>
        </details>
      </template>
    </template>
  </section>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import H5Button from '../../components/H5Button'
import { H5Label } from '../../components/H5Form'
import TrendChart from '../../components/TrendChart.vue'
import { currentEpoch } from '../../services/httpClient'
import { getCycleComparison } from '../../services/weightService'
import type { WeightCycleComparison, WeightCyclePoint } from '../../services/weightService'
import { addDays, formatDayLabel } from '../../shared/dates'
import { measureChange, measureValue, pairCycleMeasurements, weightMetrics } from '../../shared/weight'
import type { WeightMetric } from '../../shared/weight'

const props = defineProps<{ metric: WeightMetric; hasHeight: boolean; refresh: number }>()
const emit = defineEmits<{ period: []; profile: [] }>()
const phases = {
  all: '全部', menstrual: '经期', follicular: '卵泡期', ovulatory: '排卵估算', luteal: '黄体期'
} as const
const comparison = ref<WeightCycleComparison | null>(null)
const error = ref('')
const loading = ref(false)
const selection = ref<{ current_start: string; previous_start: string }>()
const phase = ref<keyof typeof phases>('all')
let version = 0
onBeforeUnmount(() => { version += 1 })
const metricInfo = computed(() => weightMetrics[props.metric])
const currentStart = computed(() => comparison.value?.current?.cycle.start_day ?? '')
const previousStart = computed(() => comparison.value?.previous?.cycle.start_day ?? '')
const previousOptions = computed(() => comparison.value?.cycles.filter(cycle => cycle.start_day < currentStart.value) ?? [])
const result = computed(() => pairCycleMeasurements(
  comparison.value?.current?.points ?? [], comparison.value?.previous?.points ?? [], props.metric, phase.value
))
const displayAverages = computed(() => {
  const averages = result.value.averages
  if (!averages) return null
  const digits = metricInfo.value.digits
  return { current: Number(averages.current.toFixed(digits)), previous: Number(averages.previous.toFixed(digits)) }
})
const through = computed(() => currentStart.value
  ? addDays(currentStart.value, (comparison.value?.aligned_days ?? 1) - 1) : undefined)
const chartPoints = (points: WeightCyclePoint[]) => points.map(point => ({
  day: addDays(currentStart.value, point.cycle_day - 1), value: point[props.metric]!
}))
const chartCurrent = computed(() => chartPoints(result.value.currentPoints))
const chartPrevious = computed(() => chartPoints(result.value.previousPoints))

function cycleLabel(day: string) {
  return day.slice(0, 4) + ' 年 ' + formatDayLabel(day)
}

function chooseCurrent(day: string) {
  const older = comparison.value?.cycles.find(cycle => cycle.start_day < day)
  if (!older) return
  void load({ current_start: day, previous_start: previousStart.value < day ? previousStart.value : older.start_day })
}

function choosePrevious(day: string) {
  void load({ current_start: currentStart.value, previous_start: day })
}

async function load(pair?: typeof selection.value) {
  const request = ++version
  const epoch = currentEpoch()
  const active = () => request === version && epoch === currentEpoch()
  selection.value = pair
  error.value = ''
  loading.value = true
  try {
    const data = await getCycleComparison(pair)
    if (active()) comparison.value = data
  } catch {
    if (active()) error.value = '暂时无法读取周期对比。'
  } finally {
    if (active()) loading.value = false
  }
}

watch(() => props.refresh, () => { void load(selection.value) }, { immediate: true })
</script>

<style scoped>
.cycle-card { padding: 14px; border: 1px solid var(--hr-line-strong); border-radius: var(--hr-radius); background: var(--hr-surface); box-shadow: var(--hr-shadow); min-width: 0; }
.cycle-intro h2 { margin: 0 0 4px; font: 700 19px/1.3 var(--hr-font); }
.cycle-intro p, .muted, .cycle-empty p { margin: 4px 0; color: var(--hr-ink-2); font-size: 13px; line-height: 1.55; }
.cycle-picker { display: grid; grid-template-columns: repeat(2, minmax(0,1fr)); gap: 7px; margin: 8px 0 0; }
.cycle-picker .field { font-size: 13px; padding-inline: 6px; margin-bottom: 6px; }
.phase-chips { display: flex; flex-wrap: wrap; gap: 5px; margin: 5px 0 11px; }
.phase-chip { min-height: 44px; padding: 5px 8px; border: 1px solid var(--hr-line-strong); border-radius: 10px; background: var(--hr-paper); color: var(--hr-ink-2); font: 13px var(--hr-font); }
.phase-chip[aria-pressed='true'] { color: var(--hr-plum); background: var(--hr-plum-soft); border-color: var(--hr-plum); font-weight: 650; }
.paired-result { padding: 10px 12px; margin: 0 0 10px; border-radius: 12px; background: var(--hr-plum-soft); color: var(--hr-plum); }
.paired-head { display: flex; justify-content: space-between; flex-wrap: wrap; gap: 3px 8px; font-size: 12px; }
.paired-result strong { display: block; margin: 5px 0; }
.difference { font: 680 24px/1.2 var(--hr-serif, Georgia, serif); }
.cycle-legend { display: flex; flex-wrap: wrap; gap: 4px 12px; color: var(--hr-ink-2); font-size: 12px; margin: 0 0 4px; }
.cycle-legend span { display: inline-flex; gap: 5px; align-items: center; }
.cycle-legend i { width: 14px; border-block-start: 2px solid var(--hr-rose); }
.cycle-legend .dashed { border-block-start: 2px dashed var(--hr-plum); }
.compare-note { margin-top: 9px; }
.cycle-empty { padding: 12px; margin-top: 10px; border: 1px dashed var(--hr-line-strong); border-radius: 12px; }
.cycle-empty .ghost { margin-top: 7px; }
.paired-days { margin-top: 5px; border-top: 1px solid var(--hr-line); }
.paired-days summary { cursor: pointer; min-height: 44px; padding: 10px 0 6px; color: var(--hr-plum); font-size: 13px; }
.paired-days table { width: 100%; border-collapse: collapse; text-align: left; font-size: 12px; }
.paired-days th, .paired-days td { padding: 6px 2px; border-top: 1px solid var(--hr-line); }
.paired-days td span { display: block; color: var(--hr-ink-2); }
.retry { display: flex; flex-wrap: wrap; align-items: center; gap: 6px; font-size: 13px; }
</style>
