<template>
  <HerlogSheet title="选择月份" @close="emit('close')">
    <H5Label class="hr-field-label" for="calendar-year">年份</H5Label>
    <component :is="'select'" id="calendar-year" class="field year-select" :value="pickerYear"
      @change="pickerYear = Number(($event.target as HTMLSelectElement).value)">
      <option v-for="year in years" :key="year" :value="year">{{ year }} 年</option>
    </component>
    <div class="picker-grid" role="group" :aria-label="pickerYear + ' 年的月份'">
      <H5Button v-for="number in 12" :key="number" class="picker-month"
        :disabled="monthKey(number) > latestMonth" :aria-pressed="monthKey(number) === month"
        @click="pick(monthKey(number))">{{ number }} 月</H5Button>
    </div>
    <template #actions>
      <H5Button class="ghost" @click="pick(startOfMonth(today))">本月</H5Button>
    </template>
  </HerlogSheet>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import H5Button from '../../components/H5Button'
import { H5Label } from '../../components/H5Form'
import HerlogSheet from '../../components/HerlogSheet.vue'
import { startOfMonth } from '../../shared/dates'
import { selectedDayInMonth } from '../../shared/period'

const props = defineProps<{ month: string; today: string; forecastEnd: string | null }>()
const emit = defineEmits<{ close: []; select: [day: string] }>()
const latestMonth = computed(() => startOfMonth(props.forecastEnd ?? props.today))
const pickerYear = ref(Number(props.month.slice(0, 4)))
const years = computed(() => {
  const last = Math.max(Number(latestMonth.value.slice(0, 4)), Number(props.month.slice(0, 4)))
  return Array.from({ length: last - 1899 }, (_, index) => last - index)
})
const monthKey = (number: number) => pickerYear.value + '-' + String(number).padStart(2, '0') + '-01'
function pick(next: string) {
  emit('select', selectedDayInMonth(next, props.today))
}
</script>

<style scoped>
.year-select { width: 100%; }
.picker-grid { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 8px; margin-top: 12px; }
.picker-month { min-height: 44px; padding: 4px; border: 1px solid var(--hr-line); border-radius: 12px; background: var(--hr-paper); color: var(--hr-ink); font: 14px var(--hr-font); }
.picker-month[aria-pressed='true'] { border-color: var(--hr-rose); color: var(--hr-rose-deep); background: var(--hr-rose-soft); }
.picker-month:disabled { opacity: .45; }
</style>
