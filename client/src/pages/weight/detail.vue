<template>
  <view class="page plain-bottom">
    <SubHeader
      title="记录明细"
      kicker="体重 / DETAIL"
      :sub="`共 ${total} 笔 · 同日多笔全部保留`"
      fallback="/pages/weight/index"
    />

    <view class="main">
      <view class="card filters">
        <view class="filter-row">
          <view class="filter-cell">
            <picker mode="date" :value="from" :end="to" @change="onFromChange">
              <view class="control filter-control">起始 {{ from || '不限' }}</view>
            </picker>
          </view>
          <view class="filter-cell">
            <picker mode="date" :value="to" :end="today" @change="onToChange">
              <view class="control filter-control">结束 {{ to || '不限' }}</view>
            </picker>
          </view>
        </view>
        <input v-model="tag" class="control filter-control tag-input" placeholder="标签筛选（选填）" placeholder-class="ph" @confirm="load" />
        <view class="filter-actions">
          <view class="btn ghost sm filter-btn" @tap="resetFilters">重置</view>
          <view class="btn sm filter-btn" @tap="load">筛选</view>
        </view>
      </view>

      <view class="card list">
        <view v-if="items.length === 0" class="empty">还没有符合条件的记录。</view>
        <view v-for="item in items" :key="item.id" class="row" @tap="startEdit(item)">
          <view class="row-main">
            <view class="row-value">{{ item.kg }}<text class="row-unit"> kg</text></view>
            <view class="row-meta">
              {{ formatMoment(item.measured_at) }}<text v-if="item.tag"> · {{ item.tag }}</text>
            </view>
            <view v-if="item.note" class="row-meta">{{ item.note }}</view>
          </view>
          <view class="row-actions">
            <text class="act">编辑</text>
            <text class="act danger" @tap.stop="remove(item)">删除</text>
          </view>
        </view>
      </view>

      <view v-if="total > items.length" class="more" @tap="loadMore">
        加载更多（{{ items.length }}/{{ total }}）
      </view>

      <view class="note list-note">只展示已加载的 {{ items.length }} 笔，共 {{ total }} 笔。</view>

      <view class="hintbox">
        编辑会改动这一笔的数值、时间与标签；删除只移除当前一笔。趋势与统计按「每天最后一次测量」重新计算。
      </view>
    </view>

    <view v-if="editVisible" class="sheet-mask" @tap="editVisible = false" />
    <view v-if="editVisible" class="sheet">
      <view class="grab" />
      <view class="sheet-head">
        <view>
          <view class="sheet-title">修改这笔体重</view>
          <view class="sheet-sub">{{ editing ? formatMoment(editing.measured_at) : '' }}</view>
        </view>
        <view class="sheet-x" @tap="editVisible = false">×</view>
      </view>

      <view class="sheet-body">
        <input v-model="editKg" class="control" type="digit" placeholder="体重 kg" placeholder-class="ph" />
        <picker mode="date" :value="editDay" :end="today" @change="onEditDay">
          <view class="control picker-line">日期 {{ editDay }}</view>
        </picker>
        <picker mode="time" :value="editTime" @change="onEditTime">
          <view class="control picker-line">时间 {{ editTime }}</view>
        </picker>
        <input v-model="editTag" class="control" placeholder="标签（选填，如晨起）" placeholder-class="ph" />
        <input v-model="editNote" class="control" placeholder="备注（选填）" placeholder-class="ph" />
        <text v-if="editError" class="error">{{ editError }}</text>
      </view>

      <view class="sheet-foot">
        <button class="btn block" :disabled="saving" @tap="saveEdit">
          {{ saving ? '保存中…' : '保存修改' }}
        </button>
        <view class="btn ghost block cancel" @tap="editVisible = false">取消</view>
      </view>
    </view>
  </view>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { onShow } from '@dcloudio/uni-app'
import SubHeader from '../../components/SubHeader.vue'
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
.filters {
  margin-top: 4px;
  padding: 14px 16px 16px;
}
.filter-row {
  display: flex;
  gap: 10px;
}
.filter-cell {
  flex: 1;
  min-width: 0;
}
.filter-control {
  height: 40px;
  font-size: 13px;
  color: var(--ink);
  border-radius: 10px;
}
.tag-input {
  margin-top: 10px;
}
.filter-actions {
  display: flex;
  gap: 8px;
  margin-top: 12px;
}
.filter-btn {
  flex: 1;
  height: 38px;
  font-size: 13px;
}
.list {
  padding: 4px 16px 6px;
}
.row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  padding: 13px 0;
  border-bottom: 1px solid var(--card-line);
}
.row:last-child {
  border-bottom: 0;
  padding-bottom: 6px;
}
.row-main {
  flex: 1;
  min-width: 0;
}
.row-value {
  font-size: 19px;
  line-height: 25px;
  font-weight: 600;
  color: var(--ink);
  font-variant-numeric: tabular-nums;
}
.row-unit {
  font-size: 13px;
  font-weight: 400;
  color: var(--ink-2);
}
.row-meta {
  margin-top: 2px;
  font-size: 13px;
  line-height: 20px;
  color: var(--ink-2);
}
.row-actions {
  flex: 0 0 auto;
  display: flex;
  gap: 12px;
}
.act {
  font-size: 13px;
  color: var(--berry);
}
.act.danger {
  color: var(--ink-2);
}
.empty {
  padding: 26px 0;
  text-align: center;
  color: var(--ink-2);
  font-size: 13px;
}
.more {
  text-align: center;
  color: var(--berry);
  font-size: 13px;
  padding: 10px 0;
}
.list-note {
  margin-top: 10px;
}
.picker-line {
  margin-top: 10px;
  font-size: 14px;
}
.control {
  margin-top: 10px;
}
.sheet-body .control:first-child {
  margin-top: 4px;
}
.cancel {
  margin-top: 10px;
  height: 44px;
  font-size: 14px;
}
</style>
