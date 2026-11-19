<template>
  <view class="page">
    <view class="hero">
      <view class="h-title">体重</view>
      <view class="h-sub">记录变化，不对单次涨跌做判断</view>
    </view>

    <view class="main">
      <view class="card">
        <view v-if="hasLatest">
          <view class="card-label">最近一次测量</view>
          <view class="last-weight">
            <text class="num grad-text">{{ formatKg(summary?.latest_grams ?? null) }}</text>
            <text class="unit">kg</text>
          </view>
          <view class="last-meta">{{ latestMoment }}</view>
        </view>
        <view v-else>
          <view class="card-label">最近一次测量</view>
          <view class="last-empty">还没有记录</view>
          <view class="last-meta">先记录第一次体重，不用设目标。</view>
        </view>

        <button class="btn block record-btn" :disabled="loading" @tap="formVisible = true">
          {{ hasLatest ? '记体重' : '记录第一次体重' }}
        </button>
      </view>

      <view class="section">
        <view class="section-head">
          <view class="h2">趋势</view>
          <view class="segmented">
            <view class="seg" :class="{ on: days === 7 }" @tap="switchDays(7)">近 7 天</view>
            <view class="seg" :class="{ on: days === 30 }" @tap="switchDays(30)">近 30 天</view>
          </view>
        </view>

        <view class="card chart-card">
          <TrendChart :points="chartPoints" />
          <view class="chart-foot">
            <view class="chart-note">
              记录 {{ summary?.count ?? 0 }} 次
              <text v-if="summary && summary.delta_grams !== null" class="delta">
                · 首尾变化 {{ formatDelta(summary.delta_grams) }}
              </text>
            </view>
            <view class="chart-note">每天取最后一次测量</view>
          </view>
          <view v-if="singlePoint" class="chart-note single">
            目前只有一个数据点，再记录几天就能看变化。
          </view>
        </view>
      </view>

      <view class="section">
        <view class="rowlink" @tap="openDetail">
          <text class="t">记录明细</text>
          <view class="r">全部 {{ summary?.count ?? 0 }} 笔<text class="chev">›</text></view>
        </view>
      </view>

      <view v-if="advice" class="hintbox advice">
        <view class="ad-ic">i</view>
        <text class="ad-text">{{ advice }}</text>
      </view>
    </view>

    <WeightForm :visible="formVisible" @close="formVisible = false" @saved="onSaved" />
    <TabBar current="/pages/weight/index" />
  </view>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { onShow } from '@dcloudio/uni-app'
import TabBar from '../../components/TabBar.vue'
import WeightForm from '../../components/WeightForm.vue'
import TrendChart from '../../components/TrendChart.vue'
import { formatMoment } from '../../shared/dates'
import { formatDelta, formatKg } from '../../shared/weight'
import { ApiRequestError, StaleSessionError } from '../../services/httpClient'
import { getSummary } from '../../services/weightService'
import type { WeightSummary } from '../../services/types'

const days = ref<7 | 30>(30)
const summary = ref<WeightSummary | null>(null)
const loading = ref(false)
const formVisible = ref(false)

const hasLatest = computed(() => Boolean(summary.value && summary.value.latest_grams !== null))
const latestMoment = computed(() =>
  summary.value?.latest_measured_at ? formatMoment(summary.value.latest_measured_at) : '—'
)
const singlePoint = computed(() => (summary.value?.points.length ?? 0) === 1)

const chartPoints = computed(() =>
  (summary.value?.points ?? []).map((point) => ({ day: point.day, kg: point.kg }))
)
const advice = computed(() => summary.value?.suggestion ?? '')

async function load() {
  loading.value = true
  try {
    summary.value = await getSummary(days.value)
  } catch (failure) {
    if (failure instanceof StaleSessionError) {
      return
    }
    uni.showToast({
      title: failure instanceof ApiRequestError ? failure.message : '加载失败',
      icon: 'none'
    })
  } finally {
    loading.value = false
  }
}

function switchDays(target: 7 | 30) {
  if (days.value === target) {
    return
  }
  days.value = target
  load()
}

function openDetail() {
  uni.navigateTo({ url: '/pages/weight/detail' })
}

async function onSaved() {
  formVisible.value = false
  await load()
}

onShow(load)
</script>

<style scoped>
.card-label {
  font-size: 13px;
  line-height: 20px;
  color: var(--ink-2);
}
.last-weight {
  display: flex;
  align-items: flex-end;
  gap: 6px;
  margin-top: 2px;
}
.num {
  font-size: 44px;
  line-height: 48px;
  font-weight: 600;
  letter-spacing: -0.5px;
  font-variant-numeric: tabular-nums;
}
.unit {
  font-size: 16px;
  line-height: 24px;
  color: var(--ink-2);
  padding-bottom: 6px;
}
.last-empty {
  margin-top: 4px;
  font-size: 20px;
  line-height: 28px;
  font-weight: 600;
  color: var(--ink-2);
}
.last-meta {
  margin-top: 4px;
  font-size: 13px;
  line-height: 20px;
  color: var(--ink-2);
}
.record-btn {
  margin-top: 14px;
  height: 48px;
}
.segmented {
  display: inline-flex;
  padding: 3px;
  border-radius: 999px;
  background: var(--segbg);
  border: 1px solid var(--card-line);
}
.seg {
  height: 30px;
  padding: 0 12px;
  border-radius: 999px;
  display: flex;
  align-items: center;
  font-size: 12px;
  color: var(--ink-2);
}
.seg.on {
  background: #ffffff;
  color: var(--berry);
  font-weight: 600;
  box-shadow: 0 4px 10px -6px var(--btn-shadow);
}
.chart-card {
  padding-bottom: 14px;
}
.chart-foot {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  margin-top: 8px;
}
.chart-note {
  font-size: 11px;
  line-height: 16px;
  color: var(--ink-2);
}
.chart-note.single {
  margin-top: 8px;
  font-size: 12px;
}
.delta {
  color: var(--berry);
  font-weight: 600;
}
.chev {
  color: var(--ink-2);
}
.advice {
  display: flex;
  align-items: flex-start;
  gap: 10px;
}
.ad-ic {
  flex: 0 0 auto;
  width: 24px;
  height: 24px;
  border-radius: 50%;
  background: var(--soft-grad);
  color: var(--berry);
  font-size: 12px;
  font-weight: 600;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-top: 1px;
}
.ad-text {
  flex: 1;
  font-size: 14px;
  line-height: 22px;
  color: var(--ink);
}
</style>
