<template>
  <view class="page">
    <view class="card latest">
      <view v-if="summary && summary.latest_grams !== null">
        <view class="latest-value">{{ formatKg(summary.latest_grams) }} <text class="unit">kg</text></view>
        <view class="muted">最近一次：{{ summary.latest_measured_at ? formatMoment(summary.latest_measured_at) : '—' }}</view>
      </view>
      <view v-else class="latest-empty">
        <view class="latest-value placeholder">还没有记录</view>
        <view class="muted">先记录第一次体重，不用设目标。</view>
      </view>
      <button class="primary record-button" :disabled="loading" @tap="formVisible = true">
        {{ summary && summary.latest_grams === null ? '记录第一次体重' : '记体重' }}
      </button>
    </view>

    <view class="card">
      <view class="row-between">
        <view class="tabs">
          <view class="tab" :class="{ active: days === 30 }" @tap="switchDays(30)">近 30 天</view>
          <view class="tab" :class="{ active: days === 7 }" @tap="switchDays(7)">近 7 天</view>
        </view>
        <view class="link" @tap="openDetail">记录明细 ›</view>
      </view>

      <TrendChart :points="chartPoints" />

      <view class="stats">
        <view class="stat">
          <view class="stat-value">{{ summary?.count ?? 0 }}</view>
          <view class="muted">记录次数</view>
        </view>
        <view class="stat">
          <view class="stat-value">
            {{ summary && summary.delta_grams !== null ? formatDelta(summary.delta_grams) : '—' }}
          </view>
          <view class="muted">首尾变化</view>
        </view>
        <view class="stat">
          <view class="stat-value">{{ summary?.points.length ?? 0 }}</view>
          <view class="muted">数据点</view>
        </view>
      </view>
      <view v-if="summary && summary.delta_grams === null && summary.points.length === 1" class="muted">
        目前只有一个数据点，再记录几天就能看变化。
      </view>
    </view>

    <view v-if="advice" class="card advice">
      <view class="advice-title">一条建议</view>
      <view class="muted">{{ advice }}</view>
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
.page {
  min-height: 100vh;
  padding: 12px 16px 76px;
  box-sizing: border-box;
}
.latest-value {
  font-size: 32px;
  font-weight: 700;
  color: #b4544a;
}
.latest-value.placeholder {
  font-size: 20px;
  color: #8a7f7a;
}
.unit {
  font-size: 15px;
  font-weight: 400;
}
.record-button {
  margin-top: 14px;
}
.row-between {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}
.tabs {
  display: flex;
  gap: 8px;
}
.tab {
  padding: 5px 12px;
  border-radius: 999px;
  border: 1px solid #e4d8d3;
  font-size: 13px;
  color: #6f635e;
}
.tab.active {
  background: #b4544a;
  border-color: #b4544a;
  color: #ffffff;
}
.link {
  font-size: 13px;
  color: #b4544a;
}
.stats {
  display: flex;
  margin-top: 10px;
}
.stat {
  flex: 1;
  text-align: center;
}
.stat-value {
  font-size: 17px;
  font-weight: 600;
}
.advice {
  background: #fdf2ef;
}
.advice-title {
  font-size: 14px;
  font-weight: 600;
  margin-bottom: 4px;
}
</style>
