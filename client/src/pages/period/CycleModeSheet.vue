<template>
  <HerlogSheet title="周期模式" :busy="saving" @close="emit('close')">
    <template v-if="store.preference">
      <div class="mode-list" role="group" aria-label="选择周期模式">
        <H5Button v-for="option in modes" :key="option.value" class="mode-choice"
          :aria-pressed="choice === option.value" :disabled="saving" @click="choose(option.value)">
          <span><strong>{{ option.title }}</strong><small>{{ option.description }}</small></span>
          <span v-if="store.mode === option.value" class="muted">当前</span>
        </H5Button>
      </div>
      <section v-if="choice === 'trying_to_conceive'" class="mode-info">
        <p class="muted">{{ fertilityNotice }}。模式可随时切换，已保存的经期和观察都会保留。</p>
        <p v-if="!store.preference.seen_fertility" class="muted">体温、试纸、黏液和同房情况均为选填。可以从一项观察开始。</p>
      </section>
      <div v-if="choice === 'trying_to_conceive' && store.mode === choice" class="start-field">
        <H5Label for="trying-start" class="hr-field-label">备孕开始日期（选填）</H5Label>
        <H5Input id="trying-start" v-model="start" class="field" type="date" :max="today" :disabled="saving" />
        <div class="start-actions">
          <H5Button class="hr-action" :disabled="saving || !start" @click="start = ''">清空日期</H5Button>
          <H5Button class="hr-action" :disabled="saving || !dateChanged" @click="saveStart">保存日期</H5Button>
        </div>
      </div>
      <div class="future-modes">
        <p><strong>怀孕</strong><span>暂未开放</span></p>
        <p><strong>产后记录</strong><span>暂未开放</span></p>
        <p><strong>围绝经期记录</strong><span>暂未开放</span></p>
      </div>
    </template>
    <p v-else-if="store.unavailable" role="alert" class="error">模式设置暂时不可用，请稍后重试。</p>
    <p v-else role="status" class="muted">正在读取模式设置…</p>
    <p v-if="error" class="error" role="alert">{{ error }}</p>
    <p v-if="success" class="muted" role="status">{{ success }}</p>
    <template #actions>
      <H5Button v-if="!store.preference && store.unavailable" class="primary" @click="store.load">重新加载</H5Button>
      <H5Button v-else-if="store.preference && choice !== store.mode" class="primary" :disabled="saving" @click="saveMode">
        {{ saving ? '切换中…' : choice === 'trying_to_conceive' ? '进入备孕模式' : '切回经期模式' }}
      </H5Button>
      <H5Button v-else class="ghost" :disabled="saving" @click="emit('close')">完成</H5Button>
    </template>
  </HerlogSheet>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import H5Button from '../../components/H5Button'
import { H5Label } from '../../components/H5Form'
import H5Input from '../../components/H5Input'
import HerlogSheet from '../../components/HerlogSheet.vue'
import { ApiRequestError, currentEpoch, StaleSessionError } from '../../services/httpClient'
import { useCyclePreference } from '../../stores/cyclePreference'
import { todayString } from '../../shared/dates'
import { fertilityNotice } from '../../shared/fertility'
import type { CycleMode } from '../../shared/fertility'

const emit = defineEmits<{ close: []; changed: [] }>()
const store = useCyclePreference()
const today = todayString()
const modes = [
  { value: 'period' as const, title: '经期', description: '查看月历、感受和周期历史' },
  { value: 'trying_to_conceive' as const, title: '备孕', description: fertilityNotice }
]
const choice = ref(store.mode)
const start = ref('')
const saving = ref(false)
const error = ref('')
const success = ref('')
const dateChanged = computed(() => (start.value || null) !== store.preference?.trying_started_on)

watch(() => store.preference, preference => {
  if (!preference || saving.value) return
  choice.value = preference.active_mode
  start.value = preference.trying_started_on ?? ''
}, { immediate: true })

onMounted(() => { if (!store.preference) void store.load() })

function choose(mode: CycleMode) {
  if (dateChanged.value && choice.value === 'trying_to_conceive' && store.mode === choice.value) {
    const epoch = currentEpoch()
    uni.showModal({
      title: '放弃未保存的开始日期？', confirmText: '放弃', cancelText: '继续编辑',
      success: result => {
        if (result.confirm && epoch === currentEpoch()) {
          start.value = store.preference?.trying_started_on ?? ''
          choice.value = mode
        }
      }
    })
    return
  }
  choice.value = mode
  error.value = ''
  success.value = ''
}

async function save(operation: () => Promise<void>, onSuccess: () => void) {
  if (saving.value) return
  const epoch = currentEpoch()
  saving.value = true
  error.value = ''
  success.value = ''
  try {
    await operation()
    if (epoch === currentEpoch()) onSuccess()
  } catch (failure) {
    if (epoch === currentEpoch() && !(failure instanceof StaleSessionError)) {
      error.value = failure instanceof ApiRequestError ? failure.message : '保存失败，请重试。'
    }
  } finally {
    saving.value = false
  }
}

function saveMode() {
  void save(() => store.chooseMode(choice.value), () => emit('changed'))
}

function saveStart() {
  if (start.value && start.value > today) {
    error.value = '备孕开始日期不能晚于今天'
    return
  }
  void save(() => store.setStart(start.value || null), () => { success.value = '备孕开始日期已更新。' })
}
</script>

<style scoped>
.mode-list { display: grid; gap: 8px; }
.mode-choice { display: flex; justify-content: space-between; text-align: left; align-items: center; gap: 8px; min-height: 62px; padding: 9px 12px; border-radius: 14px; border: 1px solid var(--hr-line-strong); background: var(--hr-paper); color: var(--hr-ink); }
.mode-choice[aria-pressed='true'] { background: var(--hr-rose-soft); border-color: var(--hr-rose); color: var(--hr-rose-deep); }
.mode-choice strong, .mode-choice small { display: block; }
.mode-choice small { margin-top: 2px; color: var(--hr-ink-2); font-size: 13px; }
.mode-info, .start-field { margin-top: 10px; padding: 10px 12px; border-radius: 12px; background: var(--hr-paper-deep); }
.mode-info p { margin: 3px 0; }
.start-field .field { margin: 0; }
.start-actions { display: flex; flex-wrap: wrap; justify-content: space-between; }
.future-modes { margin-top: 12px; }
.future-modes p { display: flex; justify-content: space-between; gap: 8px; margin: 0; padding: 8px 0; color: var(--hr-ink-2); border-bottom: 1px solid var(--hr-line); font-size: 13px; }
</style>
