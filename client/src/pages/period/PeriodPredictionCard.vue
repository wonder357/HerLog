<template>
  <section class="prediction-card" aria-labelledby="period-prediction" :aria-busy="loading">
    <h2 id="period-prediction"><i aria-hidden="true" />经期预测</h2>
    <div class="prediction-content" aria-live="polite">
      <p v-if="loading" class="prediction-note" role="status">正在读取预测…</p>
      <p v-else-if="failed" class="prediction-note" role="alert">暂时无法读取经期预测。</p>
      <template v-else-if="prediction?.status === 'upcoming' && day">
        <div class="date-row">
          <span class="prediction-label">预计开始</span>
          <time class="prediction-date" :datetime="day">{{ dateLabel(day) }}</time>
          <span class="prediction-countdown">{{ daysUntil === 0 ? '今天' : '还有 ' + daysUntil + ' 天' }}</span>
        </div>
        <p class="prediction-note">按最近 {{ prediction.cycle_count }} 个周期估算。实际日期可能不同，不用于避孕。</p>
      </template>
      <template v-else-if="prediction?.status === 'overdue'">
        <strong class="prediction-status">已过预计开始日</strong>
        <p class="prediction-note">
          <template v-if="prediction.expected_start">原预计 {{ dateLabel(prediction.expected_start) }} 开始。</template>如果经期已经开始，可以补记实际日期。
        </p>
      </template>
      <template v-else-if="prediction?.status === 'irregular'">
        <strong class="prediction-status">近期周期变化较大</strong>
        <p class="prediction-note">最近 {{ prediction.cycle_count }} 个周期的间隔差异较大，暂缓显示预计日期。补记遗漏的开始日后会重新计算。</p>
      </template>
      <template v-else>
        <strong class="prediction-status">还差 {{ remaining }} 次开始记录</strong>
        <p class="prediction-note">累计 {{ MIN_STARTS }} 次实际开始日后，可按周期估算下次日期。</p>
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
import { MIN_STARTS } from '../../shared/period'

const props = defineProps<{
  prediction: PeriodPrediction | null
  day: string | null
  today: string
  loading: boolean
  failed: boolean
  reminderAvailable: boolean
}>()
const emit = defineEmits<{ showDay: [day: string]; remind: []; retry: []; backfill: [] }>()
const remaining = computed(() => Math.max(0, MIN_STARTS - (props.prediction?.starts_used ?? 0)))
const daysUntil = computed(() => props.day ? diffDays(props.day, props.today) : 0)

function dateLabel(day: string) {
  const year = day.slice(0, 4)
  return (year === props.today.slice(0, 4) ? '' : year + ' 年 ') + formatDayLabel(day)
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
.prediction-date { font: 650 clamp(19px, 5.6vw, 24px)/1.35 var(--hr-serif); font-variant-numeric: tabular-nums; }
.prediction-status { font-size: 15px; font-weight: 650; }
.prediction-note { margin: 4px 0 0; color: var(--hr-ink-2); font-size: 13px; line-height: 1.5; }
.prediction-actions { display: flex; flex-wrap: wrap; column-gap: 14px; }
.prediction-actions .hr-action { padding-inline: 0; color: var(--hr-plum); }
</style>
