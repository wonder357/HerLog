<template>
  <section class="record-overview" aria-label="健康记录概览">
    <header class="calendar-header">
      <h2>健康记录概览</h2>
      <H5Button class="hr-action" @click="open(today)">查看更多 ›</H5Button>
    </header>
    <div class="date-grid">
      <H5Button v-for="day in week" :key="day" class="date-button" :class="{ today: day === today }"
        :aria-label="dayLabel(day, weekly)" :aria-current="day === today ? 'date' : undefined" :disabled="day > today" @click="open(day)">
        {{ Number(day.slice(-2)) }}
        <span class="marks" aria-hidden="true"><i v-for="kind in marks(day, weekly)" :key="kind" :class="kind" /></span>
      </H5Button>
    </div>
    <div class="legend"><span><i class="period" />经期</span><span><i class="weight" />体重</span><span><i class="skin" />皮肤</span></div>
    <p v-if="weeklyError" class="muted" role="status">部分记录未能加载</p>
  </section>

  <HerlogSheet v-if="visible" title="健康记录月历" @close="visible = false">
    <div class="calendar-header">
      <H5Button class="hr-action" aria-label="上个月" @click="moveMonth(-1)">‹</H5Button>
      <strong>{{ formatMonthLabel(month) }}</strong>
      <H5Button class="hr-action" aria-label="下个月" :disabled="month >= startOfMonth(today)" @click="moveMonth(1)">›</H5Button>
    </div>
    <div class="date-grid">
      <span v-for="label in weekdays" :key="label" class="muted">{{ label }}</span>
      <span v-for="blank in grid.leading" :key="`blank-${blank}`" aria-hidden="true" />
      <H5Button v-for="day in grid.days" :key="day" class="date-button" :class="{ selected: day === selected, today: day === today }"
        :aria-label="dayLabel(day, monthly)" :aria-pressed="day === selected" :disabled="day > today" @click="selected = day">
        {{ Number(day.slice(-2)) }}
        <span class="marks" aria-hidden="true"><i v-for="kind in marks(day, monthly)" :key="kind" :class="kind" /></span>
      </H5Button>
    </div>
    <section class="day-detail" aria-live="polite">
      <h3>{{ formatDayLabel(selected) }}的记录</h3>
      <p v-if="loading && !detail && !selectedPeriod" class="muted">正在读取记录…</p>
      <template v-else>
        <p v-if="monthError" class="muted">部分记录未能加载。<H5Button class="hr-action" @click="retry++">重试</H5Button></p>
        <p v-else-if="periods === null" class="muted">经期区间暂不可用</p>
        <p v-else-if="!selectedPeriod && !detail" class="muted">当天没有记录</p>
        <div v-if="selectedPeriod || detail?.feelings.length">
          <strong>经期</strong>
          <p v-if="selectedPeriod">经期第 {{ diffDays(selected, selectedPeriod.start_day) + 1 }} 天 · {{ formatDayLabel(selectedPeriod.start_day) }}开始</p>
          <p v-for="item in detail?.feelings" :key="item.day">{{ [item.flow && `经量：${item.flow}`, ...item.symptoms, item.impact, item.note].filter(Boolean).join(' · ') }}</p>
        </div>
        <div v-if="detail?.weights.length">
          <strong>体重</strong>
          <p v-for="item in detail.weights" :key="item.id">{{ formatMoment(item.measured_at) }} · {{ item.kg }} kg<span v-if="item.tag"> · {{ item.tag }}</span><span v-if="item.note"> · {{ item.note }}</span></p>
        </div>
        <div v-if="detail?.journal.length || detail?.photos.length">
          <strong>皮肤</strong>
          <p v-for="item in detail?.journal" :key="item.day">{{ [skinNames[item.skin_type ?? ''], item.comfort == null ? '' : `舒适度 ${item.comfort}/5`, ...item.sensations.map(code => sensationNames[code] ?? code), ...item.routine.map(code => routineNames[code] ?? code), item.note].filter(Boolean).join(' · ') || '已记录皮肤日记' }}</p>
          <p v-for="item in detail?.photos" :key="item.id">{{ formatMoment(item.captured_at) }} · {{ item.site }} · {{ item.visible }}</p>
        </div>
      </template>
    </section>
  </HerlogSheet>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import H5Button from '../../components/H5Button'
import HerlogSheet from '../../components/HerlogSheet.vue'
import { addDays, diffDays, formatDayLabel, formatMoment, formatMonthLabel, monthGrid, shanghaiDayKey, shiftMonth, startOfMonth } from '../../shared/dates'
import { currentEpoch } from '../../services/httpClient'
import { listFeelings } from '../../services/periodService'
import { listWeights } from '../../services/weightService'
import { listObservations } from '../../services/skinService'
import { listJournal, type JournalDay } from '../../services/wellnessService'
import type { FeelingItem, PeriodItem, SkinSummaryItem, WeightItem } from '../../services/types'

const props = defineProps<{ today: string; periods: PeriodItem[] | null; revision: number }>()
const weekdays = ['一', '二', '三', '四', '五', '六', '日']
const kinds = { period: '经期', weight: '体重', skin: '皮肤' }
const skinNames: Record<string, string> = { dry: '偏干', oily: '偏油', combination: '混合', balanced: '较平衡', unsure: '待观察' }
const sensationNames: Record<string, string> = { tight: '紧绷', shine: '有油光', sensitive: '易刺痒', rough: '有粗糙感', redness: '感觉偏红' }
const routineNames: Record<string, string> = { cleanse: '温和清洁', moisturize: '保湿', sunscreen: '涂防晒', shade: '找阴凉', cover: '衣帽遮挡', reapply: '补涂' }

interface DayRecords {
  feelings: FeelingItem[]
  weights: WeightItem[]
  journal: JournalDay[]
  photos: SkinSummaryItem[]
}

const week = computed(() => Array.from({ length: 7 }, (_, index) => addDays(props.today, index - 3)))
const visible = ref(false)
const selected = ref(props.today)
const month = ref(startOfMonth(props.today))
const grid = computed(() => monthGrid(month.value))
const weekly = ref(new Map<string, DayRecords>())
const monthly = ref(new Map<string, DayRecords>())
const weeklyError = ref(false)
const monthError = ref(false)
const loading = ref(false)
const retry = ref(0)
const detail = computed(() => monthly.value.get(selected.value))
const selectedPeriod = computed(() => periodOn(selected.value))

function periodOn(day: string) {
  return props.periods?.find(item => day >= item.start_day && day <= (item.end_day ?? props.today))
}

function marks(day: string, records: Map<string, DayRecords>): (keyof typeof kinds)[] {
  const entry = records.get(day)
  const result: (keyof typeof kinds)[] = []
  if (periodOn(day) || entry?.feelings.length) result.push('period')
  if (entry?.weights.length) result.push('weight')
  if (entry?.journal.length || entry?.photos.length) result.push('skin')
  return result
}

function dayLabel(day: string, records: Map<string, DayRecords>) {
  return [formatDayLabel(day), ...marks(day, records).map(kind => kinds[kind])].join('，')
}

function open(day: string) {
  selected.value = day > props.today ? props.today : day
  month.value = startOfMonth(selected.value)
  visible.value = true
}

function moveMonth(delta: number) {
  const next = shiftMonth(month.value, delta)
  if (next > startOfMonth(props.today)) return
  month.value = next
  selected.value = next === startOfMonth(props.today) ? props.today : next
}

async function allWeights(from: string, to: string) {
  const first = await listWeights({ from, to, pageSize: 100 })
  const items = [...first.items]
  for (let page = 2; (page - 1) * first.page_size < first.total; page++) {
    items.push(...(await listWeights({ from, to, page, pageSize: first.page_size })).items)
  }
  return items
}

async function loadDays(from: string, to: string) {
  const end = to > props.today ? props.today : to
  const [feelings, weights, journal, photos] = await Promise.allSettled([
    listFeelings(from, end), allWeights(from, end), listJournal(from, end), listObservations({ from, to: end })
  ])
  const records = new Map<string, DayRecords>()
  function forDay(day: string) {
    const existing = records.get(day)
    if (existing) return existing
    const entry: DayRecords = { feelings: [], weights: [], journal: [], photos: [] }
    records.set(day, entry)
    return entry
  }
  if (feelings.status === 'fulfilled') for (const item of feelings.value) forDay(item.day).feelings.push(item)
  if (weights.status === 'fulfilled') for (const item of weights.value) forDay(shanghaiDayKey(item.measured_at)).weights.push(item)
  if (journal.status === 'fulfilled') for (const item of journal.value) forDay(item.day).journal.push(item)
  if (photos.status === 'fulfilled') for (const item of photos.value) forDay(shanghaiDayKey(item.captured_at)).photos.push(item)
  return { records, failed: [feelings, weights, journal, photos].some(result => result.status === 'rejected') }
}

watch([() => props.today, () => props.revision], async (_, __, onCleanup) => {
  const epoch = currentEpoch()
  let active = true
  onCleanup(() => { active = false })
  const result = await loadDays(week.value[0], week.value[6])
  if (!active || epoch !== currentEpoch()) return
  weekly.value = result.records
  weeklyError.value = result.failed
}, { immediate: true })

watch([visible, month, () => props.revision, retry], async (_, __, onCleanup) => {
  if (!visible.value) return
  const epoch = currentEpoch()
  let active = true
  onCleanup(() => { active = false })
  loading.value = true
  const result = await loadDays(month.value, grid.value.days[grid.value.days.length - 1])
  if (!active || epoch !== currentEpoch()) return
  monthly.value = result.records
  monthError.value = result.failed
  loading.value = false
})
</script>

<style scoped>
.record-overview { margin-bottom: 12px; padding: 12px 16px; border-radius: var(--hr-radius); background: var(--hr-rose-soft); }
.calendar-header { display: flex; align-items: center; justify-content: space-between; gap: 8px; }
.calendar-header h2 { margin: 0; font-size: 16px; color: var(--hr-rose-deep); }
.calendar-header .hr-action { flex-shrink: 0; }
.date-grid { display: grid; grid-template-columns: repeat(7, minmax(0, 1fr)); align-items: center; text-align: center; }
.date-button { display: grid; place-content: center; justify-items: center; gap: 4px; min-width: 0; min-height: 44px; padding: 0; border: 0; border-radius: 8px; background: transparent; color: var(--hr-ink); }
.date-button.today { color: var(--hr-rose-deep); font-weight: 700; }
.date-button.selected { background: var(--hr-rose-soft); outline: 1px solid var(--hr-rose); outline-offset: -1px; }
.date-button:disabled { opacity: .45; }
.marks { display: flex; gap: 2px; min-height: 5px; }
.marks:empty::after { content: ''; width: 5px; height: 5px; border-radius: 50%; background: var(--hr-line-strong); }
.marks i, .legend i { display: inline-block; width: 5px; height: 5px; border-radius: 50%; }
.period { background: var(--hr-rose); }
.weight { background: var(--hr-taupe); }
.skin { background: var(--hr-plum); }
.legend { display: flex; flex-wrap: wrap; gap: 4px 12px; color: var(--hr-ink-2); font-size: 12px; }
.legend i { margin-inline-end: 4px; vertical-align: middle; }
.day-detail { margin-top: 12px; border-top: 1px solid var(--hr-line); overflow-wrap: anywhere; }
.day-detail h3 { margin: 10px 0; font-size: 16px; }
.day-detail div + div { margin-top: 8px; }
.day-detail p { margin: 3px 0; font-size: 14px; }
</style>
