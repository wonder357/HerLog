<template>
  <view class="observation-copy">
    <view v-if="observation.demo_sample" class="observation-source">演示样例 · 未调用模型推理</view>
    <view class="observation-source">AI 观察 · 不用于诊断</view>
    <view v-if="summary" class="observation-summary">{{ observation.visible }}</view>
    <template v-else-if="'unclear' in observation">
      <view v-for="section in sections" :key="section.key" class="observation-section">
        <view class="observation-heading">{{ section.label }}</view>
        <view>{{ observation[section.key] }}</view>
      </view>
    </template>
  </view>
</template>

<script setup lang="ts">
import type { SkinAnalysis, SkinObservation, SkinSummaryItem } from '../../services/types'

defineProps<{
  observation: SkinAnalysis | SkinObservation | SkinSummaryItem
  summary?: boolean
}>()

const sections = [
  { key: 'visible', label: '可见外观' },
  { key: 'unclear', label: '看不清之处' },
  { key: 'attention', label: '值得留意' }
] as const
</script>

<style scoped>
.observation-source { color: var(--skin-lilac); font-size: 12px; }
.observation-summary { margin-top: 6px; font-size: 14px; }
.observation-section { padding: 10px 0; border-bottom: 1px solid var(--skin-line); font-size: 14px; }
.observation-section:last-child { border-bottom: 0; padding-bottom: 0; }
.observation-heading { margin-bottom: 4px; font-weight: 600; }
</style>
