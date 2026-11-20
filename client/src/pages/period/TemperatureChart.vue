<template>
  <div class="temperature-chart">
    <p class="muted chart-note">{{ fertilityNotice }}。只显示已录入的温度，缺测日期留空。</p>
    <p v-if="!points.length" class="muted">这段日期没有体温记录。</p>
    <template v-else>
      <svg viewBox="0 0 320 128" role="img" aria-label="已记录基础体温，单位摄氏度，完整数值在下方">
        <text x="0" y="12">°C</text>
        <g v-for="tick in ticks" :key="tick">
          <text x="0" :y="y(tick) + 3">{{ tick.toFixed(2) }}</text>
          <line x1="38" :y1="y(tick)" x2="307" :y2="y(tick)" class="gridline" />
        </g>
        <polyline v-for="segment in connectedLines" :key="segment[0].day"
          :points="segment.map(point => x(point.day) + ',' + y(point.celsius)).join(' ')" />
        <circle v-for="point in points" :key="point.day" :cx="x(point.day)" :cy="y(point.celsius)" r="3.7" />
        <text x="38" y="120">{{ shortDay(range.from) }}</text>
        <text x="307" y="120" text-anchor="end">{{ shortDay(range.to) }}</text>
      </svg>
      <details class="temperature-values">
        <summary>查看体温明细（{{ points.length }} 天）</summary>
        <ul>
          <li v-for="point in points" :key="point.day">
            <span>{{ point.day }}</span><strong>{{ point.celsius.toFixed(2) }} °C</strong>
          </li>
        </ul>
      </details>
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { diffDays } from '../../shared/dates'
import { fertilityNotice, temperatureSegments } from '../../shared/fertility'
import type { DateRange, FertilityDay } from '../../shared/fertility'

const props = defineProps<{ rows: FertilityDay[]; range: DateRange }>()
const lines = computed(() => temperatureSegments(props.rows))
const connectedLines = computed(() => lines.value.filter(segment => segment.length > 1))
const points = computed(() => lines.value.flat())
const bounds = computed(() => {
  const values = points.value.map(point => point.celsius)
  const min = Math.floor(Math.min(...values) * 10) / 10 - 0.1
  const max = Math.ceil(Math.max(...values) * 10) / 10 + 0.1
  return { min, max }
})
const ticks = computed(() => [bounds.value.max, (bounds.value.max + bounds.value.min) / 2, bounds.value.min])

const shortDay = (day: string) => day.slice(5).replace('-', '/')
function x(day: string): number {
  const span = diffDays(props.range.to, props.range.from)
  return span ? 41 + 263 * diffDays(day, props.range.from) / span : 172
}
function y(celsius: number): number {
  const { min, max } = bounds.value
  return 97 - 75 * (celsius - min) / (max - min)
}
</script>

<style scoped>
.chart-note { margin: 4px 0 8px; }
.temperature-chart svg { display: block; width: 100%; height: auto; margin-block: 6px; }
.temperature-chart svg text { fill: var(--hr-ink-2); font-size: 10px; font-family: var(--hr-font); }
.gridline { stroke: var(--hr-line-strong); stroke-width: 1; }
.temperature-chart polyline { stroke: var(--hr-rose); stroke-width: 2; fill: none; }
.temperature-chart circle { fill: var(--hr-rose-deep); }
.temperature-values summary { min-height: 44px; line-height: 1.5; padding-block: 10px; color: var(--hr-rose-deep); cursor: pointer; }
.temperature-values ul { list-style: none; margin: 0; padding: 0; }
.temperature-values li { display: flex; justify-content: space-between; flex-wrap: wrap; gap: 8px; padding: 7px 0; border-top: 1px solid var(--hr-line); font-size: 13px; }
</style>
