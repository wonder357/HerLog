<template>
  <view class="hr-page detail-page">
    <HerlogHeading title="记录明细" back-to="/pages/weight/index" back-label="体重" />
    <details class="card filters">
      <summary>按日期或标签筛选</summary>
      <view class="filter-grid">
        <view>
          <H5Label class="hr-field-label" for="filter-start">起始日期</H5Label>
          <H5Input id="filter-start" v-model="from" class="field" type="date" :max="to || today" />
        </view>
        <view>
          <H5Label class="hr-field-label" for="filter-end">结束日期</H5Label>
          <H5Input id="filter-end" v-model="to" class="field" type="date" :min="from || undefined" :max="today" />
        </view>
      </view>
      <H5Label class="hr-field-label" for="filter-tag">标签</H5Label>
      <H5Input id="filter-tag" v-model="tag" class="field" placeholder="例如晨起" />
      <view class="filter-actions">
        <H5Button class="ghost" @click="resetFilters">重置</H5Button>
        <H5Button class="primary" @click="applyFilters">筛选</H5Button>
      </view>
    </details>
    <view class="card ledger">
      <view class="ledger-header">
        <h2 class="hr-section-title">测量记录</h2>
        <text class="muted">{{ total }} 笔</text>
      </view>
      <view v-if="!items.length" class="empty muted">还没有符合条件的记录。</view>
      <view v-for="item in items" :key="item.id" class="record">
        <view class="record-main">
          <view class="record-value hr-number">{{ item.kg }} <text class="unit">kg</text></view>
          <view v-if="item.body_fat_pct != null" class="muted">体脂率 {{ item.body_fat_pct }}%</view>
          <view class="muted">{{ formatMoment(item.measured_at) }}<text v-if="item.tag"> · {{ item.tag }}</text></view>
          <view class="muted">{{ item.source === 'scale' ? '设备测量' : '手动记录' }}<text v-if="item.feeling_tags?.length"> · {{ item.feeling_tags.map(code => feelingLabels[code]).join('、') }}</text></view>
          <view v-if="item.note" class="muted">{{ item.note }}</view>
          <H5Button v-if="item.has_photo" class="hr-action" @click="startEdit(item, true)">查看照片</H5Button>
        </view>
        <view class="record-actions">
          <H5Button class="hr-action" @click="startEdit(item)" :aria-label="'修改 ' + formatMoment(item.measured_at) + ' 的记录'">编辑</H5Button>
          <H5Button class="hr-action danger" @click="remove(item)" :aria-label="'删除 ' + formatMoment(item.measured_at) + ' 的记录'">删除</H5Button>
        </view>
      </view>
      <H5Button v-if="total > items.length" class="hr-action more" @click="loadMore">加载更多（{{ items.length }}/{{ total }}）</H5Button>
    </view>

    <view class="card metric">
      <h2 class="hr-section-title">体成分</h2>
      <view v-if="bmi?.value != null">最近一次 BMI {{ bmi.value.toFixed(1) }}</view>
      <H5Button v-else-if="bmi?.status === 'missing_height'" class="hr-action" @click="openProfile">补充身高后可查看 BMI</H5Button>
      <view v-else class="muted">有了体重和身高记录后，可以在这里查看 BMI。</view>
      <view v-if="fat?.value != null" class="muted">最近一次体脂率 {{ fat.value }}% · {{ fat.source === 'scale' ? '设备测量' : '手动填录' }}</view>
      <view v-else class="muted">在记体重时可以填入已测量的体脂率。</view>
    </view>

    <HerlogSheet v-if="editVisible" title="修改体重" :context="formatMoment(editing?.measured_at || '')"
      :busy="saving" @close="closeEdit">
      <H5Label class="hr-field-label" for="edit-weight">体重（kg）</H5Label>
      <H5Input id="edit-weight" v-model="editKg" class="field" inputmode="decimal" />
      <H5Label class="hr-field-label" for="edit-body-fat">体脂率（%，选填）</H5Label>
      <H5Input id="edit-body-fat" v-model="editBodyFat" class="field" inputmode="decimal" maxlength="5" />
      <view class="filter-grid">
        <view><H5Label class="hr-field-label" for="edit-day">日期</H5Label><H5Input id="edit-day" v-model="editDay" class="field" type="date" :max="today" /></view>
        <view><H5Label class="hr-field-label" for="edit-time">时间</H5Label><H5Input id="edit-time" v-model="editTime" class="field" type="time" /></view>
      </view>
      <H5Label class="hr-field-label" for="edit-tag">标签（选填）</H5Label>
      <H5Input id="edit-tag" v-model="editTag" class="field" maxlength="32" />
      <H5Label class="hr-field-label" for="edit-note">备注（选填）</H5Label>
      <H5Input id="edit-note" v-model="editNote" class="field" maxlength="500" />
      <view class="hr-field-label">身体感受（选填）</view>
      <view class="edit-feelings">
        <H5Button v-for="(label, code) in feelingLabels" :key="code" :class="{ chosen: editFeelings.includes(code) }"
          :aria-pressed="editFeelings.includes(code)" @click="toggleFeeling(code)">{{ label }}</H5Button>
      </view>
      <div ref="photoField">
        <PrivatePhotoEditor v-model="editPhoto" v-model:processing="photoProcessing" label="测量照片" :disabled="saving"
          :saved-path="editing?.has_photo ? weightPhotoPath(editing.id) : undefined" />
      </div>
      <view v-if="editError" class="error" role="alert">{{ editError }}</view>
      <template #actions>
        <H5Button class="primary" :disabled="saving || photoProcessing" @click="saveEdit">{{ saving ? '保存中…' : '保存修改' }}</H5Button>
      </template>
    </HerlogSheet>
  </view>
</template>

<script setup lang="ts">
import { H5Label } from '../../components/H5Form'
import HerlogHeading from '../../components/HerlogHeading.vue'
import HerlogSheet from '../../components/HerlogSheet.vue'
import H5Input from '../../components/H5Input'
import H5Button from '../../components/H5Button'
import PrivatePhotoEditor from '../../components/PrivatePhotoEditor.vue'
import { nextTick, ref } from 'vue'
import { onHide, onShow } from '@dcloudio/uni-app'
import { formatMoment, shanghaiDayKey, toZonedIso, todayString } from '../../shared/dates'
import { parseBodyFat, parseKgToGrams } from '../../shared/weight'
import { ApiRequestError, currentEpoch, StaleSessionError } from '../../services/httpClient'
import { deleteWeight, getSummary, listWeights, updateWeight } from '../../services/weightService'
import type { WeightItem, WeightSummary } from '../../services/types'
import type { Feeling } from '../../services/wellnessService'
import { weightPhotoPath } from '../../services/privatePhotoService'
import type { PrivatePhotoPayload } from '../../services/privatePhotoService'

const today = todayString()
const items = ref<WeightItem[]>([])
const bmi = ref<NonNullable<WeightSummary['metrics']>[string] | null>(null)
const fat = ref<NonNullable<WeightSummary['metrics']>[string] | null>(null)
const feelingLabels = { comfortable: '舒适', tired: '疲惫', bloating: '腹胀', puffy: '感觉浮肿' }
const total = ref(0)
const page = ref(1)
const from = ref('')
const to = ref('')
const tag = ref('')

const editVisible = ref(false)
const editFeelings = ref<Feeling[]>([])
const editing = ref<WeightItem | null>(null)
const editKg = ref('')
const editBodyFat = ref('')
const editDay = ref(today)
const editTime = ref('08:00')
const editTag = ref('')
const editNote = ref('')
const editPhoto = ref<PrivatePhotoPayload | null>()
const photoField = ref<HTMLElement | null>(null)
const photoProcessing = ref(false)
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

function applyFilters() {
  if (from.value && to.value && from.value > to.value) {
    uni.showToast({ title: '起始日期不能晚于结束日期', icon: 'none' })
    return
  }
  page.value = 1
  void load()
}

function resetFilters() {
  from.value = ''
  to.value = ''
  tag.value = ''
  page.value = 1
  load()
}

function startEdit(item: WeightItem, focusPhoto = false) {
  editPhoto.value = undefined
  editing.value = item
  editKg.value = String(item.kg)
  editBodyFat.value = item.body_fat_pct == null ? '' : String(item.body_fat_pct)
  editDay.value = shanghaiDayKey(item.measured_at)
  editTime.value = formatMoment(item.measured_at).slice(-5)
  editTag.value = item.tag ?? ''
  editNote.value = item.note ?? ''
  editFeelings.value = [...(item.feeling_tags ?? [])]
  editError.value = ''
  editVisible.value = true
  if (focusPhoto) void nextTick(() => photoField.value?.scrollIntoView({ block: 'start' }))
}

function closeEdit() {
  editVisible.value = false
  editPhoto.value = undefined
  editing.value = null
}

function toggleFeeling(code: Feeling) {
  if (editFeelings.value.includes(code)) editFeelings.value = editFeelings.value.filter(item => item !== code)
  else if (editFeelings.value.length < 3) editFeelings.value.push(code)
  else uni.showToast({ title: '最多选择三项', icon: 'none' })
}

async function saveEdit() {
  const target = editing.value
  if (!target || saving.value || photoProcessing.value) {
    return
  }
  editError.value = ''
  if (!editDay.value || !editTime.value) {
    editError.value = '请选择测量日期和时间'
    return
  }
  try {
    parseKgToGrams(editKg.value)
    parseBodyFat(editBodyFat.value)
  } catch (validation) {
    editError.value = (validation as Error).message
    return
  }
  saving.value = true
  const sameMoment = editDay.value === shanghaiDayKey(target.measured_at) &&
    editTime.value === formatMoment(target.measured_at).slice(-5)
  try {
    await updateWeight(target.id, {
      client_key: target.client_key,
      kg: editKg.value.trim(),
      body_fat_pct: parseBodyFat(editBodyFat.value),
      measured_at: sameMoment ? target.measured_at : toZonedIso(editDay.value, editTime.value),
      tag: editTag.value.trim() || null,
      note: editNote.value.trim() || null,
      feeling_tags: editFeelings.value,
      ...(editPhoto.value !== undefined ? { photo: editPhoto.value } : {})
    })
    closeEdit()
    page.value = 1
    await load()
    void loadMetrics()
  } catch (failure) {
    if (failure instanceof StaleSessionError) return
    editError.value =
      failure instanceof ApiRequestError ? failure.message : '保存失败，请稍后重试'
  } finally {
    saving.value = false
  }
}

function remove(item: WeightItem) {
  uni.showModal({
    title: '删除体重记录',
    content: `${formatMoment(item.measured_at)} 的 ${item.kg} kg 记录将被删除。${item.has_photo ? '照片将一并删除。' : ''}趋势与明细会同步刷新。`,
    confirmText: '删除',
    success: async (result) => {
      if (!result.confirm) {
        return
      }
      try {
        await deleteWeight(item.id)
        page.value = 1
        await load()
        void loadMetrics()
      } catch (failure) {
        uni.showToast({
          title: failure instanceof ApiRequestError ? failure.message : '删除失败',
          icon: 'none'
        })
      }
    }
  })
}

async function loadMetrics() {
  const epoch = currentEpoch()
  bmi.value = null
  fat.value = null
  try {
    const data = await getSummary(30)
    if (epoch === currentEpoch()) {
      bmi.value = data.metrics?.bmi ?? null
      fat.value = data.metrics?.body_fat_pct ?? null
    }
  } catch {
    // 明细仍可以独立读取。
  }
}

function openProfile() {
  uni.switchTab({ url: '/pages/me/index' })
}

onHide(closeEdit)
onShow(() => {
  page.value = 1
  load()
  void loadMetrics()
})
</script>

<style scoped>
.filters summary { cursor: pointer; min-height: 44px; color: var(--hr-ink); padding: 8px 0; box-sizing: border-box; font-size: 14px; }
.filters:not([open]) { padding-block: 4px; }
.filters[open] summary { margin-bottom: 8px; }
.filter-grid,.filter-actions { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }
.filter-grid > view,.filter-grid > uni-view { min-width: 0; }
.ledger-header { display: flex; align-items: center; justify-content: space-between; gap: 8px; margin-bottom: 6px; }
h2 { margin: 0; }
.record { display: flex; gap: 8px; align-items: center; justify-content: space-between; padding: 10px 0; border-top: 1px solid var(--hr-line); }
.record-main { min-width: 0; }
.record-actions { display: flex; flex-wrap: wrap; justify-content: end; gap: 0; flex: 0 0 auto; }
.record-actions .hr-action { padding-inline: 6px; min-width: 44px; }
.record-value { color: var(--hr-rose-deep); font-size: 25px; line-height: 1.1; }
.unit { font: 13px var(--hr-font); color: var(--hr-ink-2); }
.danger { color: var(--hr-danger); }
.empty { padding: 20px 4px; }
.more { margin: 0 auto; display: flex; }
.metric { display: grid; gap: 5px; background: var(--hr-peach); }
.metric .hr-action { justify-self: start; padding-left: 0; }
.edit-feelings { display: flex; gap: 8px; flex-wrap: wrap; margin: 7px 0 10px; }
.edit-feelings button {
  min-height: 44px; padding: 7px 11px; font-size: 13px; background: var(--hr-paper);
  color: var(--hr-ink-2); border: 1px solid var(--hr-line); border-radius: 999px;
}
.edit-feelings button.chosen { background: var(--hr-rose-soft); border-color: var(--hr-rose); color: var(--hr-rose-deep); }
</style>
