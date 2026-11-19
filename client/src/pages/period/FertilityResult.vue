<template>
  <section class="result">
    <h3 v-if="cycle">{{ cycle.days === null ? '当前记录段' : '周期 ' + cycle.from + ' · ' + cycle.days + ' 天' }}</h3>
    <p class="muted range">{{ range.from }} 至 {{ range.to }}</p>
    <p v-if="loading" class="muted" role="status">正在读取记录…</p>
    <div v-else-if="error" role="alert">
      <p class="muted">{{ error }}</p><H5Button class="hr-action" @click="emit('retry')">重试</H5Button>
    </div>
    <template v-else>
      <p class="muted">{{ rows.length ? '这段日期已记 ' + rows.length + ' 天' : '这段日期没有备孕记录' }}</p>
      <TemperatureChart v-if="showChart && rows.length" :rows="rows" :range="range" />
      <ul v-if="rows.length">
        <li v-for="row in [...rows].reverse()" :key="row.day">
          <H5Button class="result-day" @click="emit('select', row.day)">
            <strong>{{ row.day }}</strong>
            <span>{{ describeDay(row) }}</span>
          </H5Button>
        </li>
      </ul>
    </template>
    <div v-if="cycle && (range.from > cycle.from || range.to < cycle.to)" class="pages">
      <H5Button class="hr-action" :disabled="range.from <= cycle.from" @click="emit('page', -1)">上一段日期</H5Button>
      <H5Button class="hr-action" :disabled="range.to >= cycle.to" @click="emit('page', 1)">下一段日期</H5Button>
    </div>
  </section>
</template>

<script setup lang="ts">
import H5Button from '../../components/H5Button'
import { describeDay } from '../../shared/fertility'
import type { CycleRange, DateRange, FertilityDay } from '../../shared/fertility'
import TemperatureChart from './TemperatureChart.vue'

defineProps<{ range: DateRange; cycle: CycleRange | null; rows: FertilityDay[]; loading: boolean; error: string; showChart?: boolean }>()
const emit = defineEmits<{ retry: []; select: [day: string]; page: [delta: number] }>()
</script>

<style scoped>
.result { min-width: 0; padding: 10px; border-radius: 12px; background: var(--hr-paper-deep); }
.result h3 { margin: 0 0 4px; overflow-wrap: anywhere; font-size: 15px; }
.result p { margin: 5px 0; }
.result .range { font-variant-numeric: tabular-nums; }
.result ul { list-style: none; margin: 0; padding: 0; }
.result-day { display: grid; gap: 3px; width: 100%; min-height: 44px; text-align: left; padding: 8px 0; background: transparent; color: var(--hr-ink); border: 0; border-top: 1px solid var(--hr-line); overflow-wrap: anywhere; }
.result-day span { color: var(--hr-ink-2); }
.pages { display: flex; justify-content: space-between; gap: 4px; }
.pages .hr-action { padding-inline: 3px; }
</style>
