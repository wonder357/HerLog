<template>
  <section class="card history">
    <h2 class="hr-section-title">备孕记录回顾</h2>
    <p class="muted">{{ fertilityNotice }}。周期长度按相邻两次实际经期开始日计算。</p>
    <div class="history-nav" role="group" aria-label="回顾方式">
      <H5Button class="mode" :aria-pressed="tab === 'dates'" @click="tab = 'dates'">按日期</H5Button>
      <H5Button class="mode" :aria-pressed="tab === 'cycle'" @click="tab = 'cycle'">按周期</H5Button>
      <H5Button class="mode" :aria-pressed="tab === 'compare'" @click="tab = 'compare'">两段对比</H5Button>
    </div>
    <template v-if="tab === 'dates'">
      <H5Form class="history-controls" @submit.prevent="applyDates">
        <div>
          <label class="hr-field-label" for="fertility-from">起始日期</label>
          <H5Input id="fertility-from" v-model="from" class="field" type="date" :max="today" required />
        </div>
        <div>
          <label class="hr-field-label" for="fertility-to">截至日期</label>
          <H5Input id="fertility-to" v-model="to" class="field" type="date" :min="from" :max="today" required />
        </div>
        <H5Button type="submit" class="ghost apply">筛选日期</H5Button>
      </H5Form>
      <p v-if="validation" class="error" role="alert">{{ validation }}</p>
    </template>
    <template v-else>
      <div v-if="options.length" class="history-controls">
        <div>
          <label class="hr-field-label" for="fertility-cycle-left">{{ tab === 'compare' ? '第一段周期' : '选择周期' }}</label>
          <select id="fertility-cycle-left" v-model="left" class="field" @change="leftOffset = 0">
            <option v-for="range in options" :key="range.from" :value="range.from" :disabled="tab === 'compare' && range.from === right">
              {{ cycleLabel(range) }}
            </option>
          </select>
        </div>
        <div v-if="tab === 'compare'">
          <label class="hr-field-label" for="fertility-cycle-right">第二段周期</label>
          <select id="fertility-cycle-right" v-model="right" class="field" @change="rightOffset = 0">
            <option v-for="range in options" :key="range.from" :value="range.from" :disabled="range.from === left">
              {{ cycleLabel(range) }}
            </option>
          </select>
        </div>
      </div>
      <p v-else class="muted">还没有实际经期开始日。可以先按日期查看备孕观察。</p>
      <p v-if="tab === 'compare' && complete.length < 2" class="muted">需要至少两段已有下一次实际开始日的周期，才能对比。</p>
    </template>
    <div v-if="leftRange && (tab !== 'compare' || rightRange)" class="results" :class="{ comparison: tab === 'compare' }">
      <FertilityResult :range="leftRange" :cycle="tab === 'dates' ? null : leftCycle" :rows="leftRows" :loading="leftLoading" :error="leftError"
        :show-chart="tab === 'compare'" @retry="retryLeft" @select="emit('select', $event)"
        @page="leftOffset += $event * 92" />
      <FertilityResult v-if="rightRange" :range="rightRange" :cycle="rightCycle" :rows="rightRows"
        :loading="rightLoading" :error="rightError" show-chart @retry="retryRight" @select="emit('select', $event)"
        @page="rightOffset += $event * 92" />
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import H5Button from '../../components/H5Button'
import H5Form from '../../components/H5Form'
import H5Input from '../../components/H5Input'
import { addDays, diffDays } from '../../shared/dates'
import { cycleRanges, fertilityNotice } from '../../shared/fertility'
import type { CycleRange, DateRange } from '../../shared/fertility'
import type { PeriodItem } from '../../services/types'
import { useFertilityRange } from './useFertilityRange'
import FertilityResult from './FertilityResult.vue'

const props = defineProps<{ today: string; periods: PeriodItem[]; refresh: number }>()
const emit = defineEmits<{ select: [day: string] }>()
const tab = ref<'dates' | 'cycle' | 'compare'>('dates')
const from = ref(addDays(props.today, -29))
const to = ref(props.today)
const dates = ref<DateRange>({ from: from.value, to: to.value })
const validation = ref('')
const left = ref('')
const right = ref('')
const leftOffset = ref(0)
const rightOffset = ref(0)
const cycles = computed(() => cycleRanges(props.periods, props.today))
const complete = computed(() => cycles.value.filter(cycle => cycle.days !== null))
const options = computed(() => tab.value === 'compare' ? complete.value : cycles.value)
const leftCycle = computed(() => options.value.find(cycle => cycle.from === left.value) ?? null)
const rightCycle = computed(() => tab.value === 'compare' ? options.value.find(cycle => cycle.from === right.value) ?? null : null)

watch([options, tab], () => {
  const first = options.value.find(cycle => cycle.from === left.value) ?? options.value[0]
  if (first?.from !== left.value) {
    left.value = first?.from ?? ''
    leftOffset.value = 0
  }
  const second = options.value.find(cycle => cycle.from === right.value && cycle.from !== left.value)
    ?? options.value.find(cycle => cycle.from !== left.value)
  if (second?.from !== right.value) {
    right.value = second?.from ?? ''
    rightOffset.value = 0
  }
}, { immediate: true })

function cyclePage(cycle: CycleRange | null, offset: number): DateRange | null {
  if (!cycle) return null
  const pageOffset = Math.max(0, Math.min(offset, Math.floor(diffDays(cycle.to, cycle.from) / 92) * 92))
  const from = addDays(cycle.from, pageOffset)
  const end = addDays(from, 91)
  return { from, to: end < cycle.to ? end : cycle.to }
}

const leftRange = computed(() => {
  if (tab.value === 'dates') return dates.value
  if (tab.value === 'compare' && complete.value.length < 2) return null
  return cyclePage(leftCycle.value, leftOffset.value)
})
const rightRange = computed(() => cyclePage(rightCycle.value, rightOffset.value))
const { rows: leftRows, loading: leftLoading, error: leftError, retry: retryLeft } =
  useFertilityRange(() => leftRange.value, () => props.refresh)
const { rows: rightRows, loading: rightLoading, error: rightError, retry: retryRight } =
  useFertilityRange(() => rightRange.value, () => props.refresh)

function cycleLabel(range: CycleRange) {
  return range.from + (range.days === null ? ' · 当前记录段' : ' · ' + range.days + ' 天')
}

function applyDates() {
  validation.value = ''
  if (!from.value || !to.value || from.value > to.value || to.value > props.today || diffDays(to.value, from.value) >= 92) {
    validation.value = '请选择今天或更早的日期，范围不超过 92 天。'
    return
  }
  dates.value = { from: from.value, to: to.value }
}
</script>

<style scoped>
.history h2 { margin: 0; }
.history p { margin-block: 6px 12px; }
.history-nav { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 6px; margin: 12px 0; }
.mode { min-height: 44px; padding: 4px 5px; background: var(--hr-paper); color: var(--hr-ink); border: 1px solid var(--hr-line-strong); border-radius: 12px; }
.mode[aria-pressed='true'] { background: var(--hr-rose-soft); color: var(--hr-rose-deep); border-color: var(--hr-rose); }
.history-controls, .results { display: grid; gap: 8px; grid-template-columns: repeat(auto-fit, minmax(min(100%, 142px), 1fr)); }
.history-controls > div { min-width: 0; }
.history-controls .field { margin: 0; padding-inline: 6px; }
.apply { grid-column: 1 / -1; }
.results { grid-template-columns: 1fr; margin-top: 9px; }
@media (min-width: 560px) {
  .results.comparison { grid-template-columns: repeat(2, minmax(0, 1fr)); }
}
</style>
