<template>
  <section class="card review-card" aria-labelledby="cycle-review-title">
    <header class="review-head">
      <h2 id="cycle-review-title" class="hr-section-title">周期变化</h2>
      <H5Button class="hr-action" :disabled="!loaded" @click="emit('backfill')">补记经期</H5Button>
    </header>
    <p v-if="pending" class="muted" role="status">正在整理周期记录…</p>
    <div v-else-if="failed" class="review-head" role="alert">
      <span class="muted">暂时无法读取周期记录。</span>
      <H5Button class="hr-action" @click="emit('retry')">重试</H5Button>
    </div>
    <template v-else>
      <div class="metric-switch" role="group" aria-label="周期比较指标">
        <H5Button v-for="(option, key) in metrics" :key="key" class="segment"
          :aria-pressed="metric === key" @click="metric = key">{{ option }}</H5Button>
      </div>
      <template v-if="currentStats">
        <div class="metric-head">
          <strong class="metric-value">{{ statisticLabel }} <small>天</small></strong>
          <span class="muted">最近 {{ currentStats.count }} {{ metric === 'cycle_days' ? '个间隔' : '段完整记录' }}</span>
        </div>
        <div v-if="series.length > 1" class="metric-bars" role="list" :aria-label="metrics[metric] + '的历史比较'">
          <div v-for="row in series" :key="row.item.id" role="listitem">
            <H5Button class="bar-button" :aria-label="row.item.start_day + ' 开始，' + metrics[metric] + ' ' + row.value + ' 天。在月历查看'"
              @click="emit('select', row.item.start_day)">
              <span class="bar-date">
                <small v-if="row.item.start_day.slice(0, 4) !== newestYear">{{ row.item.start_day.slice(0, 4) }} 年</small>
                {{ formatDayLabel(row.item.start_day) }}
              </span>
              <span class="bar-track" aria-hidden="true"><i :style="{ width: barWidth(row.value) }" /></span>
              <span class="bar-value">{{ row.value }} 天</span>
            </H5Button>
          </div>
        </div>
        <p v-else class="muted">再补一条可比较的记录，就能查看两次之间的变化。</p>
      </template>
      <p v-else class="muted">{{ metric === 'duration_days' ? '补记一次实际结束日后，可在这里看到持续天数。' : '记录两次实际开始日后，可在这里看到间隔天数。' }}</p>
    </template>
  </section>

  <section class="card review-card" aria-labelledby="diary-title">
    <header class="review-head">
      <h2 id="diary-title" class="hr-section-title">感受回顾</h2>
      <H5Button class="hr-action" @click="emit('pickMonth')">{{ formatMonthLabel(month) }}</H5Button>
    </header>
    <p v-if="diaryLoading" class="muted" role="status">正在读取感受记录…</p>
    <div v-else-if="diaryFailed" class="review-head" role="alert">
      <span class="muted">暂时无法读取本月感受。</span>
      <H5Button class="hr-action" @click="emit('retryDiary')">重试</H5Button>
    </div>
    <p v-else-if="!diary.days" class="muted">这月还没有感受记录。可以从心情、经量或一句备注开始。</p>
    <template v-else>
      <p class="muted">本月有 {{ diary.days }} 天记录感受</p>
      <div v-if="groups.length" class="filters" role="group" aria-label="感受类别">
        <H5Button v-for="option in groups" :key="option.kind" class="segment"
          :aria-pressed="group?.kind === option.kind" @click="chooseGroup(option.kind)">{{ option.title }}</H5Button>
      </div>
      <div v-if="group" class="filters labels" role="group" :aria-label="group.title + '筛选'">
        <H5Button v-for="entry in group.items" :key="entry.label" class="filter"
          :aria-pressed="filter?.kind === group.kind && filter.label === entry.label"
          @click="emit('filter', { kind: group.kind, label: entry.label })">{{ entry.label }} · {{ entry.days }} 天</H5Button>
      </div>
      <div class="diary-dates">
        <div v-if="filter" class="review-head">
          <p class="muted">{{ filter.label }} · 记录日期</p>
          <H5Button class="hr-action" @click="emit('filter', null)">清除筛选</H5Button>
        </div>
        <p v-else class="muted">记录日期</p>
        <div class="filters" role="group" aria-label="在月历查看感受">
          <H5Button v-for="entry in matchingDays" :key="entry.day" class="date-link"
            @click="emit('select', entry.day)">{{ formatDayLabel(entry.day) }}</H5Button>
        </div>
      </div>
    </template>
  </section>

  <section class="card review-card" aria-labelledby="cycle-history">
    <header class="review-head">
      <h2 id="cycle-history" class="hr-section-title">经期历史</h2>
      <div v-if="years.length" class="year-filter">
        <H5Label for="cycle-history-year" class="sr-only">筛选经期年份</H5Label>
        <component :is="'select'" id="cycle-history-year" class="field" :value="yearFilter"
          @change="yearFilter = ($event.target as HTMLSelectElement).value">
          <option value="">全部年份</option>
          <option v-for="year in years" :key="year" :value="year">{{ year }} 年</option>
        </component>
      </div>
    </header>
    <p v-if="pending" class="muted">正在读取经期记录…</p>
    <p v-else-if="failed" class="muted">重新读取后可查看历史。</p>
    <p v-else-if="!filteredHistory.length" class="muted">{{ yearFilter ? '这一年没有经期记录。' : '保存第一段经期后，就能在这里回看。' }}</p>
    <template v-else>
      <p class="muted">{{ filteredHistory.length }} 段实际经期</p>
      <div v-for="item in filteredHistory.slice(0, visibleLimit)" :key="item.id" class="history-row">
        <H5Button class="history-date" :aria-label="'在月历查看 ' + item.start_day + ' 开始的经期'" @click="emit('select', item.start_day)">
          <strong>{{ periodRange(item) }}</strong>
          <span class="muted">
            {{ item.duration_days === null ? '未记录结束' : '持续 ' + item.duration_days + ' 天' }}
            <template v-if="item.cycle_days !== null"> · 距上次开始 {{ item.cycle_days }} 天</template>
          </span>
        </H5Button>
        <H5Button class="hr-action" :aria-label="'更正 ' + item.start_day + ' 开始的经期'"
          @click="emit('edit', item)">更正</H5Button>
      </div>
      <H5Button v-if="filteredHistory.length > visibleLimit" class="hr-action" @click="visibleLimit += 6">查看更多</H5Button>
    </template>
  </section>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import H5Button from '../../components/H5Button'
import { H5Label } from '../../components/H5Form'
import { formatDayLabel, formatMonthLabel } from '../../shared/dates'
import { matchesFeeling, periodRange, recentCycleStats, summarizeDiary } from '../../shared/period'
import type { FeelingFilter } from '../../shared/period'
import type { FeelingItem, PeriodItem } from '../../services/types'

const props = defineProps<{
  items: PeriodItem[]; feelings: FeelingItem[]; filter: FeelingFilter | null; month: string
  loaded: boolean; pending: boolean; failed: boolean; diaryLoading: boolean; diaryFailed: boolean
}>()
const emit = defineEmits<{
  backfill: []; retry: []; retryDiary: []; pickMonth: []; select: [day: string]; edit: [item: PeriodItem]
  filter: [value: FeelingFilter | null]
}>()
const metrics = { cycle_days: '开始日间隔', duration_days: '经期时长' } as const
const metric = ref<keyof typeof metrics>('cycle_days')
const stats = computed(() => recentCycleStats(props.items))
const currentStats = computed(() => metric.value === 'cycle_days' ? stats.value.interval : stats.value.duration)
const statisticLabel = computed(() => {
  const range = currentStats.value
  if (!range) return ''
  return range.min === range.max ? String(range.min) : range.min + '–' + range.max
})
const series = computed(() => props.items.flatMap(item => {
  const value = item[metric.value]
  return value === null ? [] : [{ item, value }]
}).slice(0, 6).reverse())
const newestYear = computed(() => series.value.at(-1)?.item.start_day.slice(0, 4))
const scale = computed(() => Math.max(1, ...series.value.map(row => row.value)))
const barWidth = (value: number) => value / scale.value * 100 + '%'

const diary = computed(() => summarizeDiary(props.feelings))
const groups = computed(() => [
  { kind: 'mood' as const, title: '心情', items: diary.value.moods },
  { kind: 'symptom' as const, title: '身体感受', items: diary.value.symptoms },
  { kind: 'flow' as const, title: '经量', items: diary.value.flows },
  { kind: 'impact' as const, title: '生活影响', items: diary.value.impacts }
].filter(item => item.items.length))
const groupKind = ref<FeelingFilter['kind']>('mood')
const group = computed(() => groups.value.find(item => item.kind === (props.filter?.kind ?? groupKind.value)) ?? groups.value[0])
const matchingDays = computed(() => {
  const filter = props.filter
  return filter ? props.feelings.filter(row => matchesFeeling(row, filter)) : props.feelings
})
function chooseGroup(kind: FeelingFilter['kind']) {
  groupKind.value = kind
  if (props.filter && props.filter.kind !== kind) emit('filter', null)
}

const yearFilter = ref('')
const visibleLimit = ref(6)
const years = computed(() => [...new Set(props.items.map(item => item.start_day.slice(0, 4)))])
const filteredHistory = computed(() => yearFilter.value
  ? props.items.filter(item => item.start_day.startsWith(yearFilter.value + '-')) : props.items)
watch(yearFilter, () => { visibleLimit.value = 6 })
watch(years, values => { if (yearFilter.value && !values.includes(yearFilter.value)) yearFilter.value = '' })
</script>

<style scoped>
.review-card { padding: 13px 15px; }
.review-head { display: flex; justify-content: space-between; align-items: center; gap: 8px; min-height: 44px; }
.review-head .hr-action { padding-inline: 0; white-space: nowrap; }
.review-head .hr-section-title { margin: 0; }
.muted { margin: 6px 0; color: var(--hr-ink-2); font-size: 13px; line-height: 1.5; }
.metric-switch, .filters { display: flex; flex-wrap: wrap; gap: 6px; }
.metric-switch { margin: 5px 0 13px; }
.filters { margin: 8px 0; }
.segment, .filter, .date-link { min-height: 44px; padding: 5px 9px; border: 1px solid var(--hr-line-strong); border-radius: 12px; background: var(--hr-paper); color: var(--hr-ink); font: 13px var(--hr-font); }
.segment[aria-pressed='true'], .filter[aria-pressed='true'] { background: var(--hr-rose-soft); border-color: var(--hr-rose); color: var(--hr-rose-deep); font-weight: 650; }
.metric-head { display: flex; align-items: baseline; flex-wrap: wrap; gap: 4px 9px; }
.metric-value { color: var(--hr-rose-deep); font: 700 32px/1.1 var(--hr-serif, Georgia, "Songti SC", serif); }
.metric-value small { font: 14px var(--hr-font); }
.metric-bars { margin: 7px 0 0; }
.bar-button { display: grid; grid-template-columns: 4.7em minmax(0, 1fr) 3em; width: 100%; align-items: center; gap: 6px; min-height: 44px; padding: 2px 0; border: 0; border-radius: 7px; background: transparent; color: var(--hr-ink); font: 13px var(--hr-font); text-align: left; }
.bar-track { display: block; height: 7px; overflow: hidden; border-radius: 999px; background: var(--hr-paper-deep); }
.bar-track i { display: block; height: 100%; border-radius: inherit; background: var(--hr-rose); }
.bar-date small { display: block; color: var(--hr-ink-2); font-size: 11px; }
.bar-value { text-align: right; font-variant-numeric: tabular-nums; }
.filter { background: var(--hr-surface); }
.diary-dates { padding-top: 6px; border-top: 1px solid var(--hr-line); }
.year-filter .field { width: auto; min-height: 44px; font-size: 14px; }
.sr-only { position: absolute; width: 1px; height: 1px; overflow: hidden; clip-path: inset(50%); white-space: nowrap; }
.history-row { display: flex; align-items: center; justify-content: space-between; gap: 8px; border-top: 1px solid var(--hr-line); }
.history-date { display: grid; gap: 2px; flex: 1; min-width: 0; min-height: 44px; padding: 8px 0; text-align: left; border: 0; border-radius: 6px; background: transparent; color: var(--hr-ink); font: 14px var(--hr-font); }
.history-date .muted { margin: 0; }
</style>
