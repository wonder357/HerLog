<template>
  <view class="trend-chart">
    <view v-if="!points.length" class="chart-empty">
      <strong>这段时间还没有记录</strong>
      <text>保存体重后，这里会显示每天最后一次测量。</text>
    </view>
    <template v-else>
      <svg viewBox="0 0 320 166" class="trend-svg" role="img" :aria-label="chartLabel">
        <rect v-for="band in bands" :key="band.day" :x="band.x" :y="top" :width="band.width" :height="bottom - top" :fill="band.fill" />
        <!-- 动态标签保留原生 SVG text，避免被 uni-app 编译成 uni-text。 -->
        <g v-for="tick in ticks" :key="tick.value">
          <component :is="'text'" x="0" :y="tick.y + 3" class="axis">{{ tick.label }}</component>
          <line :x1="left" :x2="right" :y1="tick.y" :y2="tick.y" class="grid-line" />
        </g>
        <path v-for="segment in segments" :key="'area-' + segment[0].day" :d="areaPath(segment)" class="trend-fill" />
        <polyline v-for="segment in segments" :key="segment[0].day" :points="segment.map(dot => dot.x + ',' + dot.y).join(' ')"
          class="trend-line" />
        <line v-if="activeDot" :x1="activeDot.x" :x2="activeDot.x" :y1="top" :y2="bottom" class="selection-line" />
        <circle v-for="dot in dots" :key="dot.day" :cx="dot.x" :cy="dot.y" :r="dot.day === activeDot?.day ? 4 : 2.4"
          class="trend-dot" :class="{ current: dot.day === activeDot?.day }" />
        <component :is="'text'" v-for="tick in dateTicks" :key="tick.day" :x="tick.x" y="151" class="axis date-axis" :text-anchor="tick.anchor">{{ tick.label }}</component>
        <component :is="'text'" x="0" y="151" class="axis">kg</component>
      </svg>
      <div v-if="activeDot" class="point-detail">
        <div class="point-copy" aria-live="polite">
          <span>{{ formatDayLabel(activeDot.day) }} · 当日测量</span>
          <strong>{{ activeDot.kg }} <small>kg</small></strong>
        </div>
        <div v-if="dots.length > 1" class="point-controls" role="group" aria-label="查看不同日期的测量值">
          <H5Button class="point-nav previous" aria-label="上一个记录日" :disabled="activeIndex === 0" @click="select(activeIndex - 1)" />
          <H5Button class="point-nav next" aria-label="下一个记录日" :disabled="activeIndex === dots.length - 1" @click="select(activeIndex + 1)" />
        </div>
      </div>
    </template>
  </view>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import H5Button from './H5Button'
import { addDays, diffDays, formatDayLabel } from '../shared/dates'
import type { CycleDay, Phase } from '../services/wellnessService'

interface Point { day: string; kg: number }
interface Dot extends Point { x: number; y: number }

const props = defineProps<{ points: Point[]; from?: string; to?: string; context?: CycleDay[] | null }>()
const left = 36
const right = 309
const top = 15
const bottom = 129

const colors: Record<Phase, string> = {
  menstrual: 'var(--hr-rose-soft)', follicular: 'var(--hr-follicular)',
  ovulatory: 'var(--hr-peach)', luteal: 'var(--hr-plum-soft)', unknown: 'transparent'
}
const rangeStart = computed(() => props.from ?? props.context?.[0]?.day ?? props.points[0]?.day)
const rangeEnd = computed(() => props.to ?? props.context?.at(-1)?.day ?? props.points.at(-1)?.day)
const span = computed(() => rangeStart.value && rangeEnd.value ? diffDays(rangeEnd.value, rangeStart.value) : 0)

function xAt(day: string): number {
  if (!span.value || !rangeStart.value) return (left + right) / 2
  return left + diffDays(day, rangeStart.value) * (right - left) / span.value
}

const bands = computed(() => (props.context ?? []).map(context => {
  const half = span.value ? (right - left) / (2 * span.value) : (right - left) / 2
  const center = xAt(context.day)
  const x = Math.max(left, center - half)
  return { day: context.day, x, width: Math.max(0, Math.min(right, center + half) - x), fill: colors[context.phase] }
}))

const bounds = computed(() => {
  const values = props.points.map(point => point.kg)
  if (!values.length) return { min: 0, step: 1 }
  const min = Math.min(...values)
  const max = Math.max(...values)
  const suggestedStep = Math.max(0.1, (max - min) / 3)
  const magnitude = 10 ** Math.floor(Math.log10(suggestedStep))
  const step = ([1, 2, 2.5, 5, 10].find(factor => factor * magnitude >= suggestedStep) ?? 10) * magnitude
  const padding = min === max ? step * 1.5 : 0
  return { min: Math.max(0, Math.floor((min - padding) / step) * step), step }
})

function yAt(kg: number): number {
  return bottom - (kg - bounds.value.min) * (bottom - top) / (bounds.value.step * 4)
}

const ticks = computed(() => Array.from({ length: 5 }, (_, index) => {
  const value = bounds.value.min + bounds.value.step * index
  return { value, label: String(Number(value.toFixed(2))), y: yAt(value) }
}))

const selectedDay = ref('')
const dots = computed<Dot[]>(() => props.points.map(point => ({ ...point, x: xAt(point.day), y: yAt(point.kg) })))
const activeIndex = computed(() => {
  const index = dots.value.findIndex(dot => dot.day === selectedDay.value)
  return index >= 0 ? index : dots.value.length - 1
})
const activeDot = computed(() => dots.value[activeIndex.value])

function select(index: number) {
  const dot = dots.value[index]
  if (dot) selectedDay.value = dot.day
}

const segments = computed(() => {
  const runs: Dot[][] = []
  for (const dot of dots.value) {
    const current = runs.at(-1)
    const previous = current?.at(-1)
    if (current && previous && diffDays(dot.day, previous.day) === 1) current.push(dot)
    else runs.push([dot])
  }
  return runs.filter(run => run.length >= 2)
})

function areaPath(segment: Dot[]) {
  const first = segment[0]
  const last = segment[segment.length - 1]
  return 'M' + first.x + ',' + bottom + ' L' + segment.map(dot => dot.x + ',' + dot.y).join(' L') +
    ' L' + last.x + ',' + bottom + ' Z'
}

function shortDay(day: string) {
  const [, month, date] = day.split('-')
  return Number(month) + '/' + Number(date)
}

const dateTicks = computed(() => {
  const first = rangeStart.value
  if (!first) return []
  if (!span.value) return [{ day: first, label: shortDay(first), x: xAt(first), anchor: 'middle' }]
  return [0, Math.round(span.value / 3), Math.round(span.value * 2 / 3), span.value].filter((offset, index, offsets) =>
    offsets.indexOf(offset) === index
  ).map(offset => {
    const day = addDays(first, offset)
    return { day, label: shortDay(day), x: xAt(day), anchor: !offset ? 'start' : offset === span.value ? 'end' : 'middle' }
  })
})

const chartLabel = computed(() => '体重趋势，' + props.points.length + ' 个记录日，单位千克')
</script>

<style scoped>
.trend-chart { min-width: 0; }
.trend-svg { display: block; width: 100%; height: auto; overflow: visible; }
.axis { fill: var(--hr-ink-2); font-size: 10px; font-family: var(--hr-font); }
.date-axis { font-variant-numeric: tabular-nums; }
.grid-line { stroke: var(--hr-line); stroke-width: 1; }
.trend-fill { fill: var(--hr-rose-soft); opacity: .65; }
.trend-line { fill: none; stroke: var(--hr-rose); stroke-width: 2; stroke-linejoin: round; stroke-linecap: round; }
.trend-dot { fill: var(--hr-surface); stroke: var(--hr-rose-deep); stroke-width: 1.15; }
.trend-dot.current { fill: var(--hr-rose-deep); stroke: var(--hr-surface); stroke-width: 1.7; }
.selection-line { stroke: var(--hr-line-strong); stroke-dasharray: 2 3; }
.point-detail { display:flex; justify-content:space-between; align-items:center; gap:8px; border:1px solid var(--hr-line); border-radius:12px; padding:5px 8px 5px 11px; }
.point-copy span { display:block; color:var(--hr-ink-2); font-size:12px; }
.point-copy strong { color:var(--hr-ink); font:650 21px/1.2 var(--hr-serif); font-variant-numeric:tabular-nums; }
.point-copy small { color:var(--hr-ink-2); font:12px var(--hr-font); }
.point-controls { display:flex; gap:6px; flex-shrink:0; }
.point-nav { display:grid; place-items:center; width:44px; height:44px; color:var(--hr-rose-deep); border:1px solid var(--hr-line); background:var(--hr-paper); border-radius:10px; padding:0; }
.point-nav:disabled { opacity:.45; }
.point-nav::before { content:''; width:7px; height:7px; border-right:1.5px solid currentColor; border-top:1.5px solid currentColor; transform:rotate(45deg); }
.point-nav.previous::before { transform:rotate(-135deg); }
.chart-empty { display:grid; gap:4px; place-items:center; min-height:160px; padding:12px; text-align:center; color:var(--hr-ink-2); font-size:13px; border:1px dashed var(--hr-line-strong); border-radius:12px; }
.chart-empty strong { color:var(--hr-ink); }
</style>
