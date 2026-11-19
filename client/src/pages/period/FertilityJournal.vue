<template>
  <section class="card fertility-intro">
    <div>
      <p class="notice">{{ fertilityNotice }}</p>
      <h2>备孕日记</h2>
      <p v-if="tryingStartedOn" class="start-date">备孕开始日期 <strong>{{ tryingStartedOn }}</strong></p>
    </div>
    <HerlogIcon name="period" class="hero-icon" />
  </section>

  <slot name="prediction" />

  <CycleCalendar :month="month" :selected="selected" :today="today" :predicted-day="predictedDay"
    :periods="items" :marked-days="markedDays" mark-label="有备孕记录" @select="emit('select', $event)" />

  <section ref="dayCard" class="card day-card" aria-labelledby="fertility-day">
    <div class="day-head">
      <h2 id="fertility-day" class="hr-section-title">{{ formatDayLabel(selected) }}</h2>
      <span v-if="selected === today" class="date-tag">今天</span>
    </div>
    <p class="muted">{{ fertilityNotice }}</p>
    <p v-if="selected > today" class="muted">可在当天或之后补记观察。</p>
    <template v-else>
      <p v-if="monthLoading" class="muted" role="status">正在读取当天观察…</p>
      <div v-else-if="monthError" class="retry" role="alert">
        <span class="muted">{{ monthError }}</span><H5Button class="hr-action" @click="retryMonth">重试</H5Button>
      </div>
      <div v-else>
        <p v-if="entry" class="detail">{{ describeDay(entry) }}</p>
        <p v-else class="muted">这一天还没有备孕记录，可以只记一项。</p>
        <p v-if="entry && !entry.bbt_c" class="muted">当天未记录体温。</p>
      </div>
      <p v-if="selectedFeeling" class="shared-details">
        <strong>已记感受</strong> {{ feelingSummary }}
      </p>
      <div class="day-actions">
        <H5Button class="primary" :disabled="monthLoading || !!monthError" @click="editing = true">
          {{ entry ? '编辑观察' : '记录观察' }}
        </H5Button>
        <H5Button class="ghost" :disabled="!overview" @click="emit('record-period')">{{ periodAction }}</H5Button>
        <H5Button class="hr-action" :disabled="feelingsLoading || feelingError" @click="emit('record-feeling')">
          {{ selectedFeeling ? '编辑经期感受' : '记录经期感受' }}
        </H5Button>
        <H5Button v-if="feelingError" class="hr-action" @click="emit('retry-feelings')">重试读取感受</H5Button>
      </div>
    </template>
  </section>

  <section class="card">
    <h2 class="hr-section-title chart-title">近 30 天基础体温</h2>
    <p v-if="chartLoading" class="muted" role="status">正在读取体温记录…</p>
    <div v-else-if="chartError" class="retry" role="alert">
      <span class="muted">{{ chartError }}</span><H5Button class="hr-action" @click="retryChart">重试</H5Button>
    </div>
    <TemperatureChart v-else :rows="chartRows" :range="recentRange" />
  </section>

  <FertilityHistory :periods="items" :today="today" :refresh="refresh" @select="showDay" />
  <FertilityDayForm v-if="editing" :day="selected" :initial="entry" @close="editing = false" @saved="onSaved" />
</template>

<script setup lang="ts">
import { computed, nextTick, ref } from 'vue'
import H5Button from '../../components/H5Button'
import HerlogIcon from '../../components/HerlogIcon.vue'
import type { FeelingItem, PeriodOverview } from '../../services/types'
import { addDays, daysInMonth, formatDayLabel, startOfMonth } from '../../shared/dates'
import { describeDay, fertilityNotice } from '../../shared/fertility'
import type { FertilityDay } from '../../shared/fertility'
import CycleCalendar from './CycleCalendar.vue'
import FertilityDayForm from './FertilityDayForm.vue'
import FertilityHistory from './FertilityHistory.vue'
import TemperatureChart from './TemperatureChart.vue'
import { useFertilityRange } from './useFertilityRange'

const props = defineProps<{
  selected: string; today: string; overview: PeriodOverview | null; predictedDay: string | null
  selectedFeeling: FeelingItem | null; feelingError: boolean; feelingsLoading: boolean
  tryingStartedOn: string | null; periodAction: string
}>()
const emit = defineEmits<{
  select: [day: string]; 'record-period': []; 'record-feeling': []; 'retry-feelings': []
}>()
const editing = ref(false)
const refresh = ref(0)
const dayCard = ref<HTMLElement | null>(null)
const month = computed(() => startOfMonth(props.selected))
const items = computed(() => props.overview?.items ?? [])
const recentRange = computed(() => ({ from: addDays(props.today, -29), to: props.today }))

const { rows: monthRows, loading: monthLoading, error: monthError, retry: retryMonth } = useFertilityRange(
  () => ({ from: month.value, to: month.value.slice(0, 7) + '-' + String(daysInMonth(month.value)).padStart(2, '0') }),
  () => refresh.value
)
const { rows: chartRows, loading: chartLoading, error: chartError, retry: retryChart } =
  useFertilityRange(() => recentRange.value, () => refresh.value)
const markedDays = computed(() => new Set(monthRows.value.map(row => row.day)))
const entry = computed(() => monthRows.value.find(row => row.day === props.selected) ?? null)
const feelingSummary = computed(() => {
  const row = props.selectedFeeling
  return row ? [row.flow && '经量 ' + row.flow, row.mood, ...row.symptoms, row.impact, row.note].filter(Boolean).join(' · ') : ''
})

async function showDay(day: string) {
  emit('select', day)
  await nextTick()
  dayCard.value?.scrollIntoView({ block: 'start' })
}

function onSaved(row: FertilityDay | null) {
  const day = row?.day ?? props.selected
  const remaining = monthRows.value.filter(item => item.day !== day)
  monthRows.value = row ? [...remaining, row] : remaining
  editing.value = false
  refresh.value += 1
  uni.showToast({ title: row ? '观察已保存' : '观察已删除', icon: 'none' })
}
</script>

<style scoped>
.fertility-intro { display: grid; grid-template-columns: minmax(0, 1fr) 38px; gap: 8px; background: var(--hr-rose-soft); }
.fertility-intro h2 { margin: 5px 0; color: var(--hr-rose-deep); font: 680 clamp(23px, 6vw, 30px)/1.15 var(--hr-serif); }
.notice { margin: 0; font-size: 13px; font-weight: 650; color: var(--hr-rose-deep); }
.hero-icon { box-sizing: border-box; width: 38px; height: 38px; padding: 8px; color: var(--hr-rose-deep); background: var(--hr-surface); border-radius: 50%; }
.start-date { margin: 7px 0 0; font-size: 13px; color: var(--hr-ink-2); }
.start-date strong { font-variant-numeric: tabular-nums; }
.day-head, .retry { display: flex; flex-wrap: wrap; align-items: center; justify-content: space-between; gap: 6px; }
.day-head h2, .chart-title { margin: 0; }
.date-tag { padding: 4px 8px; color: var(--hr-rose-deep); background: var(--hr-rose-soft); border-radius: 999px; font-size: 12px; }
.day-card p { margin: 6px 0; line-height: 1.55; }
.detail, .shared-details { font-size: 14px; overflow-wrap: anywhere; }
.shared-details { padding: 6px 0; border-block-start: 1px solid var(--hr-line); }
.shared-details strong { display: block; }
.day-actions { display: grid; grid-template-columns: repeat(auto-fit, minmax(min(100%, 120px), 1fr)); gap: 8px; margin-top: 10px; }
.day-actions .hr-action { grid-column: 1 / -1; justify-self: center; }
</style>
