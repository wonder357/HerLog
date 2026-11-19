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
        <span class="day-number">{{ Number(day.slice(-2)) }}</span>
        <span v-if="markedDays.has(day)" class="calendar-dot" aria-hidden="true" />
      </H5Button>
    </div>
    <div class="legend">
      <span><i class="swatch actual" />实际经期</span>
      <span><i class="swatch predicted" />预计开始</span>
      <span><i class="swatch feeling" />{{ markLabel }}</span>
      <slot />
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import H5Button from '../../components/H5Button'
import { formatDayLabel, formatMonthLabel, monthGrid, shiftMonth, startOfMonth } from '../../shared/dates'
import { periodOnDay, selectedDayInMonth } from '../../shared/period'
import type { PeriodItem } from '../../services/types'

const props = defineProps<{
  month: string; selected: string; today: string; predictedDay: string | null
  periods: PeriodItem[]; markedDays: Set<string>; markLabel: string
}>()
const emit = defineEmits<{ select: [day: string] }>()
const weekdays = ['一', '二', '三', '四', '五', '六', '日']
const grid = computed(() => monthGrid(props.month))
const latestMonth = computed(() => startOfMonth(props.predictedDay ?? props.today))
const actualDays = computed(() => new Map(grid.value.days.map(day => [
  day, day <= props.today ? periodOnDay(props.periods, day) : null
])))

function cellClass(day: string) {
  const actual = actualDays.value.get(day)
  return {
    selected: day === props.selected, actual: Boolean(actual),
    start: actual?.start_day === day, 'predicted-day': day === props.predictedDay && !actual,
    future: day > props.today
  }
}

function dayLabel(day: string) {
  return [
    formatDayLabel(day), actualDays.value.get(day) ? '实际经期' : '',
    day === props.predictedDay ? '预计开始' : '',
    props.markedDays.has(day) ? props.markLabel : ''
  ].filter(Boolean).join('，')
}

function shift(delta: number) {
  const next = shiftMonth(props.month, delta)
  if (next >= '1900-01-01' && (delta < 0 || next <= latestMonth.value)) emit('select', selectedDayInMonth(next, props.today))
}
</script>

<style scoped>
.calendar-card { padding: 10px 9px 12px; scroll-margin-top: 12px; }
.month-row { display: flex; align-items: center; justify-content: space-between; gap: 8px; padding: 0 3px; margin-bottom: 4px; }
.month-nav {
  display: grid; place-items: center; width: 44px; min-height: 44px; padding: 0; border: 0;
  border-radius: 12px; color: var(--hr-rose-deep); background: transparent; font: 26px var(--hr-font);
}
.month-nav:disabled { opacity: .45; }
.month-label { margin: 0; text-align: center; font: 680 19px var(--hr-serif); font-variant-numeric: tabular-nums; }
.calendar-grid { display: grid; grid-template-columns: repeat(7, minmax(0, 1fr)); gap: 2px; }
.weekday { text-align: center; color: var(--hr-ink-2); font-size: 12px; padding: 4px 0; }
.cell {
  position: relative; display: grid; place-items: center; min-height: 44px; min-width: 0;
  padding: 1px; border: 1px solid transparent; border-radius: 10px; color: var(--hr-ink);
  background: transparent; font: 17px var(--hr-serif); font-variant-numeric: tabular-nums;
}
.cell.future { color: var(--hr-ink-3); }
.cell[aria-current='date'] .day-number { font-weight: 700; text-decoration: underline; text-underline-offset: 3px; }
.cell.actual { background: var(--hr-rose-soft); color: var(--hr-rose-deep); }
.cell.start { background: var(--hr-rose-deep); color: var(--hr-surface-strong); }
.cell.predicted-day { border-color: var(--hr-plum); border-style: dashed; color: var(--hr-plum); }
.cell.selected { box-shadow: inset 0 0 0 1px var(--hr-rose-deep); }
.cell.start.selected { box-shadow: inset 0 0 0 1px var(--hr-surface-strong); }
.calendar-dot { position: absolute; bottom: 5px; width: 5px; height: 5px; background: var(--hr-taupe); border-radius: 50%; }
.cell.start .calendar-dot { background: var(--hr-surface-strong); }
.legend { display: flex; flex-wrap: wrap; align-items: center; gap: 6px 12px; margin: 9px 4px 0; color: var(--hr-ink-2); font-size: 12px; }
.legend span { display: inline-flex; align-items: center; gap: 5px; }
.swatch { display: inline-block; width: 11px; height: 11px; border-radius: 4px; }
.swatch.actual { background: var(--hr-rose-soft); border: 1px solid var(--hr-rose); }
.swatch.feeling { width: 6px; height: 6px; border-radius: 50%; background: var(--hr-taupe); }
.swatch.predicted { border: 1px dashed var(--hr-plum); }
.month-nav:active, .cell:active { filter: brightness(.95); }
</style>
