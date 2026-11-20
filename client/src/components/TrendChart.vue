<template>
  <view class="trend-chart">
    <view v-if="!selectedDays.length" class="chart-empty">
      <strong>这段范围还没有{{ title }}记录</strong>
      <text v-if="emptyHint">{{ emptyHint }}</text>
    </view>
    <template v-else>
      <svg viewBox="0 0 320 166" class="trend-svg" role="img" :aria-label="chartLabel" @click="selectFromPlot">
        <rect v-for="band in bands" :key="band.day" :x="band.x" :y="top" :width="band.width" :height="bottom - top" :fill="band.fill" />
        <!-- 动态标签保留原生 SVG text，避免被 uni-app 编译成 uni-text。 -->
        <g v-for="tick in ticks" :key="tick.value">
          <component :is="'text'" x="0" :y="tick.y + 3" class="axis">{{ tick.label }}</component>
          <line :x1="left" :x2="right" :y1="tick.y" :y2="tick.y" class="grid-line" />
        </g>
        <path v-for="segment in (relative ? [] : segments)" :key="'area-' + segment[0].day" :d="areaPath(segment)" class="trend-fill" />
        <polyline v-for="segment in segments" :key="'primary-' + segment[0].day" :points="segment.map(dot => dot.x + ',' + dot.y).join(' ')"
          class="trend-line" />
        <polyline v-for="segment in secondarySegments" :key="'secondary-' + segment[0].day"
          :points="segment.map(dot => dot.x + ',' + dot.y).join(' ')" class="trend-line secondary" />
        <line v-if="activeDay" :x1="xAt(activeDay)" :x2="xAt(activeDay)" :y1="top" :y2="bottom" class="selection-line" />
        <circle v-for="dot in secondaryDots" :key="'secondary-' + dot.day" :cx="dot.x" :cy="dot.y" :r="dot.day === activeDay ? 4 : 2.4"
          class="trend-dot secondary" :class="{ current: dot.day === activeDay }" />
        <circle v-for="dot in dots" :key="dot.day" :cx="dot.x" :cy="dot.y" :r="dot.day === activeDay ? 4 : 2.4"
          class="trend-dot" :class="{ current: dot.day === activeDay }" />
        <component :is="'text'" v-for="tick in dateTicks" :key="tick.day" :x="tick.x" y="151" class="axis date-axis" :text-anchor="tick.anchor">{{ tick.label }}</component>
        <component :is="'text'" x="0" y="151" class="axis">{{ unit }}</component>
      </svg>
      <div v-if="activeDay" class="point-detail">
        <div class="point-copy" aria-live="polite">
          <template v-if="relative && rangeStart">
            <span>周期第 {{ diffDays(activeDay, rangeStart) + 1 }} 天</span>
            <div class="point-dual">
              <span>当前 <strong>{{ activeDot?.value ?? '—' }}</strong><small v-if="activeDot"> {{ unit }}</small></span>
              <span>对照 <strong>{{ activeSecondary?.value ?? '—' }}</strong><small v-if="activeSecondary"> {{ unit }}</small></span>
            </div>
          </template>
          <template v-else-if="activeDot">
            <span>{{ formatDayLabel(activeDot.day) }} · 当日{{ title }}</span>
            <strong>{{ activeDot.value }} <small>{{ unit }}</small></strong>
          </template>
        </div>
        <div v-if="selectedDays.length > 1" class="point-controls" role="group" aria-label="查看不同日期的测量值">
          <H5Button class="point-nav previous" aria-label="上一个记录日" :disabled="activeIndex === 0" @click="select(activeIndex - 1)" />
          <H5Button class="point-nav next" aria-label="下一个记录日" :disabled="activeIndex === selectedDays.length - 1" @click="select(activeIndex + 1)" />
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

interface Point { day: string; value: number }
interface Dot extends Point { x: number; y: number }

const props = defineProps<{
  title: string; unit: string; points: Point[]; from?: string; to?: string; context?: CycleDay[] | null
  secondaryPoints?: Point[]; relative?: boolean; emptyHint?: string
}>()
const left = 45
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
  const values = [...props.points, ...(props.secondaryPoints ?? [])].map(point => point.value)
  if (!values.length) return { min: 0, step: 1 }
  const min = Math.min(...values)
  const max = Math.max(...values)
  const suggestedStep = Math.max(0.1, (max - min) / 3)
  const magnitude = 10 ** Math.floor(Math.log10(suggestedStep))
  const step = ([1, 2, 2.5, 5, 10].find(factor => factor * magnitude >= suggestedStep) ?? 10) * magnitude
  const padding = min === max ? step * 1.5 : 0
  return { min: Math.max(0, Math.floor((min - padding) / step) * step), step }
})

function yAt(value: number): number {
  return bottom - (value - bounds.value.min) * (bottom - top) / (bounds.value.step * 4)
}

const ticks = computed(() => Array.from({ length: 5 }, (_, index) => {
  const value = bounds.value.min + bounds.value.step * index
  return { value, label: String(Number(value.toFixed(2))), y: yAt(value) }
}))

const selectedDay = ref('')
function toDots(points: Point[]): Dot[] {
  return points.map(point => ({ ...point, x: xAt(point.day), y: yAt(point.value) }))
}
const dots = computed(() => toDots(props.points))
const secondaryDots = computed(() => toDots(props.secondaryPoints ?? []))
const selectedDays = computed(() => [...new Set([...dots.value, ...secondaryDots.value].map(dot => dot.day))].sort())
const activeIndex = computed(() => {
  const index = selectedDays.value.indexOf(selectedDay.value)
  return index >= 0 ? index : selectedDays.value.length - 1
})
const activeDay = computed(() => selectedDays.value[activeIndex.value])
const activeDot = computed(() => dots.value.find(dot => dot.day === activeDay.value))
const activeSecondary = computed(() => secondaryDots.value.find(dot => dot.day === activeDay.value))

function select(index: number) {
  const day = selectedDays.value[index]
  if (day) selectedDay.value = day
}

function selectFromPlot(event: MouseEvent) {
  const box = (event.currentTarget as SVGSVGElement).getBoundingClientRect()
  const x = (event.clientX - box.left) * 320 / box.width
  let distance = Infinity
  for (const day of selectedDays.value) {
    const nextDistance = Math.abs(xAt(day) - x)
    if (nextDistance >= distance) continue
    distance = nextDistance
    selectedDay.value = day
  }
}

function connectedSegments(series: Dot[]) {
  const runs: Dot[][] = []
  for (const dot of series) {
    const current = runs.at(-1)
    const previous = current?.at(-1)
    if (current && previous && diffDays(dot.day, previous.day) === 1) current.push(dot)
    else runs.push([dot])
  }
  return runs.filter(run => run.length >= 2)
}
const segments = computed(() => connectedSegments(dots.value))
const secondarySegments = computed(() => connectedSegments(secondaryDots.value))

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
  if (!span.value) return [{ day: first, label: props.relative ? '第1天' : shortDay(first), x: xAt(first), anchor: 'middle' }]
  return [0, Math.round(span.value / 3), Math.round(span.value * 2 / 3), span.value].filter((offset, index, offsets) =>
    offsets.indexOf(offset) === index
  ).map(offset => {
    const day = addDays(first, offset)
    return { day, label: props.relative ? '第' + (offset + 1) + '天' : shortDay(day), x: xAt(day), anchor: !offset ? 'start' : offset === span.value ? 'end' : 'middle' }
  })
})

const chartLabel = computed(() => props.relative
  ? props.title + '周期对比，当前 ' + props.points.length + ' 个记录日，对照 ' + secondaryDots.value.length + ' 个记录日'
  : props.title + '趋势，' + props.points.length + ' 个记录日，单位 ' + props.unit)
</script>

<style scoped>
.trend-chart { min-width: 0; }
.trend-svg { display: block; width: 100%; height: auto; overflow: visible; }
.axis { fill: var(--hr-ink-2); font-size: 10px; font-family: var(--hr-font); }
.date-axis { font-variant-numeric: tabular-nums; }
.grid-line { stroke: var(--hr-line); stroke-width: 1; }
.trend-fill { fill: var(--hr-rose-soft); opacity: .65; }
.trend-line { fill: none; stroke: var(--hr-rose); stroke-width: 2; stroke-linejoin: round; stroke-linecap: round; }
.trend-line.secondary { stroke: var(--hr-plum); stroke-dasharray: 5 4; }
.trend-dot { fill: var(--hr-surface); stroke: var(--hr-rose-deep); stroke-width: 1.15; }
.trend-dot.current { fill: var(--hr-rose-deep); stroke: var(--hr-surface); stroke-width: 1.7; }
.trend-dot.secondary { stroke: var(--hr-plum); }
.trend-dot.secondary.current { fill: var(--hr-plum); stroke: var(--hr-surface); }
.selection-line { stroke: var(--hr-line-strong); stroke-dasharray: 2 3; }
.point-detail { display:flex; justify-content:space-between; align-items:center; gap:8px; border:1px solid var(--hr-line); border-radius:12px; padding:5px 8px 5px 11px; }
.point-copy span { display:block; color:var(--hr-ink-2); font-size:12px; }
.point-copy strong { color:var(--hr-ink); font:650 21px/1.2 var(--hr-font); font-variant-numeric:tabular-nums; }
.point-copy small { color:var(--hr-ink-2); font:12px var(--hr-font); }
.point-dual { display:flex; flex-wrap:wrap; gap:0 8px; }
.point-dual strong { font-size:14px; }
.point-controls { display:flex; gap:6px; flex-shrink:0; }
.point-nav { display:grid; place-items:center; width:44px; height:44px; color:var(--hr-rose-deep); border:1px solid var(--hr-line); background:var(--hr-paper); border-radius:10px; padding:0; }
.point-nav:disabled { opacity:.45; }
.point-nav::before { content:''; width:7px; height:7px; border-right:1.5px solid currentColor; border-top:1.5px solid currentColor; transform:rotate(45deg); }
.point-nav.previous::before { transform:rotate(-135deg); }
.chart-empty { display:grid; gap:4px; place-items:center; min-height:160px; padding:12px; text-align:center; color:var(--hr-ink-2); font-size:13px; border:1px dashed var(--hr-line-strong); border-radius:12px; }
.chart-empty strong { color:var(--hr-ink); }
</style>
