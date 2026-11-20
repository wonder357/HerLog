<template>
  <section id="cycle-calendar" class="card calendar-card" aria-labelledby="cycle-calendar-month">
    <div class="month-row">
      <H5Button class="month-nav" aria-label="上个月" :disabled="month <= '1900-01-01'" @click="shift(-1)">‹</H5Button>
      <h2 id="cycle-calendar-month" class="month-label" aria-live="polite">{{ formatMonthLabel(month) }}</h2>
      <H5Button class="month-nav" aria-label="下个月" :disabled="month >= latestMonth" @click="shift(1)">›</H5Button>
    </div>
    <div class="calendar-grid" :aria-label="formatMonthLabel(month)">
      <span v-for="name in weekdays" :key="name" class="weekday">{{ name }}</span>
      <span v-for="blank in grid.leading" :key="'blank-' + blank" aria-hidden="true" />
      <H5Button v-for="day in grid.days" :key="day" class="cell" :class="cellClass(day)"
        :aria-pressed="day === selected" :aria-current="day === today ? 'date' : undefined"
        :aria-label="dayLabel(day)" @click="emit('select', day)">
        <span class="day-number" :class="{ 'has-today': day === today }">{{ Number(day.slice(-2)) }}</span>
        <span v-if="day === today" class="today-caption" aria-hidden="true">今天</span>
        <svg v-if="role(day) === 'ovulation'" class="flower" viewBox="0 0 16 16" aria-hidden="true" focusable="false">
          <g fill="currentColor">
            <circle cx="8" cy="4" r="2.6" />
            <circle cx="12" cy="6.8" r="2.6" />
            <circle cx="10.4" cy="11.6" r="2.6" />
            <circle cx="5.6" cy="11.6" r="2.6" />
            <circle cx="4" cy="6.8" r="2.6" />
          </g>
          <circle cx="8" cy="8" r="1.7" fill="var(--hr-surface)" />
        </svg>
        <span v-if="markedDays.has(day) && day !== today" class="calendar-dot" aria-hidden="true" />
      </H5Button>
    </div>
    <div class="legend">
      <span><i class="swatch actual" />经期</span>
      <span v-if="predictedRange"><i class="swatch predicted" />预测经期</span>
      <span v-if="ovulationDay"><i class="swatch ovulation" aria-hidden="true">✿</i>排卵日</span>
      <span v-if="fertileWindow"><i class="swatch fertile" />易孕期</span>
      <span><i class="swatch feeling" />{{ markLabel }}</span>
      <slot />
    </div>
    <p v-if="predictedRange || ovulationDay" class="calendar-note">
      高亮按最近周期估算，仅供记录参考，不作为避孕或备孕依据。
    </p>
  </section>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import H5Button from '../../components/H5Button'
import { formatDayLabel, formatMonthLabel, monthGrid, shiftMonth, startOfMonth } from '../../shared/dates'
import { cycleDayRole, selectedDayInMonth } from '../../shared/period'
import type { DayRange } from '../../shared/period'
import type { PeriodItem } from '../../services/types'

const props = defineProps<{
  month: string; selected: string; today: string
  periods: PeriodItem[]; markedDays: Set<string>; markLabel: string
  predictedDay?: string | null
  predictedRange?: DayRange | null
  ovulationDay?: string | null
  fertileWindow?: DayRange | null
}>()
const emit = defineEmits<{ select: [day: string] }>()
const weekdays = ['一', '二', '三', '四', '五', '六', '日']
const grid = computed(() => monthGrid(props.month))
const latestMonth = computed(() =>
  startOfMonth(props.predictedRange?.end_day ?? props.predictedDay ?? props.today)
)
const highlight = computed(() => ({
  today: props.today,
  periods: props.periods,
  predictedRange: props.predictedRange ?? null,
  ovulationDay: props.ovulationDay ?? null,
  fertileWindow: props.fertileWindow ?? null
}))

function role(day: string) {
  return cycleDayRole(day, highlight.value)
}

const ROLE_LABEL: Record<string, string> = {
  actual: '经期',
  predicted: '预测经期',
  ovulation: '排卵日',
  fertile: '易孕期'
}

function cellClass(day: string) {
  const kind = role(day)
  return [kind, {
    selected: day === props.selected,
    start: day === props.periods.find(row => row.start_day === day)?.start_day && kind === 'actual',
    'predicted-start': kind === 'predicted' && day === props.predictedRange?.start_day,
    'predicted-end': kind === 'predicted' && day === props.predictedRange?.end_day,
    'fertile-start': kind === 'fertile' && day === props.fertileWindow?.start_day,
    'fertile-end': kind === 'fertile' && day === props.fertileWindow?.end_day,
    today: day === props.today,
    future: day > props.today
  }]
}

function dayLabel(day: string) {
  return [
    formatDayLabel(day),
    ROLE_LABEL[role(day)] ?? '',
    day === props.today ? '今天' : '',
    props.markedDays.has(day) ? props.markLabel : ''
  ].filter(Boolean).join('，')
}

function shift(delta: number) {
  const next = shiftMonth(props.month, delta)
  if (next >= '1900-01-01' && (delta < 0 || next <= latestMonth.value)) emit('select', selectedDayInMonth(next, props.today))
}
</script>

<style scoped>
.calendar-card {
  --cycle-predicted-fill: #ece1f6;
  --cycle-predicted-ink: #6b4b8a;
  padding: 10px 9px 12px; scroll-margin-top: 12px;
}
.month-row { display: flex; align-items: center; justify-content: space-between; gap: 8px; padding: 0 3px; margin-bottom: 4px; }
.month-nav {
  display: grid; place-items: center; width: 44px; min-height: 44px; padding: 0; border: 0;
  border-radius: 12px; color: var(--hr-rose-deep); background: transparent; font: 26px var(--hr-font);
}
.month-nav:disabled { opacity: .45; }
.month-label { margin: 0; text-align: center; font: 680 19px var(--hr-serif); font-variant-numeric: tabular-nums; }
.calendar-grid { display: grid; grid-template-columns: repeat(7, minmax(0, 1fr)); gap: 3px; }
.weekday { text-align: center; color: var(--hr-ink-2); font-size: 12px; padding: 4px 0; }
.cell {
  position: relative; display: grid; place-items: center; align-content: center; min-height: 46px; min-width: 0;
  padding: 2px 0; border: 1px solid transparent; border-radius: 12px; color: var(--hr-ink);
  background: transparent; font: 17px var(--hr-serif); font-variant-numeric: tabular-nums;
}
.day-number { line-height: 1.1; }
.cell.future { color: var(--hr-ink-3); }

/* 实际经期：连续粉色块，开始日加深 */
.cell.actual { background: var(--hr-rose-soft); color: var(--hr-rose-deep); font-weight: 620; }
.cell.actual.start { background: var(--hr-rose); color: var(--hr-surface-strong); font-weight: 700; }

/* 预测经期：整段淡紫块，首日虚线框，末日圆角收尾 */
.cell.predicted { background: var(--cycle-predicted-fill); color: var(--cycle-predicted-ink); font-weight: 640; }
.cell.predicted-start { border-color: var(--hr-plum); border-style: dashed; }
.cell.predicted.predicted-start { border-radius: 12px; }

/* 排卵日：淡橘底 + 花朵标记 */
.cell.ovulation { background: var(--hr-peach); color: var(--hr-peach-ink); font-weight: 700; }
.flower { position: absolute; top: 3px; right: 4px; width: 10px; height: 10px; color: var(--hr-plum); }

/* 易孕期：暖灰底，与经期粉、预测紫、排卵橘区分开 */
.cell.fertile { background: var(--hr-taupe-soft); color: var(--hr-ink-2); }

/* 今天：玫红圈 + 小字；与预测首日重叠时用圈代替虚线 */
.cell.today { box-shadow: inset 0 0 0 2px var(--hr-rose); }
.cell.predicted-start.today { border-color: transparent; border-style: solid; }
.cell.today .day-number.has-today { font-size: 16px; font-weight: 700; color: var(--hr-rose-deep); transform: translateY(-3px); }
.today-caption {
  position: absolute; bottom: 4px; font: 600 9px/1 var(--hr-font); letter-spacing: .02em;
  color: var(--hr-rose-deep);
}
.cell.selected:not(.today) { box-shadow: inset 0 0 0 1px var(--hr-ink); }
.cell.actual.start.selected { box-shadow: inset 0 0 0 1px var(--hr-surface-strong); }
.calendar-dot { position: absolute; bottom: 5px; width: 5px; height: 5px; background: var(--hr-taupe); border-radius: 50%; }
.cell.start .calendar-dot { background: var(--hr-surface-strong); }

.legend { display: flex; flex-wrap: wrap; align-items: center; gap: 6px 12px; margin: 10px 4px 0; color: var(--hr-ink-2); font-size: 12px; }
.legend span { display: inline-flex; align-items: center; gap: 5px; }
.swatch { display: inline-block; width: 11px; height: 11px; border-radius: 4px; }
.swatch.actual { background: var(--hr-rose-soft); border: 1px solid var(--hr-rose); }
.swatch.predicted { border: 1px dashed var(--hr-plum); background: var(--cycle-predicted-fill); }
.swatch.ovulation {
  display: inline-grid; place-items: center; width: 12px; height: 12px; border-radius: 50%;
  background: var(--hr-peach); color: var(--hr-plum); font-size: 9px; line-height: 1;
}
.swatch.fertile { background: var(--hr-taupe-soft); border: 1px solid var(--hr-line-strong); }
.swatch.feeling { width: 6px; height: 6px; border-radius: 50%; background: var(--hr-taupe); }
.calendar-note { margin: 7px 4px 0; color: var(--hr-ink-2); font-size: 12px; }
.month-nav:active, .cell:active { filter: brightness(.95); }
</style>
