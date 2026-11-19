<template>
  <HerlogSheet :title="initial ? '编辑备孕观察' : '记录备孕观察'" :context="formatDayLabel(day)"
    :busy="busy" @close="cancel">
    <p class="muted notice">{{ fertilityNotice }}。每项都可以单独填写。</p>
    <div class="temperature-fields">
      <div>
        <H5Label class="hr-field-label" for="fertility-bbt">基础体温（°C）</H5Label>
        <H5Input id="fertility-bbt" v-model="bbt" class="field" inputmode="decimal" maxlength="5" placeholder="如 36.45" :disabled="busy" />
      </div>
      <div v-if="bbt.trim()">
        <H5Label class="hr-field-label" for="fertility-bbt-time">测温时间（选填）</H5Label>
        <H5Input id="fertility-bbt-time" v-model="bbtTime" class="field" type="time" :disabled="busy" />
      </div>
    </div>
    <fieldset class="journal-field">
      <legend>排卵试纸</legend>
      <p class="muted">记录你选择的结果。已有结果可更正，新的测量可另加一笔。</p>
      <div v-for="(test, index) in tests" :key="test.key" class="test-row">
        <label :for="'lh-result-' + test.key">第 {{ index + 1 }} 笔</label>
        <select :id="'lh-result-' + test.key" v-model="test.result" class="field" :disabled="busy">
          <option value="">选择结果</option>
          <option v-for="(label, value) in lhLabels" :key="value" :value="value">{{ label }}</option>
        </select>
        <H5Input v-model="test.time" class="field" type="time" :aria-label="'第 ' + (index + 1) + ' 笔试纸时间'" :disabled="busy" />
        <H5Button class="hr-action" :aria-label="'移除第 ' + (index + 1) + ' 笔试纸'" :disabled="busy" @click="removeTest(index)">移除</H5Button>
      </div>
      <H5Button class="hr-action" :disabled="busy || tests.length >= 8" @click="addTest">添加试纸结果</H5Button>
      <p v-if="tests.length" class="muted">可保留一笔时间未记录的结果。同一时间只保存一笔。</p>
    </fieldset>
    <fieldset class="journal-field">
      <legend>宫颈黏液观察</legend>
      <div class="options">
        <H5Button v-for="(label, value) in mucusLabels" :key="value" class="option" :aria-pressed="mucus === value"
          :disabled="busy" @click="mucus = mucus === value ? null : value">{{ label }}</H5Button>
      </div>
    </fieldset>
    <fieldset class="journal-field">
      <legend>同房记录（选填）</legend>
      <div class="options">
        <H5Button v-for="item in intercourseOptions" :key="item.label" class="option"
          :aria-pressed="intercourse === item.value" :disabled="busy" @click="intercourse = item.value">{{ item.label }}</H5Button>
      </div>
    </fieldset>

    <div v-if="conflict" class="conflict" role="alert">
      <strong>这一天的记录已更新</strong>
      <p class="muted">{{ latest ? describeDay(latest) : '这一天的记录已被删除。' }}</p>
      <H5Button class="hr-action" @click="keepDraftOnLatest">保留我的草稿并继续编辑</H5Button>
    </div>
    <p v-if="error" ref="errorNotice" class="error" role="alert" tabindex="-1">{{ error }}</p>
    <template #actions>
      <H5Button v-if="revision && !conflict" class="ghost" :disabled="busy" @click="confirmDelete">删除当日记录</H5Button>
      <H5Button class="primary" :disabled="busy || conflict" @click="submit">{{ busy ? '提交中…' : '保存观察' }}</H5Button>
    </template>
  </HerlogSheet>
</template>

<script setup lang="ts">
import { computed, nextTick, ref } from 'vue'
import H5Button from '../../components/H5Button'
import { H5Label } from '../../components/H5Form'
import H5Input from '../../components/H5Input'
import HerlogSheet from '../../components/HerlogSheet.vue'
import { ApiRequestError, currentEpoch, StaleSessionError } from '../../services/httpClient'
import { deleteFertilityDay, getFertilityDay, saveFertilityDay } from '../../services/fertilityService'
import { formatDayLabel, toZonedIso } from '../../shared/dates'
import { describeDay, equalObservations, fertilityNotice, lhLabels, mucusLabels, shanghaiTime } from '../../shared/fertility'
import type { DailyValues, FertilityDay, LHResult, Mucus } from '../../shared/fertility'

const props = defineProps<{ day: string; initial: FertilityDay | null }>()
const emit = defineEmits<{ close: []; saved: [entry: FertilityDay | null] }>()
const revision = ref(props.initial?.revision ?? null)
const bbt = ref(props.initial?.bbt_c ?? '')
const bbtTime = ref(shanghaiTime(props.initial?.bbt_measured_at))
const mucus = ref<Mucus | null>(props.initial?.cervical_mucus ?? null)
const intercourse = ref<boolean | null>(props.initial?.intercourse_occurred ?? null)
const busy = ref(false)
const error = ref('')
const errorNotice = ref<HTMLElement | null>(null)
const latest = ref<FertilityDay | null>(null)
const conflict = ref(false)
const intercourseOptions = [{ label: '未记录', value: null }, { label: '有', value: true }, { label: '无', value: false }]
let rowKey = 0
const tests = ref((props.initial?.lh_tests ?? []).map(test => ({
  key: rowKey++, result: test.result as LHResult | '', time: shanghaiTime(test.measured_at)
})))

const values = computed<DailyValues>(() => ({
  bbt_c: bbt.value.trim() || null,
  bbt_measured_at: bbt.value.trim() && bbtTime.value ? toZonedIso(props.day, bbtTime.value) : null,
  lh_tests: tests.value.flatMap(test => test.result ? [{
    result: test.result, measured_at: test.time ? toZonedIso(props.day, test.time) : null
  }] : []),
  cervical_mucus: mucus.value,
  intercourse_occurred: intercourse.value
}))
const dirty = computed(() => !equalObservations(values.value, props.initial ?? {
  bbt_c: null, bbt_measured_at: null, lh_tests: [], cervical_mucus: null, intercourse_occurred: null
}) || tests.value.some(test => !test.result && test.time))

function addTest() {
  tests.value.push({ key: rowKey++, result: '', time: '' })
}

function removeTest(index: number) {
  tests.value.splice(index, 1)
}

function showError(message: string) {
  error.value = message
  void nextTick(() => errorNotice.value?.focus())
}

function cancel() {
  if (busy.value) return
  if (!dirty.value) {
    emit('close')
    return
  }
  const epoch = currentEpoch()
  uni.showModal({
    title: '放弃未保存的观察？', cancelText: '继续编辑', confirmText: '放弃草稿',
    success: result => { if (epoch === currentEpoch() && result.confirm) emit('close') }
  })
}

async function loadLatest(): Promise<FertilityDay | null> {
  try {
    return await getFertilityDay(props.day)
  } catch (failure) {
    if (failure instanceof ApiRequestError && failure.status === 404) return null
    throw failure
  }
}

function showConflict(entry: FertilityDay | null) {
  latest.value = entry
  conflict.value = true
  error.value = ''
}

function keepDraftOnLatest() {
  revision.value = latest.value?.revision ?? null
  conflict.value = false
  error.value = '已保留草稿。再次保存会以当前表单为准。'
}

async function write(operation: () => Promise<FertilityDay | null>, draft: DailyValues | null) {
  if (busy.value) return
  busy.value = true
  error.value = ''
  const epoch = currentEpoch()
  try {
    const result = await operation()
    if (epoch === currentEpoch()) emit('saved', result)
  } catch (failure) {
    if (epoch !== currentEpoch() || failure instanceof StaleSessionError) return
    const status = failure instanceof ApiRequestError ? failure.status : undefined
    if (status === 409 || status === 404 || status === 0 || (status !== undefined && status >= 500)) {
      try {
        const current = await loadLatest()
        if (epoch !== currentEpoch()) return
        if ((!current && !draft) || (current && draft && equalObservations(current, draft))) {
          emit('saved', current)
          return
        }
        if ((current?.revision ?? null) !== revision.value) {
          showConflict(current)
          return
        }
      } catch {
        if (epoch !== currentEpoch()) return
      }
    }
    showError(failure instanceof ApiRequestError ? failure.message : '保存失败，请检查网络后重试。')
  } finally {
    busy.value = false
  }
}

function submit() {
  const draft = values.value
  if (draft.bbt_c && (!/^\d{2}(\.\d{1,2})?$/.test(draft.bbt_c) || Number(draft.bbt_c) < 30 || Number(draft.bbt_c) > 45)) {
    showError('请检查体温录入，使用摄氏度和最多两位小数。')
  } else if (tests.value.some(test => !test.result)) {
    showError('请选择每笔试纸的结果，或移除空行。')
  } else if (new Set(draft.lh_tests.map(test => test.measured_at)).size !== draft.lh_tests.length) {
    showError('同一测量时间只能保存一笔试纸结果，请检查时间。')
  } else if (!draft.bbt_c && !draft.lh_tests.length && !draft.cervical_mucus && draft.intercourse_occurred === null) {
    showError('请至少填写一项观察。需要清空时请选择删除当日记录。')
  } else {
    const previous = (latest.value ?? props.initial)?.lh_tests ?? []
    const replaces = previous.some(test => {
      const match = draft.lh_tests.find(item => shanghaiTime(item.measured_at) === shanghaiTime(test.measured_at))
      return match && match.result !== test.result
    })
    if (!replaces) {
      void write(() => saveFertilityDay(props.day, draft, revision.value), draft)
      return
    }
    const epoch = currentEpoch()
    uni.showModal({
      title: '替换已记录的试纸结果？', content: '新的试纸结果将替换同一测量时间的结果。',
      confirmText: '替换', cancelText: '继续编辑',
      success: result => {
        if (epoch === currentEpoch() && result.confirm) void write(() => saveFertilityDay(props.day, draft, revision.value), draft)
      }
    })
  }
}

function confirmDelete() {
  const version = revision.value
  if (!version) return
  const epoch = currentEpoch()
  uni.showModal({
    title: '删除当天的备孕观察？', content: '当天的备孕观察将被删除。经期和感受记录会保留。',
    confirmText: '删除',
    success: result => {
      if (epoch === currentEpoch() && result.confirm) void write(() => deleteFertilityDay(props.day, version), null)
    }
  })
}
</script>

<style scoped>
.notice, .journal-field p { margin: 4px 0 8px; }
.temperature-fields { display: grid; grid-template-columns: repeat(auto-fit, minmax(min(100%, 140px), 1fr)); gap: 8px; margin-top: 12px; }
.journal-field { padding: 7px 0 9px; margin: 3px 0 8px; min-width: 0; border: 0; border-bottom: 1px solid var(--hr-line); }
.journal-field legend { padding: 0; color: var(--hr-ink); font-size: 14px; font-weight: 650; }
.options { display: flex; flex-wrap: wrap; gap: 8px; }
.option { min-height: 44px; padding: 6px 12px; background: var(--hr-paper); color: var(--hr-ink); border: 1px solid var(--hr-line-strong); border-radius: 12px; }
.option[aria-pressed='true'] { background: var(--hr-rose-soft); color: var(--hr-rose-deep); border-color: var(--hr-rose); }
.test-row { display: grid; grid-template-columns: minmax(88px, 1fr) minmax(86px, 1fr) auto; align-items: center; gap: 4px 6px; margin-top: 8px; }
.test-row label { grid-column: 1 / -1; font-size: 13px; }
.test-row .field { min-width: 0; margin: 0; padding-inline: 5px; }
.test-row .hr-action { padding-inline: 4px; }
.conflict { padding: 10px; border-radius: 12px; background: var(--hr-peach); }
</style>
