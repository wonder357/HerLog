<template>
  <section class="card calendar-preview" aria-label="记录日历">
    <header class="calendar-header">
      <div><h2 class="hr-section-title">记录日历</h2><p class="muted">{{ weekLabel }}</p></div>
      <H5Button class="hr-action" @click="emit('open', today)">打开月历 ›</H5Button>
    </header>
    <div class="date-grid">
      <span v-for="label in weekdays" :key="label" class="weekday">{{ label }}</span>
      <H5Button v-for="day in week" :key="day" class="date-button" :class="{ today: day === today }"
        :aria-label="formatDayLabel(day) + (recorded?.includes(day) ? '，有记录' : '')" :aria-current="day === today ? 'date' : undefined"
        @click="emit('open', day)">
        {{ Number(day.slice(-2)) }}
        <span v-if="recorded?.includes(day)" class="week-mark" aria-hidden="true" />
      </H5Button>
    </div>
  </section>

  <HerlogSheet v-if="selected" title="健康记录月历" @close="emit('close')">
    <div class="calendar-header month-header">
      <H5Button class="hr-action" aria-label="上个月" :disabled="month <= '1900-01'" @click="shift(-1)">‹</H5Button>
      <strong aria-live="polite">{{ formatMonthLabel(month + '-01') }}</strong>
      <H5Button class="hr-action" aria-label="下个月" :disabled="month >= lastMonth" @click="shift(1)">›</H5Button>
    </div>
    <div class="date-grid">
      <span v-for="label in weekdays" :key="label" class="weekday">{{ label }}</span>
      <span v-for="blank in grid.leading" :key="'blank-' + blank" aria-hidden="true" />
      <H5Button v-for="day in grid.days" :key="day" class="date-button"
        :class="{ selected: day === selected, today: day === today, actual: actual(day), planned: planned(day), future: day > today }"
        :aria-label="dayLabel(day)" :aria-current="day === today ? 'date' : undefined" :aria-pressed="day === selected"
        @click="emit('open', day)">
        {{ Number(day.slice(-2)) }}
        <i v-if="actual(day)?.start_day === day" class="period-start" aria-hidden="true" />
        <span class="marks" aria-hidden="true">
          <i v-for="kind in otherMarks(day)" :key="kind" :class="kind" />
        </span>
      </H5Button>
    </div>
    <div class="legend">
      <span><i class="period" />经期</span><span><i class="planned" />预计开始</span>
      <span><i class="weight" />体重</span><span><i class="skin" />皮肤</span><span><i class="feeling" />感受</span>
    </div>
    <section class="day-detail" aria-live="polite">
      <h3>{{ formatDayLabel(selected) }}</h3>
      <p v-if="loading" class="muted">正在读取记录…</p>
      <div v-else-if="error" role="alert" class="retry">{{ error }}<H5Button class="hr-action" @click="emit('retry')">重试</H5Button></div>
      <template v-else>
        <p v-if="actual(selected)"><strong>经期</strong> 实际记录 · {{ formatDayLabel(actual(selected)!.start_day) }}开始</p>
        <p v-else-if="planned(selected)"><strong>预计开始</strong> 仅供记录参考，不用于避孕</p>
        <p v-if="detail?.weight_kg != null"><strong>体重</strong> {{ detail.weight_kg }} kg</p>
        <p v-if="detail?.skin_observation_count"><strong>皮肤</strong> 已保存 {{ detail.skin_observation_count }} 次观察</p>
        <p v-if="detail?.feeling_tags.length"><strong>感受</strong> {{ detail.feeling_tags.join('、') }}</p>
        <p v-if="!detail && !actual(selected) && !planned(selected)" class="muted">{{ selected > today ? '这一天还没到。' : '当天没有记录。' }}</p>
        <div v-if="detail || actual(selected) || planned(selected)" class="detail-links">
          <H5Button v-if="actual(selected) || planned(selected) || detail?.feeling_tags.length" class="hr-action" @click="emit('details', 'period')">查看经期 ›</H5Button>
          <H5Button v-if="detail?.weight_kg != null" class="hr-action" @click="emit('details', 'weight')">查看体重 ›</H5Button>
          <H5Button v-if="detail?.skin_observation_count" class="hr-action" @click="emit('details', 'skin')">查看皮肤 ›</H5Button>
        </div>
      </template>
    </section>
  </HerlogSheet>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import H5Button from '../../components/H5Button'
import HerlogSheet from '../../components/HerlogSheet.vue'
import { addDays, formatDayLabel, formatMonthLabel, monthGrid, shiftMonth } from '../../shared/dates'
import { calendarKinds, calendarMarks } from '../../shared/home'
import type { HomeOverview } from '../../services/homeService'

const props = defineProps<{
  today: string; selected: string | null; data: HomeOverview | null; prediction: string | null
  recorded: string[] | undefined; loading: boolean; error: string
}>()
const emit = defineEmits<{ open: [day: string]; close: []; retry: []; details: [page: 'period' | 'weight' | 'skin'] }>()
const weekdays = ['一', '二', '三', '四', '五', '六', '日']
const week = computed(() => {
  const weekday = new Date(props.today + 'T00:00:00Z').getUTCDay()
  const monday = addDays(props.today, -((weekday + 6) % 7))
  return weekdays.map((_, index) => addDays(monday, index))
})
const weekLabel = '点日期看当天记录'
const month = computed(() => (props.selected ?? props.today).slice(0, 7))
const lastMonth = computed(() => (props.prediction && props.prediction > props.today ? props.prediction : props.today).slice(0, 7))
const grid = computed(() => monthGrid(month.value + '-01'))
const days = computed(() => new Map((props.data?.days ?? []).map(row => [row.day, row])))
const detail = computed(() => props.selected ? days.value.get(props.selected) : null)
const actual = (day: string) => props.data?.period_intervals.find(row => row.start_day <= day && day <= (row.end_day ?? row.start_day) && day <= props.today)
const planned = (day: string) => day === props.prediction && !actual(day)
const otherMarks = (day: string) => calendarMarks(false, days.value.get(day))
const dayLabel = (day: string) => [
  formatDayLabel(day), ...calendarMarks(Boolean(actual(day)), days.value.get(day)).map(kind => calendarKinds[kind]),
  actual(day)?.start_day === day ? '经期开始日' : '',
  planned(day) ? '预计开始' : ''
].filter(Boolean).join('，')

function shift(delta: number) {
  const next = shiftMonth(month.value + '-01', delta)
  emit('open', next.slice(0, 7) === props.today.slice(0, 7) ? props.today : next)
}
</script>

<style scoped>
.calendar-header { display:flex; align-items:center; justify-content:space-between; gap:8px; }
.calendar-header h2,.calendar-header p { margin:0; }
.calendar-header p { margin-top:2px; }
.calendar-preview { padding:12px 14px; }
.calendar-preview .hr-action { padding-inline:4px; white-space:nowrap; }
.date-grid { display:grid; grid-template-columns:repeat(7,minmax(0,1fr)); gap:3px; margin-top:8px; }
.calendar-preview .date-grid { gap:0; margin-inline:-9px; }
.weekday { text-align:center; color:var(--hr-ink-2); font-size:12px; }
.date-button { position:relative; min-width:0; min-height:44px; display:grid; place-items:center; padding:5px 0 9px; border:1px solid transparent; border-radius:10px; background:transparent; color:var(--hr-ink); font:16px var(--hr-serif); }
.date-button.actual { background:var(--hr-rose-soft); color:var(--hr-rose-deep); }
.date-button.planned { border-style:dashed; border-color:var(--hr-plum); }
.date-button.selected { box-shadow:inset 0 0 0 1px var(--hr-rose-deep); }
.date-button.today { font-weight:700; text-decoration:underline; text-underline-offset:3px; }
.date-button.future { color:var(--hr-ink-3); }
.week-mark { position:absolute; bottom:4px; width:5px; height:5px; border-radius:50%; background:var(--hr-taupe); }
.period-start { position:absolute; top:5px; right:5px; width:5px; height:5px; border-radius:50%; background:var(--hr-rose); }
.marks { position:absolute; bottom:5px; display:grid; grid-template-columns:repeat(3,5px); align-items:center; gap:3px; }
.marks i,.legend i { display:inline-block; }
.weight { grid-column:1; width:5px; height:2px; background:var(--hr-peach-ink); }
.skin { grid-column:2; width:5px; height:5px; background:var(--hr-plum); border-radius:50%; }
.feeling { grid-column:3; width:4px; height:4px; background:var(--hr-taupe); transform:rotate(45deg); }
.legend { display:flex; flex-wrap:wrap; gap:6px 11px; margin:11px 0; color:var(--hr-ink-2); font-size:12px; }
.legend span { display:inline-flex; gap:5px; align-items:center; }
.legend .period,.legend .planned { width:9px; height:9px; border-radius:3px; }
.legend .period { background:var(--hr-rose-soft); border:1px solid var(--hr-rose); }
.legend .planned { border:1px dashed var(--hr-plum); }
.day-detail { padding:12px; border-radius:12px; background:var(--hr-paper-deep); }
.day-detail h3,.day-detail p { margin:0 0 5px; }
.day-detail p { font-size:14px; overflow-wrap:anywhere; }
.day-detail strong { margin-right:5px; }
.detail-links { display:flex; flex-wrap:wrap; gap:0 10px; }
.detail-links .hr-action { padding-inline:0; font-size:13px; }
.retry { display:flex; align-items:center; justify-content:space-between; gap:8px; }
</style>
