<template>
  <section class="prediction-card" aria-labelledby="period-prediction" :aria-busy="loading">
    <h2 id="period-prediction"><i aria-hidden="true" />经期预测</h2>
    <div class="prediction-content" aria-live="polite">
      <p v-if="loading" class="prediction-note" role="status">正在读取预测…</p>
      <p v-else-if="failed" class="prediction-note" role="alert">暂时无法读取经期预测。</p>
      <template v-else-if="range && (prediction?.status === 'upcoming' || prediction?.status === 'overdue')">
        <div class="date-row">
          <span class="prediction-label">预计经期</span>
          <time class="prediction-date" :datetime="range.start_day">{{ rangeLabel }}</time>
          <span class="prediction-countdown" :class="{ late: overdueDays > 0 }">{{ countdown }}</span>
        </div>
        <dl class="prediction-facts">
          <template v-if="ovulationDay">
            <dt><i class="fact-dot ovulation" aria-hidden="true">✿</i>排卵日</dt>
            <dd>{{ dateLabel(ovulationDay) }}</dd>
          </template>
          <template v-if="fertileWindow">
            <dt><i class="fact-dot fertile" aria-hidden="true" />易孕期</dt>
            <dd>{{ rangeText(fertileWindow) }}</dd>
          </template>
        </dl>
        <p class="prediction-note">
          <template v-if="overdueDays > 0">
            已比原预计晚 {{ overdueDays }} 天，高亮按今天起顺延；排卵日与易孕期是本周期推算，已过去。记录实际开始日后会重新计算。
          </template>
          <template v-else>
            按最近 {{ prediction.cycle_count }} 个周期估算，预测经期约 {{ duration }} 天。实际日期可能不同，不用于避孕。
          </template>
        </p>
      </template>
      <template v-else-if="prediction?.status === 'irregular'">
        <strong class="prediction-status">近期周期变化较大</strong>
        <p class="prediction-note">最近 {{ prediction.cycle_count }} 个周期的间隔差异较大，暂缓显示预计日期。补记遗漏的开始日后会重新计算。</p>
      </template>
      <template v-else>
        <strong class="prediction-status">还差 {{ remaining }} 次开始记录</strong>
        <p class="prediction-note">累计 {{ MIN_STARTS }} 次实际开始日后，可按周期估算下次日期、排卵日与易孕期。</p>
      </template>
    </div>
    <div class="prediction-actions" v-if="!loading">
      <H5Button v-if="failed" class="hr-action" @click="emit('retry')">重试预测</H5Button>
      <template v-else-if="day">
        <H5Button class="hr-action" aria-controls="cycle-calendar" @click="emit('showDay', day)">在月历查看 ›</H5Button>
        <H5Button v-if="reminderAvailable" class="hr-action" @click="emit('remind')">添加日历提醒</H5Button>
      </template>
      <H5Button v-else-if="prediction" class="hr-action" @click="emit('backfill')">
        {{ prediction.status === 'overdue' ? '补记开始日' : '补记经期' }}
      </H5Button>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import H5Button from '../../components/H5Button'
import type { PeriodPrediction } from '../../services/types'
import { diffDays, formatDayLabel } from '../../shared/dates'
import { DEFAULT_DURATION_DAYS, MIN_STARTS, fertileWindow as fertileWindowOf, ovulationDay as ovulationDayOf, scheduleRange } from '../../shared/period'
import type { DayRange } from '../../shared/period'

const props = defineProps<{
  prediction: PeriodPrediction | null
  day: string | null
  today: string
  overdueDays: number
  loading: boolean
  failed: boolean
  reminderAvailable: boolean
}>()
const emit = defineEmits<{ showDay: [day: string]; remind: []; retry: []; backfill: [] }>()
const remaining = computed(() => Math.max(0, MIN_STARTS - (props.prediction?.starts_used ?? 0)))
const duration = computed(() => props.prediction?.duration_days ?? DEFAULT_DURATION_DAYS)
const range = computed<DayRange | null>(() => {
  const prediction = props.prediction
  if (!prediction) return null
  if (prediction.predicted_range) return prediction.predicted_range
  const start = prediction.expected_start ?? props.day
  return start ? scheduleRange(start, props.today, duration.value) : null
})
const ovulationDay = computed(() => {
  const prediction = props.prediction
  if (prediction?.ovulation_day) return prediction.ovulation_day
  return prediction?.expected_start ? ovulationDayOf(prediction.expected_start) : null
})
const fertileWindow = computed<DayRange | null>(() => {
  const prediction = props.prediction
  if (prediction?.fertile_window) return prediction.fertile_window
  return prediction?.expected_start ? fertileWindowOf(prediction.expected_start) : null
})
const countdown = computed(() => {
  if (props.overdueDays > 0) return '推迟 ' + props.overdueDays + ' 天'
  const daysUntil = range.value ? diffDays(range.value.start_day, props.today) : 0
  return daysUntil === 0 ? '今天开始' : '还有 ' + daysUntil + ' 天'
})
const rangeLabel = computed(() => {
  const value = range.value
  if (!value) return ''
  const sameMonth = value.start_day.slice(0, 7) === value.end_day.slice(0, 7)
  const end = sameMonth ? formatDayLabel(value.end_day).replace(/^\d+ 月 /, '') : dateLabel(value.end_day)
  return dateLabel(value.start_day) + ' – ' + end
})

function dateLabel(day: string) {
  const year = day.slice(0, 4)
  return (year === props.today.slice(0, 4) ? '' : year + ' 年 ') + formatDayLabel(day)
}

function rangeText(value: DayRange) {
  const sameMonth = value.start_day.slice(0, 7) === value.end_day.slice(0, 7)
  const end = sameMonth ? formatDayLabel(value.end_day).replace(/^\d+ 月 /, '') : dateLabel(value.end_day)
  return dateLabel(value.start_day) + ' – ' + end
}
</script>

<style scoped>
.prediction-card {
  padding: 13px 15px 4px;
  margin-bottom: 12px;
  border: 1px solid var(--hr-line);
  border-radius: var(--hr-radius);
  background: var(--hr-plum-soft);
  color: var(--hr-plum);
}
.prediction-card h2 {
  display: flex;
  align-items: center;
  gap: 8px;
  margin: 0 0 6px;
  font: 650 15px/22px var(--hr-font);
}
.prediction-card h2 i {
  display: inline-block;
  width: 11px;
  height: 11px;
  box-sizing: border-box;
  border: 1px dashed currentColor;
  border-radius: 4px;
}
.prediction-content { padding-bottom: 8px; }
.date-row { display: flex; flex-wrap: wrap; align-items: baseline; gap: 0 8px; }
.prediction-label, .prediction-countdown { font-size: 13px; }
.prediction-countdown.late { color: var(--hr-danger); font-weight: 650; }
.prediction-date { font: 650 clamp(19px, 5.6vw, 24px)/1.35 var(--hr-serif); font-variant-numeric: tabular-nums; }
.prediction-status { font-size: 15px; font-weight: 650; }
.prediction-note { margin: 4px 0 0; color: var(--hr-ink-2); font-size: 13px; line-height: 1.5; }
.prediction-facts {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr);
  align-items: center;
  gap: 4px 10px;
  margin: 8px 0 0;
  padding: 8px 10px;
  border-radius: 12px;
  background: var(--hr-surface);
  font-size: 13px;
}
.prediction-facts dt { display: inline-flex; align-items: center; gap: 6px; color: var(--hr-ink-2); }
.prediction-facts dd { margin: 0; color: var(--hr-ink); font-variant-numeric: tabular-nums; }
.fact-dot { display: inline-block; width: 9px; height: 9px; border-radius: 3px; }
.fact-dot.ovulation {
  display: inline-grid; place-items: center; width: 13px; height: 13px; border-radius: 50%;
  background: var(--hr-peach); color: var(--hr-plum); font-size: 9px; line-height: 1;
}
.fact-dot.fertile { background: var(--hr-paper-deep); border: 1px solid var(--hr-line-strong); }
.prediction-actions { display: flex; flex-wrap: wrap; column-gap: 14px; }
.prediction-actions .hr-action { padding-inline: 0; color: var(--hr-plum); }
</style>
