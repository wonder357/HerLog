<template>
  <section id="cycle-calendar" class="card calendar-card" aria-labelledby="cycle-calendar-month">
    <div class="month-row">
      <H5Button class="month-nav" aria-label="上个月" :disabled="month <= '1900-01-01'" @click="shift(-1)">‹</H5Button>
      <h2 id="cycle-calendar-month" class="month-label">
        <H5Button class="month-title" aria-haspopup="dialog" :aria-label="'选择月份，' + formatMonthLabel(month)"
          @click="emit('pickMonth')">{{ formatMonthLabel(month) }} <span aria-hidden="true">⌄</span></H5Button>
      </h2>
      <H5Button class="month-nav" aria-label="下个月" :disabled="month >= latestMonth" @click="shift(1)">›</H5Button>
    </div>
    <div class="calendar-grid" :aria-label="formatMonthLabel(month)">
      <span v-for="name in weekdays" :key="name" class="weekday">{{ name }}</span>
      <span v-for="blank in grid.leading" :key="'blank-' + blank" aria-hidden="true" />
      <H5Button v-for="(day, index) in grid.days" :key="day" class="cell" :class="cellClass(day, index)"
        :aria-pressed="day === selected" :aria-current="day === today ? 'date' : undefined"
        :aria-label="dayLabel(day)" @click="emit('select', day)">
        <span class="day-number">{{ Number(day.slice(-2)) }}</span>
        <span v-if="isOvulationEstimate(day)" class="ovulatory-mark" aria-hidden="true" />
        <span v-if="day === today" class="today-caption" aria-hidden="true">今天</span>
        <span v-if="markedDays.has(day)" class="calendar-dot" aria-hidden="true" />
      </H5Button>
    </div>
    <div class="legend">
      <span><i class="swatch actual" />实际经期</span>
      <span v-if="predictedDay"><i class="swatch predicted" />预计经期</span>
      <span v-if="ovulatoryWindow"><i class="swatch ovulatory" />排卵阶段估算</span>
      <span v-if="ovulatoryWindow?.estimated_day"><i class="swatch diamond" />排卵估算日</span>
      <span><i class="swatch feeling" />{{ markLabel }}</span>
      <slot />
    </div>
    <p v-if="ovulatoryWindow" class="calendar-note">排卵标记由经期日期推算，仅供记录参考，不用于避孕或备孕决策。</p>
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
  predictedEnd?: string | null
  periods: PeriodItem[]; markedDays: Set<string>; markLabel: string
  ovulatoryWindow?: { start_day: string; end_day: string; estimated_day?: string } | null
}>()
const emit = defineEmits<{ select: [day: string]; pickMonth: [] }>()
const weekdays = ['一', '二', '三', '四', '五', '六', '日']
const grid = computed(() => monthGrid(props.month))
const latestMonth = computed(() => startOfMonth(props.predictedEnd ?? props.predictedDay ?? props.today))
const actualDays = computed(() => new Map(grid.value.days.map(day => [
  day, day <= props.today ? periodOnDay(props.periods, day) : null
])))

function dayKind(day?: string) {
  if (!day) return ''
  if (actualDays.value.get(day)) return 'actual'
  if (props.predictedDay && day >= props.today && day >= props.predictedDay && day <= (props.predictedEnd ?? props.predictedDay)) return 'predicted-day'
  const range = props.ovulatoryWindow
  return range && day >= range.start_day && day <= range.end_day ? 'ovulatory' : ''
}

function isOvulationEstimate(day: string) {
  return dayKind(day) === 'ovulatory' && props.ovulatoryWindow?.estimated_day === day
}

function cellClass(day: string, index: number) {
  const kind = dayKind(day)
  const col = (grid.value.leading + index) % 7
  return [kind, {
    selected: day === props.selected,
    start: actualDays.value.get(day)?.start_day === day,
    'forecast-start': kind === 'predicted-day' && day === props.predictedDay,
    'band-left': Boolean(kind) && (col === 0 || dayKind(grid.value.days[index - 1]) !== kind),
    'band-right': Boolean(kind) && (col === 6 || dayKind(grid.value.days[index + 1]) !== kind),
    future: day > props.today
  }]
}

function dayLabel(day: string) {
  const kind = dayKind(day)
  return [
    formatDayLabel(day),
    kind === 'actual' ? '实际经期' :
      kind === 'predicted-day' ? (day === props.predictedDay ? '预计经期开始' : '预计经期') :
        isOvulationEstimate(day) ? '排卵估算日' : kind === 'ovulatory' ? '排卵阶段估算' : '',
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
  --cycle-ovulatory-ink: #276258;
  --cycle-ovulatory-fill: #e5f2eb;
  padding: 10px 9px 14px; scroll-margin-top: 12px;
}
.month-row { display: flex; align-items: center; justify-content: space-between; gap: 8px; padding: 0 3px; margin-bottom: 4px; }
.month-nav {
  display: grid; place-items: center; width: 44px; min-height: 44px; padding: 0; border: 0;
  border-radius: 12px; color: var(--hr-rose-deep); background: transparent; font: 26px var(--hr-font);
}
.month-nav:disabled { opacity: .45; }
.month-label { margin: 0; text-align: center; font: 680 19px var(--hr-serif, Georgia, "Songti SC", serif); font-variant-numeric: tabular-nums; }
.month-title { min-height: 44px; padding: 0 9px; border: 0; border-radius: 9px; background: transparent; color: var(--hr-ink); font: inherit; }
.month-title span { color: var(--hr-rose-deep); font: 15px var(--hr-font); }
.calendar-grid { display: grid; grid-template-columns: repeat(7, minmax(0, 1fr)); row-gap: 4px; }
.weekday { text-align: center; color: var(--hr-ink-2); font-size: 12px; padding: 4px 0; }
.cell {
  position: relative; display: grid; place-items: center; min-height: 44px; min-width: 0;
  padding: 1px; border: 0; border-radius: 0; color: var(--hr-ink);
  background: transparent; font: 17px var(--hr-serif, Georgia, "Songti SC", serif); font-variant-numeric: tabular-nums;
}
.cell.future { color: var(--hr-ink-3); }
.cell[aria-current='date'] .day-number { font-weight: 700; transform: translateY(-4px); }
.today-caption { position: absolute; bottom: 1px; font: 10px/13px var(--hr-font); }
.cell.actual { background: var(--hr-rose-soft); color: var(--hr-rose-deep); }
.cell.start { font-weight: 750; }
.cell.predicted-day { color: var(--hr-plum); background: var(--hr-plum-soft); border-block: 1px dashed var(--hr-plum); }
.cell.forecast-start { font-weight: 750; }
.cell.ovulatory { color: var(--cycle-ovulatory-ink); background: var(--cycle-ovulatory-fill); }
.cell.band-left { border-start-start-radius: 10px; border-end-start-radius: 10px; }
.cell.band-right { border-start-end-radius: 10px; border-end-end-radius: 10px; }
.cell.predicted-day.band-left { border-inline-start: 1px dashed var(--hr-plum); }
.cell.predicted-day.band-right { border-inline-end: 1px dashed var(--hr-plum); }
.cell.selected::after { content: ''; position: absolute; inset: 2px; border: 1.5px solid currentColor; border-radius: 8px; pointer-events: none; }
.calendar-dot { position: absolute; top: 6px; left: 6px; width: 5px; height: 5px; background: var(--hr-taupe); border-radius: 50%; }
.ovulatory-mark { position: absolute; top: 6px; right: 7px; width: 7px; height: 7px; border-radius: 1px; background: var(--cycle-ovulatory-ink); transform: rotate(45deg); }
.legend { display: flex; flex-wrap: wrap; align-items: center; gap: 6px 12px; margin: 9px 4px 0; color: var(--hr-ink-2); font-size: 12px; }
.legend span { display: inline-flex; align-items: center; gap: 5px; }
.swatch { display: inline-block; width: 11px; height: 11px; border-radius: 4px; }
.swatch.actual { background: var(--hr-rose-soft); border: 1px solid var(--hr-rose); }
.swatch.feeling { width: 6px; height: 6px; border-radius: 50%; background: var(--hr-taupe); }
.swatch.predicted { border: 1px dashed var(--hr-plum); background: var(--hr-plum-soft); }
.swatch.ovulatory { background: var(--cycle-ovulatory-fill); border: 1px solid var(--cycle-ovulatory-ink); }
.swatch.diamond { width: 7px; height: 7px; border-radius: 1px; background: var(--cycle-ovulatory-ink); transform: rotate(45deg); }
.calendar-note { margin: 7px 4px 0; color: var(--hr-ink-2); font-size: 12px; }
.month-nav:active, .cell:active { filter: brightness(.95); }
</style>
