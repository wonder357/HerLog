<template>
  <view class="page">
    <view class="card">
      <view class="chips">
        <view class="chip" :class="{ active: site === '' }" @tap="selectSite('')">全部</view>
        <view
          v-for="item in SKIN_SITES"
          :key="item"
          class="chip"
          :class="{ active: site === item }"
          @tap="selectSite(item)"
        >
          {{ item }}
        </view>
      </view>
    </view>

    <view v-if="rows.length === 0" class="card empty">还没有符合条件的观察记录。</view>

    <view v-for="row in rows" :key="row.id" class="card record" @tap="openDetail(row.id)">
      <view>
        <view class="record-title">{{ row.site }} · {{ formatMoment(row.captured_at) }}</view>
        <view class="muted">{{ row.visible }}</view>
      </view>
      <view class="picks">
        <view class="pick" :class="{ active: compareSel.includes(row.id) }" @tap.stop="toggleCompare(row.id)">
          {{ compareSel.includes(row.id) ? '已选' : '对比' }}
        </view>
      </view>
    </view>

    <view v-if="compareSel.length === 2" class="card compare">
      <view class="section-title">对比（仅文字）</view>
      <view class="muted">基于两次已保存的文字观察；某次未提及某种现象，不代表该现象消失。</view>
      <view v-for="item in compareRows" :key="item.id" class="compare-item">
        <view class="record-title">{{ item.site }} · {{ formatMoment(item.captured_at) }}</view>
        <view class="compare-line">可见外观：{{ item.visible }}</view>
        <view class="compare-line">看不清：{{ item.unclear }}</view>
      </view>
      <view class="ghost" @tap="clearCompare">清空对比</view>
    </view>

    <view v-if="detail">
      <view class="sheet-mask" @tap="closeDetail" />
      <view class="sheet detail-sheet">
        <view class="section-title">{{ detail.site }} · {{ formatMoment(detail.captured_at) }}</view>
        <image v-if="detailUrl" :src="detailUrl" class="detail-image" mode="aspectFill" />
        <view class="detail-block">
          <view class="detail-label">可见外观</view>
          <view class="muted">{{ detail.visible }}</view>
        </view>
        <view class="detail-block">
          <view class="detail-label">看不清之处</view>
          <view class="muted">{{ detail.unclear }}</view>
        </view>
        <view class="detail-block">
          <view class="detail-label">值得留意</view>
          <view class="muted">{{ detail.attention }}</view>
        </view>
        <view class="muted">AI 观察 · 模型 {{ detail.model_id }} · {{ detail.prompt_version }}</view>
        <view class="ghost close" @tap="closeDetail">关闭</view>
      </view>
    </view>
  </view>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { onShow, onUnload } from '@dcloudio/uni-app'
import { formatMoment } from '../../shared/dates'
import { ApiRequestError, StaleSessionError } from '../../services/httpClient'
import {
  SKIN_SITES,
  getObservation,
  listObservations,
  observationImageUrl,
  releaseBlobUrl
} from '../../services/skinService'
import type { SkinObservation, SkinSummaryItem } from '../../services/types'

const rows = ref<SkinSummaryItem[]>([])
const site = ref('')
const compareSel = ref<number[]>([])
const compareDetails = ref<Map<number, SkinObservation>>(new Map())
const detail = ref<SkinObservation | null>(null)
const detailUrl = ref<string | null>(null)

const compareRows = computed(() => {
  const picked = rows.value.filter((row) => compareSel.value.includes(row.id))
  return picked.map((row) => ({
    id: row.id,
    site: row.site,
    captured_at: row.captured_at,
    visible: compareDetails.value.get(row.id)?.visible ?? row.visible,
    unclear: compareDetails.value.get(row.id)?.unclear ?? '（正在读取完整文字…）'
  }))
})

async function load() {
  try {
    rows.value = await listObservations({ site: site.value || undefined })
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

function selectSite(value: string) {
  site.value = value
  compareSel.value = []
  load()
}

function toggleCompare(id: number) {
  if (compareSel.value.includes(id)) {
    compareSel.value = compareSel.value.filter((item) => item !== id)
    compareDetails.value = new Map()
    return
  }
  // 对比只能挑同一部位的两条。
  const next = rows.value.find((row) => row.id === id)
  const picked = rows.value.filter((row) => compareSel.value.includes(row.id))
  if (picked.length && next && picked[0].site !== next.site) {
    uni.showToast({ title: '对比仅支持同一部位', icon: 'none' })
    return
  }
  compareSel.value = [...compareSel.value, id].slice(-2)
  void loadCompareDetails()
}

async function loadCompareDetails() {
  const map = new Map<number, SkinObservation>()
  for (const id of compareSel.value) {
    try {
      map.set(id, await getObservation(id))
    } catch {
      // 单条读取失败时退回列表摘要。
    }
  }
  compareDetails.value = map
}

function clearCompare() {
  compareSel.value = []
  compareDetails.value = new Map()
}

async function openDetail(id: number) {
  try {
    releaseBlobUrl(detailUrl.value)
    detailUrl.value = null
    detail.value = await getObservation(id)
    detailUrl.value = await observationImageUrl(id)
  } catch (failure) {
    uni.showToast({
      title: failure instanceof ApiRequestError ? failure.message : '读取失败',
      icon: 'none'
    })
  }
}

function closeDetail() {
  detail.value = null
  releaseBlobUrl(detailUrl.value)
  detailUrl.value = null
}

onShow(load)
onUnload(closeDetail)
</script>

<style scoped>
.page {
  min-height: 100vh;
  padding: 12px 16px 24px;
  box-sizing: border-box;
}
.chips {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
.chip {
  padding: 6px 12px;
  border-radius: 999px;
  border: 1px solid #e4d8d3;
  font-size: 13px;
  color: #6f635e;
}
.chip.active {
  border-color: #b4544a;
  color: #b4544a;
  background: #fdf2ef;
}
.record {
  display: flex;
  justify-content: space-between;
  gap: 10px;
}
.record-title {
  font-size: 14px;
  font-weight: 600;
  margin-bottom: 4px;
}
.picks {
  display: flex;
  align-items: flex-start;
}
.pick {
  font-size: 12px;
  color: #b4544a;
  border: 1px solid #e4d8d3;
  border-radius: 999px;
  padding: 3px 10px;
}
.pick.active {
  background: #b4544a;
  color: #ffffff;
  border-color: #b4544a;
}
.empty {
  text-align: center;
  color: #a89d98;
  font-size: 13px;
  padding: 28px 0;
}
.section-title {
  font-size: 15px;
  font-weight: 600;
  margin-bottom: 8px;
}
.compare-item {
  padding: 10px 0;
  border-bottom: 1px solid #f4ebe7;
}
.compare-line {
  font-size: 13px;
  color: #6f635e;
  line-height: 1.6;
}
.detail-sheet {
  max-height: 82vh;
  overflow-y: auto;
}
.detail-image {
  width: 100%;
  height: 180px;
  border-radius: 12px;
  margin: 8px 0;
  background: #f2ece9;
}
.detail-block {
  margin-bottom: 10px;
}
.detail-label {
  font-size: 13px;
  font-weight: 600;
  margin-bottom: 2px;
}
.close {
  margin-top: 14px;
}
</style>
