<template>
  <view class="chart">
    <view v-if="points.length === 0" class="empty">这段时间还没有记录</view>
    <svg v-else viewBox="0 0 320 140" class="svg">
      <line v-for="line in gridLines" :key="line" :x1="24" :x2="308" :y1="line" :y2="line" stroke="#F0E6E2" stroke-width="1" />
      <polyline :points="polyline" fill="none" stroke="#B4544A" stroke-width="2" stroke-linejoin="round" />
      <circle v-for="dot in dots" :key="dot.key" :cx="dot.x" :cy="dot.y" r="3.2" fill="#B4544A" />
      <text x="24" y="132" class="axis">{{ firstLabel }}</text>
      <text x="308" y="132" class="axis" text-anchor="end">{{ lastLabel }}</text>
    </svg>
    <view class="note">图表每天取最后一次测量；缺测日不补值</view>
  </view>
</template>

<script setup lang="ts">
import { computed } from 'vue'

interface Point {
  day: string
  kg: number
}

const props = defineProps<{ points: Point[] }>()

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
    x: props.points.length === 1 ? 166 : 24 + (index * 284) / (props.points.length - 1),
    y: 110 - ((point.kg - bounds.value.min) / bounds.value.span) * 90
  }))
)

const polyline = computed(() => dots.value.map((dot) => `${dot.x},${dot.y}`).join(' '))

function shortDay(day: string): string {
  const [, month, date] = day.split('-')
  return `${Number(month)}/${Number(date)}`
}

const firstLabel = computed(() => (props.points.length ? shortDay(props.points[0].day) : ''))
const lastLabel = computed(() =>
  props.points.length ? shortDay(props.points[props.points.length - 1].day) : ''
)
</script>

<style scoped>
.chart {
  background: #ffffff;
  border-radius: 16px;
  padding: 12px;
}
.svg {
  width: 100%;
  height: 150px;
}
.axis {
  font-size: 10px;
  fill: #8a7f7a;
}
.note {
  font-size: 11px;
  color: #8a7f7a;
  margin-top: 6px;
}
.empty {
  padding: 36px 0;
  text-align: center;
  color: #a89d98;
  font-size: 13px;
}
</style>
