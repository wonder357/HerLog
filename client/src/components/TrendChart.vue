<template>
  <view class="chart">
    <view v-if="points.length === 0" class="empty">这段时间还没有记录</view>
    <view v-else class="body">
      <svg viewBox="0 0 320 150" class="svg" preserveAspectRatio="none">
        <defs>
          <linearGradient :id="gradientId" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stop-color="#F2B4BC" stop-opacity="0.42" />
            <stop offset="100%" stop-color="#FBE2E6" stop-opacity="0.04" />
          </linearGradient>
        </defs>
        <line
          v-for="line in gridLines"
          :key="line"
          x1="14"
          x2="306"
          :y1="line"
          :y2="line"
          stroke="#F4E5E1"
          stroke-width="1"
        />
        <path :d="areaPath" :fill="`url(#${gradientId})`" stroke="none" />
        <polyline
          :points="polyline"
          fill="none"
          stroke="#C0566B"
          stroke-width="1.8"
          stroke-linejoin="round"
        />
        <circle
          v-for="dot in dots"
          :key="dot.key"
          :cx="dot.x"
          :cy="dot.y"
          :r="dot.last ? 4 : 3.2"
          fill="#C0566B"
          stroke="#FFFFFF"
          stroke-width="1.6"
        />
      </svg>
      <view class="axis">
        <text class="axis-label">{{ firstLabel }}</text>
        <text class="axis-label">{{ midLabel }}</text>
        <text class="axis-label">{{ lastLabel }}</text>
      </view>
    </view>
  </view>
</template>

<script setup lang="ts">
import { computed } from 'vue'

interface Point {
  day: string
  kg: number
}

const props = defineProps<{ points: Point[] }>()

const gradientId = `trend-${Math.random().toString(36).slice(2, 8)}`
const gridLines = [10, 50, 90, 130]

const bounds = computed(() => {
  const values = props.points.map((point) => point.kg)
  const min = Math.min(...values)
  const max = Math.max(...values)
  return { min, max, span: max - min || 1 }
})

const dots = computed(() =>
  props.points.map((point, index) => ({
    key: `${point.day}-${index}`,
    x: props.points.length === 1 ? 160 : 16 + (index * 288) / (props.points.length - 1),
    y: 118 - ((point.kg - bounds.value.min) / bounds.value.span) * 90,
    last: index === props.points.length - 1
  }))
)

const polyline = computed(() => dots.value.map((dot) => `${dot.x},${dot.y}`).join(' '))

const areaPath = computed(() => {
  if (!dots.value.length) {
    return ''
  }
  const steps = dots.value.map((dot) => `${dot.x},${dot.y}`).join(' L ')
  const first = dots.value[0]
  const last = dots.value[dots.value.length - 1]
  return `M ${first.x} 132 L ${steps} L ${last.x} 132 Z`
})

function shortDay(day: string): string {
  const [, month, date] = day.split('-')
  return `${Number(month)}/${Number(date)}`
}

const firstLabel = computed(() => (props.points.length ? shortDay(props.points[0].day) : ''))
const midLabel = computed(() =>
  props.points.length > 2 ? shortDay(props.points[Math.floor(props.points.length / 2)].day) : ''
)
const lastLabel = computed(() =>
  props.points.length ? shortDay(props.points[props.points.length - 1].day) : ''
)
</script>

<style scoped>
.chart {
  margin-top: 10px;
}
.svg {
  width: 100%;
  height: 150px;
  display: block;
}
.axis {
  display: flex;
  justify-content: space-between;
  padding: 0 2px;
  margin-top: 2px;
}
.axis-label {
  font-size: 11px;
  line-height: 16px;
  color: var(--outline);
  font-variant-numeric: tabular-nums;
}
.empty {
  padding: 36px 0;
  text-align: center;
  color: var(--ink-2);
  font-size: 13px;
}
</style>
