<template>
  <view class="page">
    <view class="card filters">
      <picker mode="date" :value="from" :end="to" @change="onFromChange">
        <view class="filter-field">起始：{{ from || '不限' }}</view>
      </picker>
      <picker mode="date" :value="to" :end="today" @change="onToChange">
        <view class="filter-field">结束：{{ to || '不限' }}</view>
      </picker>
      <input v-model="tag" class="filter-field" placeholder="标签筛选（选填）" @confirm="load" />
      <view class="filter-actions">
        <view class="ghost small" @tap="resetFilters">重置</view>
        <view class="primary small" @tap="load">筛选</view>
      </view>
    </view>

    <view v-if="items.length === 0" class="card empty">还没有符合条件的记录。</view>

    <view v-for="item in items" :key="item.id" class="card record" @tap="startEdit(item)">
      <view class="record-main">
        <view class="record-value">{{ item.kg }} <text class="unit">kg</text></view>
        <view class="muted">{{ formatMoment(item.measured_at) }}<text v-if="item.tag"> · {{ item.tag }}</text></view>
        <view v-if="item.note" class="muted">{{ item.note }}</view>
      </view>
      <text class="danger" @tap.stop="remove(item)">删除</text>
    </view>

    <view v-if="total > items.length" class="more" @tap="loadMore">加载更多（{{ items.length }}/{{ total }}）</view>

    <view v-if="editVisible">
      <view class="sheet-mask" @tap="editVisible = false" />
      <view class="sheet">
        <view class="sheet-title">修改这笔体重</view>
        <input v-model="editKg" class="field" type="digit" placeholder="体重 kg" />
        <picker mode="date" :value="editDay" :end="today" @change="onEditDay">
          <view class="field">日期：{{ editDay }}</view>
        </picker>
        <picker mode="time" :value="editTime" @change="onEditTime">
          <view class="field">时间：{{ editTime }}</view>
        </picker>
        <input v-model="editTag" class="field" placeholder="标签（选填）" />
        <input v-model="editNote" class="field" placeholder="备注（选填）" />
        <text v-if="editError" class="error">{{ editError }}</text>
        <button class="primary" :disabled="saving" @tap="saveEdit">
          {{ saving ? '保存中…' : '保存修改' }}
        </button>
        <view class="ghost cancel" @tap="editVisible = false">取消</view>
      </view>
    </view>
  </view>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { onShow } from '@dcloudio/uni-app'
import { formatMoment, shanghaiDayKey, toZonedIso, todayString } from '../../shared/dates'
import { parseKgToGrams } from '../../shared/weight'
import { ApiRequestError, StaleSessionError } from '../../services/httpClient'
import { deleteWeight, listWeights, updateWeight } from '../../services/weightService'
import type { WeightItem } from '../../services/types'

const today = todayString()
const items = ref<WeightItem[]>([])
const total = ref(0)
const page = ref(1)
const from = ref('')
const to = ref('')
const tag = ref('')

const editVisible = ref(false)
const editing = ref<WeightItem | null>(null)
const editKg = ref('')
const editDay = ref(today)
const editTime = ref('08:00')
const editTag = ref('')
const editNote = ref('')
const editError = ref('')
const saving = ref(false)

async function load(append = false) {
  try {
    const data = await listWeights({
      from: from.value || undefined,
      to: to.value || undefined,
      tag: tag.value.trim() || undefined,
      page: page.value,
      pageSize: 20
    })
    items.value = append ? [...items.value, ...data.items] : data.items
    total.value = data.total
  } catch (failure) {
    if (failure instanceof StaleSessionError) {
      return
    }
    uni.showToast({
      title: failure instanceof ApiRequestError ? failure.message : '加载失败',
      icon: 'none'
    })
  }
}

function loadMore() {
  page.value += 1
  load(true)
}

function resetFilters() {
  from.value = ''
  to.value = ''
  tag.value = ''
  page.value = 1
  load()
}

function onFromChange(event: { detail: { value: string } }) {
  from.value = event.detail.value
}

function onToChange(event: { detail: { value: string } }) {
  to.value = event.detail.value
}

function startEdit(item: WeightItem) {
  editing.value = item
  editKg.value = String(item.kg)
  editDay.value = shanghaiDayKey(item.measured_at)
  const moment = formatMoment(item.measured_at)
  editTime.value = moment.slice(-5)
  editTag.value = item.tag ?? ''
  editNote.value = item.note ?? ''
  editError.value = ''
  editVisible.value = true
}

function onEditDay(event: { detail: { value: string } }) {
  editDay.value = event.detail.value
}

function onEditTime(event: { detail: { value: string } }) {
  editTime.value = event.detail.value
}

async function saveEdit() {
  const target = editing.value
  if (!target || saving.value) {
    return
  }
  editError.value = ''
  try {
    parseKgToGrams(editKg.value)
  } catch (validation) {
    editError.value = (validation as Error).message
    return
  }
  saving.value = true
  try {
    await updateWeight(target.id, {
      client_key: target.client_key,
      kg: editKg.value.trim(),
      measured_at: toZonedIso(editDay.value, editTime.value),
      tag: editTag.value.trim() || null,
      note: editNote.value.trim() || null
    })
    editVisible.value = false
    page.value = 1
    await load()
  } catch (failure) {
    editError.value =
      failure instanceof ApiRequestError ? failure.message : '保存失败，请稍后重试'
  } finally {
    saving.value = false
  }
}

function remove(item: WeightItem) {
  uni.showModal({
    title: '删除体重记录',
    content: `${formatMoment(item.measured_at)} 的 ${item.kg} kg 记录将被删除，趋势与明细会同步刷新。`,
    confirmText: '删除',
    success: async (result) => {
      if (!result.confirm) {
        return
      }
      try {
        await deleteWeight(item.id)
        page.value = 1
        await load()
      } catch (failure) {
        uni.showToast({
          title: failure instanceof ApiRequestError ? failure.message : '删除失败',
          icon: 'none'
        })
      }
    }
  })
}

onShow(() => {
  page.value = 1
  load()
})
</script>

<style scoped>
.page {
  min-height: 100vh;
  padding: 12px 16px 24px;
  box-sizing: border-box;
}
.filters {
  padding: 12px;
}
.filter-field {
  border: 1px solid #e4d8d3;
  border-radius: 10px;
  height: 38px;
  line-height: 38px;
  padding: 0 10px;
  margin-bottom: 8px;
  font-size: 13px;
  color: #4b413d;
}
.filter-actions {
  display: flex;
  gap: 10px;
}
.small {
  flex: 1;
  height: 36px;
  line-height: 36px;
  font-size: 13px;
}
.record {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.record-value {
  font-size: 20px;
  font-weight: 600;
}
.unit {
  font-size: 13px;
  font-weight: 400;
}
.danger {
  color: #c0392b;
  font-size: 13px;
}
.empty {
  text-align: center;
  color: #a89d98;
  font-size: 13px;
  padding: 28px 0;
}
.more {
  text-align: center;
  color: #b4544a;
  font-size: 13px;
  padding: 10px 0;
}
.sheet-title {
  font-size: 17px;
  font-weight: 600;
  margin-bottom: 14px;
}
.cancel {
  margin-top: 10px;
}
</style>
