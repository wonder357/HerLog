<template>
  <HerlogSheet title="添加日历提醒" :context="'预计 ' + formatDayLabel(expectedStart) + ' 开始'" @close="emit('close')">
    <p class="reminder-text">下载后在设备日历中打开并保存。日历只显示「个人日程提醒」，请按需要选择私人日历。</p>
    <view class="reminder-options" role="group" aria-label="提醒时间">
      <H5Button v-for="option in options" :key="option.lead" class="reminder-option"
        :disabled="!option.day" :aria-pressed="lead === option.lead" @click="lead = option.lead">
        <span>{{ option.lead ? '提前 ' + option.lead + ' 天' : '预计当天' }}</span>
        <small>{{ option.day ? formatDayLabel(option.day) : '已过期' }}</small>
      </H5Button>
    </view>
    <p class="reminder-text">提醒时间为北京时间 09:00。预计日期变化后，需在日历中手动调整。</p>
    <p v-if="message" class="reminder-text" role="status">{{ message }}</p>
    <template #actions>
      <H5Button class="primary" :disabled="!selectedDay" @click="download">下载日历文件</H5Button>
    </template>
  </HerlogSheet>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import H5Button from '../../components/H5Button'
import HerlogSheet from '../../components/HerlogSheet.vue'
import { formatDayLabel } from '../../shared/dates'
import { createReminderCalendar, reminderDay } from '../../shared/period'

const props = defineProps<{ expectedStart: string }>()
const emit = defineEmits<{ close: [] }>()
const now = ref(new Date().toISOString())
const options = computed(() => [1, 2, 3, 0].map(lead => ({
  lead, day: reminderDay(props.expectedStart, lead, now.value)
})))
const lead = ref(options.value.find(option => option.day)?.lead ?? 0)
const selectedDay = computed(() => reminderDay(props.expectedStart, lead.value, now.value))
const message = ref('')
watch(lead, () => { message.value = '' })

function download() {
  now.value = new Date().toISOString()
  const day = selectedDay.value
  if (!day) {
    message.value = '这个提醒日期已过，请换一个时间。'
    return
  }
  const uid = Array.from(crypto.getRandomValues(new Uint8Array(16)), byte => byte.toString(16).padStart(2, '0')).join('')
  const file = createReminderCalendar(day, uid, now.value)
  const url = URL.createObjectURL(new Blob([file], { type: 'text/calendar;charset=utf-8' }))
  const link = document.createElement('a')
  link.href = url
  link.download = 'herlog-reminder.ics'
  document.body.appendChild(link)
  link.click()
  link.remove()
  window.setTimeout(() => URL.revokeObjectURL(url), 1000)
  message.value = '已生成日历文件。请在设备日历中打开并保存。'
}
</script>

<style scoped>
.reminder-text { margin: 6px 0 12px; color: var(--hr-ink-2); font-size: 14px; line-height: 1.55; }
.reminder-options { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 8px; margin: 12px 0; }
.reminder-option {
  display: grid; gap: 3px; min-height: 52px; padding: 6px 8px; border: 1px solid var(--hr-line-strong);
  border-radius: 12px; background: var(--hr-paper); color: var(--hr-ink); font-size: 14px;
}
.reminder-option small { color: var(--hr-ink-2); }
.reminder-option[aria-pressed='true'] { background: var(--hr-rose-soft); border-color: var(--hr-rose); color: var(--hr-rose-deep); }
.reminder-option:disabled { opacity: .5; }
</style>
