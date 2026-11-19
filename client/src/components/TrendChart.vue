<template>
  <view class="chart">
    <view v-if="points.length === 0" class="empty">这段时间还没有记录</view>
    <svg v-else viewBox="0 0 320 140" class="svg" role="img" :aria-label="chartLabel">
      <rect v-for="band in bands" :key="band.day" :x="band.x" y="15" :width="band.width" height="98" :fill="band.fill" />
      <line v-for="line in gridLines" :key="line" :x1="24" :x2="308" :y1="line" :y2="line" stroke="var(--hr-line)" stroke-width="1" />
      <polyline v-for="(segment, index) in segments" :key="index" :points="segment" fill="none" stroke="var(--hr-rose)" stroke-width="2" stroke-linejoin="round" />
      <circle v-for="dot in dots" :key="dot.key" :cx="dot.x" :cy="dot.y" r="3.2" fill="var(--hr-rose-deep)" />
      <text x="24" y="132" class="axis">{{ firstLabel }}</text>
      <text x="308" y="132" class="axis" text-anchor="end">{{ lastLabel }}</text>
    </svg>
    <view class="note">每天取最后一次测量，缺测日留空。</view>
  </view>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { diffDays } from '../shared/dates'
import type { CycleDay, Phase } from '../services/wellnessService'

interface Point {
  day: string
  kg: number
}

const props = defineProps<{ points: Point[]; context?: CycleDay[] | null }>()

const colors: Record<Phase, string> = {
  menstrual: '#f7dbe4', follicular: '#e9eddf', ovulatory: '#faebd9', luteal: '#ece2f2', unknown: 'transparent',
}
const rangeStart = computed(() => props.context?.[0]?.day ?? props.points[0]?.day)
const rangeEnd = computed(() => props.context?.at(-1)?.day ?? props.points.at(-1)?.day)
const span = computed(() => rangeStart.value && rangeEnd.value ? diffDays(rangeEnd.value, rangeStart.value) : 0)
function xAt(day: string): number {
  return span.value && rangeStart.value ? 24 + diffDays(day, rangeStart.value) * 284 / span.value : 166
}
const bands = computed(() => (props.context ?? []).map(context => {
  const half = span.value ? 142 / span.value : 142
  const center = xAt(context.day)
  const x = Math.max(24, center - half)
  return { day: context.day, x, width: Math.min(308, center + half) - x, fill: colors[context.phase] }
}))

const gridLines = [20, 60, 100]

const bounds = computed(() => {
  const values = props.points.map((point) => point.kg)
  const min = Math.min(...values)
  const max = Math.max(...values)
  return { min, max, span: max - min || 1 }
})

const dots = computed(() =>
  props.points.map((point, index) => ({
    key: `${point.day}-${index}`,
    x: xAt(point.day),
    y: 110 - ((point.kg - bounds.value.min) / bounds.value.span) * 90
  }))
)

const segments = computed(() => {
  const lines: string[][] = []
  dots.value.forEach((dot, index) => {
    if (!index || diffDays(props.points[index].day, props.points[index - 1].day) > 1) lines.push([])
    lines[lines.length - 1].push(`${dot.x},${dot.y}`)
  })
  return lines.map(line => line.join(' '))
})

function shortDay(day: string): string {
  const [, month, date] = day.split('-')
  return `${Number(month)}/${Number(date)}`
}

const firstLabel = computed(() => rangeStart.value ? shortDay(rangeStart.value) : '')
const lastLabel = computed(() => rangeEnd.value && rangeEnd.value !== rangeStart.value ? shortDay(rangeEnd.value) : '')
const chartLabel = computed(() =>
  '体重趋势。' + props.points.map(point => shortDay(point.day) + '，' + point.kg + ' 千克').join('。')
)
</script>

<style scoped>
.chart {
  background: var(--hr-surface);
  border-radius: 14px;
  padding: 6px 0;
}
.svg {
  width: 100%;
  height: 150px;
}
.axis {
  font-size: 10px;
  fill: var(--hr-ink-2);
}
.note {
  font-size: 12px;
  color: var(--hr-ink-2);
  margin-top: 6px;
}
.empty {
  padding: 36px 0;
  text-align: center;
  color: var(--hr-ink-2);
  font-size: 13px;
}
</style>
