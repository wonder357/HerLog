<template>
  <view class="page plain-bottom">
    <SubHeader
      title="皮肤历史"
      kicker="皮肤 / HISTORY"
      :sub="`共 ${rows.length} 次 · 同一部位前后对照`"
      fallback="/pages/skin/index"
    />

    <view class="main">
      <view class="chips filter">
        <view class="chip" :class="{ on: site === '' }" @tap="selectSite('')">全部</view>
        <view
          v-for="item in SKIN_SITES"
          :key="item"
          class="chip"
          :class="{ on: site === item }"
          @tap="selectSite(item)"
        >
          {{ item }}
        </view>
      </view>

      <view class="card list">
        <view v-if="rows.length === 0" class="empty">还没有符合条件的观察记录。</view>
        <view v-for="row in rows" :key="row.id" class="row" @tap="openDetail(row.id)">
          <view class="row-main">
            <view class="row-title">{{ row.site }} · {{ formatMoment(row.captured_at) }}</view>
            <view class="row-text">{{ row.visible }}</view>
          </view>
          <view class="pick" :class="{ on: compareSel.includes(row.id) }" @tap.stop="toggleCompare(row.id)">
            {{ compareSel.includes(row.id) ? '已选' : '对比' }}
          </view>
        </view>
      </view>

      <view v-if="compareSel.length === 2" class="card compare">
        <view class="h2">对比（仅文字）</view>
        <view class="note compare-note">
          基于两次已保存的文字观察；某次未提及某种现象，不代表该现象消失。
        </view>
        <view v-for="item in compareRows" :key="item.id" class="compare-item">
          <view class="cmp-title">{{ item.site }} · {{ formatMoment(item.captured_at) }}</view>
          <view class="cmp-line">可见外观：{{ item.visible }}</view>
          <view class="cmp-line">看不清：{{ item.unclear }}</view>
        </view>
        <view class="btn ghost sm clear" @tap="clearCompare">清空对比</view>
      </view>
    </view>

    <view v-if="detail" class="sheet-mask" @tap="closeDetail" />
    <view v-if="detail" class="sheet detail-sheet">
      <view class="grab" />
      <view class="sheet-head">
        <view>
          <view class="sheet-title">{{ detail.site }}</view>
          <view class="sheet-sub">{{ formatMoment(detail.captured_at) }}</view>
        </view>
        <view class="sheet-x" @tap="closeDetail">×</view>
      </view>

      <view class="sheet-body">
        <image v-if="detailUrl" :src="detailUrl" class="detail-image" mode="aspectFill" />
        <view class="obs-block">
          <view class="k">照片中可见</view>
          <view class="v">{{ detail.visible }}</view>
        </view>
        <view class="obs-block gap">
          <view class="k">看不清的地方</view>
          <view class="v">{{ detail.unclear }}</view>
        </view>
        <view class="obs-block gap">
          <view class="k">下次可留意</view>
          <view class="v">{{ detail.attention }}</view>
        </view>
        <view class="note model-note">
          AI 观察 · 模型 {{ detail.model_id }} · {{ detail.prompt_version }}
        </view>
      </view>

      <view class="sheet-foot">
        <view class="btn ghost block" @tap="closeDetail">关闭</view>
      </view>
    </view>
  </view>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { onShow, onUnload } from '@dcloudio/uni-app'
import SubHeader from '../../components/SubHeader.vue'
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
.filter {
  margin-top: 4px;
}
.list {
  padding: 4px 16px 6px;
}
.row {
  display: flex;
  align-items: flex-start;
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
.row-title {
  font-size: 15px;
  line-height: 22px;
  font-weight: 500;
  color: var(--ink);
}
.row-text {
  margin-top: 2px;
  font-size: 13px;
  line-height: 20px;
  color: var(--ink-2);
  overflow: hidden;
  text-overflow: ellipsis;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
}
.pick {
  flex: 0 0 auto;
  font-size: 12px;
  line-height: 18px;
  color: var(--berry);
  border: 1px solid var(--ghost-line);
  background: rgba(255, 255, 255, 0.7);
  border-radius: 999px;
  padding: 4px 10px;
}
.pick.on {
  background: var(--soft-grad);
  border-color: transparent;
  color: var(--berry-deep);
  font-weight: 600;
}
.empty {
  padding: 26px 0;
  text-align: center;
  color: var(--ink-2);
  font-size: 13px;
}
.compare {
  padding: 16px;
}
.compare-note {
  margin: 6px 0 4px;
}
.compare-item {
  padding: 10px 0;
  border-bottom: 1px solid var(--card-line);
}
.cmp-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--ink);
  margin-bottom: 4px;
}
.cmp-line {
  font-size: 13px;
  line-height: 20px;
  color: var(--ink-2);
}
.clear {
  margin-top: 12px;
  height: 34px;
}
.detail-sheet {
  max-height: 86vh;
}
.detail-image {
  width: 100%;
  height: 190px;
  border-radius: 10px;
  background: var(--photo-grad);
  margin-bottom: 12px;
  display: block;
}
.obs-block.gap {
  margin-top: 12px;
}
.model-note {
  margin-top: 12px;
}
</style>
